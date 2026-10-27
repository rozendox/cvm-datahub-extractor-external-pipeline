"""
Abstracao de armazenamento do data lake (arquitetura medallion).

Toda leitura e escrita passa por esta classe, que usa o fsspec. Assim o mesmo codigo
funciona com o disco local (padrao) ou com o AWS S3, bastando trocar a raiz:

    LAKE_ROOT=lake                      -> ./lake/bronze, ./lake/silver, ./lake/gold
    LAKE_ROOT=s3://meu-bucket/cvm-lake  -> s3://meu-bucket/cvm-lake/bronze, ...

Layout:
    bronze/cvm/<fonte>/ingestion_date=AAAA-MM-DD/<arquivos originais> + _manifest.json
    silver/<tabela>/data.parquet
    gold/<tabela>/data.parquet
    exports/gold/<tabela>.csv   (copia para planilhas/BI)
"""
import io
import json

import fsspec
import pandas as pd

from configs import settings

BRONZE = 'bronze'
SILVER = 'silver'
GOLD = 'gold'


class Lake:
    """ Data lake local ou remoto, acessado via fsspec. """

    def __init__(self, root: str | None = None, storage_options: dict | None = None):
        self.root = (root or settings.LAKE_ROOT).rstrip('/')
        options = settings.LAKE_STORAGE_OPTIONS if storage_options is None else storage_options
        self.fs, self.root_path = fsspec.core.url_to_fs(self.root, **options)

    def path(self, *parts: str) -> str:
        """ Monta o caminho de um objeto a partir da raiz do lake. """
        return '/'.join([self.root_path.rstrip('/'), *[p.strip('/') for p in parts]])

    # Bronze

    def bronze_partition(self, source: str, ingestion_date: str) -> str:
        """ Caminho da particao bronze de uma fonte numa data de ingestao. """
        return self.path(BRONZE, 'cvm', source, f'ingestion_date={ingestion_date}')

    def bronze_dates(self, source: str) -> list[str]:
        """ Datas de ingestao disponiveis para uma fonte, em ordem crescente. """
        base = self.path(BRONZE, 'cvm', source)
        if not self.fs.exists(base):
            return []
        names = [entry.rstrip('/').rsplit('/', 1)[-1] for entry in self.fs.ls(base, detail=False)]
        return sorted(name.split('=', 1)[1] for name in names if name.startswith('ingestion_date='))

    def resolve_bronze_date(self, source: str, ingestion_date: str | None = None) -> str:
        """
        Retorna a data de ingestao a ser lida: a informada ou a mais recente.

        :raises FileNotFoundError: Se nao houver particao para a fonte.
        """
        dates = self.bronze_dates(source)
        if ingestion_date:
            if ingestion_date not in dates:
                raise FileNotFoundError(f'Particao bronze {source}/{ingestion_date} nao encontrada.')
            return ingestion_date
        if not dates:
            raise FileNotFoundError(f'Nenhuma particao bronze para a fonte "{source}". Rode a camada bronze.')
        return dates[-1]

    def bronze_files(self, source: str, ingestion_date: str) -> list[str]:
        """ Nomes dos arquivos de dados (sem manifest/metadados) de uma particao bronze. """
        partition = self.bronze_partition(source, ingestion_date)
        return sorted(
            entry.rsplit('/', 1)[-1]
            for entry in self.fs.ls(partition, detail=False)
            if not entry.rsplit('/', 1)[-1].startswith('_') and self.fs.isfile(entry)
        )

    # Operacoes basicas

    def write_bytes(self, path: str, data: bytes) -> None:
        """ Grava bytes num caminho do lake, criando as pastas necessarias. """
        self.fs.makedirs(path.rsplit('/', 1)[0], exist_ok=True)
        with self.fs.open(path, 'wb') as file:
            file.write(data)

    def upload_file(self, local_path: str, path: str) -> None:
        """ Copia um arquivo local para o lake em streaming (adequado para arquivos grandes). """
        self.fs.makedirs(path.rsplit('/', 1)[0], exist_ok=True)
        self.fs.put_file(local_path, path)

    def read_bytes(self, path: str) -> bytes:
        """ Le os bytes de um objeto do lake. """
        with self.fs.open(path, 'rb') as file:
            return file.read()

    def write_json(self, path: str, payload: dict) -> None:
        """ Grava um dicionario como JSON (UTF-8, indentado). """
        self.write_bytes(path, json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode('utf-8'))

    def read_csv(self, path: str, **kwargs) -> pd.DataFrame:
        """
        Le um CSV da CVM. Tenta UTF-8 e cai para Latin-1, encoding padrao do portal.
        Por padrao todas as colunas sao lidas como texto; a tipagem e feita na silver.
        """
        raw = self.read_bytes(path)
        options = {'sep': ';', 'dtype': str, 'keep_default_na': False, 'na_values': ['']}
        options.update(kwargs)
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('latin-1')
        return pd.read_csv(io.StringIO(text), **options)

    # Tabelas (silver e gold)

    def table_path(self, layer: str, table: str) -> str:
        """ Caminho do arquivo Parquet de uma tabela numa camada. """
        return self.path(layer, table, 'data.parquet')

    def export_path(self, layer: str, table: str) -> str:
        """
        Caminho da copia CSV de uma tabela. Fica fora da pasta da tabela para que
        catalogos como Glue/Athena enxerguem apenas Parquet em <camada>/<tabela>/.
        """
        return self.path('exports', layer, f'{table}.csv')

    def write_table(self, df: pd.DataFrame, layer: str, table: str, csv_copy: bool = False) -> str:
        """
        Grava (sobrescreve) uma tabela em Parquet. Opcionalmente grava uma copia CSV
        (separador ';', decimal ',' e BOM UTF-8, para abrir direto no Excel em pt-BR).

        :returns: Caminho do arquivo Parquet gravado.
        :rtype: str
        """
        path = self.table_path(layer, table)
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        self.write_bytes(path, buffer.getvalue())
        if csv_copy:
            csv_text = df.to_csv(index=False, sep=';', decimal=',')
            self.write_bytes(self.export_path(layer, table), csv_text.encode('utf-8-sig'))
        return path

    def read_table(self, layer: str, table: str) -> pd.DataFrame:
        """ Le uma tabela Parquet de uma camada. """
        path = self.table_path(layer, table)
        if not self.fs.exists(path):
            raise FileNotFoundError(f'Tabela {layer}/{table} nao encontrada em {self.root}.')
        return pd.read_parquet(io.BytesIO(self.read_bytes(path)))

    def table_exists(self, layer: str, table: str) -> bool:
        """ Indica se a tabela existe na camada. """
        return self.fs.exists(self.table_path(layer, table))
