""" Classe base e funcoes auxiliares da camada gold. """
from abc import abstractmethod

import pandas as pd

from lake.lake import GOLD, SILVER, Lake
from pipelines.shared.pipeline_base import PipelineBase
from utils.text import company_key, extract_cnpj_root, free_text_company_key


def mode_or_first(series: pd.Series):
    """ Valor mais frequente de uma serie (usado para escolher o nome 'oficial' de um agrupamento). """
    values = series.dropna()
    if values.empty:
        return pd.NA
    return values.mode().iloc[0]


def add_share_and_rank(df: pd.DataFrame, value_column: str, partition: list[str] | None = None,
                       share_column: str = 'market_share') -> pd.DataFrame:
    """ Adiciona participacao (%) e ranking por `value_column`, opcionalmente dentro de `partition`. """
    df = df.copy()
    if partition:
        total = df.groupby(partition)[value_column].transform('sum')
        rank = df.groupby(partition)[value_column].rank(method='min', ascending=False)
    else:
        total = df[value_column].sum()
        rank = df[value_column].rank(method='min', ascending=False)
    df[share_column] = (df[value_column] / total).round(4)
    df['ranking'] = rank.astype('Int64')
    sort_columns = (partition or []) + ['ranking']
    return df.sort_values(sort_columns).reset_index(drop=True)


def prefer_active(registry: pd.DataFrame) -> pd.DataFrame:
    """
    Ordena um cadastro colocando primeiro os registros ativos e mais recentes.
    Uma mesma empresa pode ter registros antigos cancelados e um registro ativo atual.
    """
    return (registry.assign(_ativo=registry['situacao_grupo'].eq('ATIVO'))
            .sort_values(['_ativo', 'data_registro'], ascending=False)
            .drop(columns='_ativo'))


class RegistryMatcher:
    """
    Resolve nomes de empresas informados em texto livre contra um cadastro da CVM.

    Ordem de tentativa: raiz do CNPJ citado no texto -> razao social -> nome comercial.
    Em caso de chaves repetidas, vence o registro ativo mais recente.
    """

    def __init__(self, registry: pd.DataFrame):
        self.registry = prefer_active(registry)
        self._index: dict[str, object] = {}
        for idx, row in self.registry.iterrows():
            keys = [
                f'CNPJ:{row["cnpj"][:8]}' if pd.notna(row['cnpj']) else None,
                f'NOME:{company_key(row["nome"])}' if pd.notna(row['nome']) else None,
                f'NOME:{company_key(row["nome_comercial"])}' if pd.notna(row['nome_comercial']) else None,
            ]
            for key in keys:
                if key and not key.endswith(':None'):
                    self._index.setdefault(key, idx)

    def match(self, text) -> object | None:
        """
        Indice do registro correspondente ao texto, ou None.

        Ultimo recurso: nome abreviado (2+ palavras) que e prefixo de um unico registro,
        ex.: 'Oliveira Trust' -> 'OLIVEIRA TRUST DTVM'.
        """
        name_key = free_text_company_key(text)
        candidates = [f'CNPJ:{extract_cnpj_root(text)}', f'NOME:{name_key}']
        exact = next((self._index[key] for key in candidates if key in self._index), None)
        if exact is not None or not name_key or len(name_key.split()) < 2:
            return exact
        prefix = f'NOME:{name_key} '
        matches = {idx for key, idx in self._index.items() if key.startswith(prefix)}
        return matches.pop() if len(matches) == 1 else None

    def resolve(self, names: pd.Series, registry_columns: list[str]) -> pd.DataFrame:
        """
        Tabela de-para: nome original -> entidade (CNPJ do cadastro, ou chave do nome quando nao encontrado).

        :returns: DataFrame com `nome_original`, `chave_entidade`, `nome_cadastro` e `registry_columns`.
        """
        rows = []
        for name in names.dropna().unique():
            idx = self.match(name)
            if idx is None:
                rows.append({'nome_original': name, 'chave_entidade': f'NOME:{free_text_company_key(name)}'})
                continue
            entry = self.registry.loc[idx]
            rows.append({'nome_original': name, 'chave_entidade': f'CNPJ:{entry["cnpj"]}',
                         'nome_cadastro': entry['nome'], **{col: entry[col] for col in registry_columns}})
        return pd.DataFrame(rows, columns=['nome_original', 'chave_entidade', 'nome_cadastro', *registry_columns])


def registry_of(participantes: pd.DataFrame, tipo_participante: str) -> pd.DataFrame:
    """ Pessoas juridicas de um tipo de participante. """
    return participantes[(participantes['tipo_participante'] == tipo_participante)
                         & (participantes['tipo_pessoa'] == 'PJ')]


class GoldPipelineBase(PipelineBase):
    """ Le tabelas da silver e grava tabelas analiticas na gold (Parquet + CSV). """

    def __init__(self, lake: Lake):
        super().__init__()
        self.lake = lake

    def read_silver(self, table: str) -> pd.DataFrame:
        """ Le uma tabela da silver. """
        return self.lake.read_table(SILVER, table)

    def write_gold(self, df: pd.DataFrame, table: str) -> None:
        """ Grava a tabela na gold, com copia CSV para consumo em planilhas e ferramentas de BI. """
        path = self.lake.write_table(df, GOLD, table, csv_copy=True)
        self.logger.info('Gold table "%s" written: %s rows -> %s', table, len(df), path)

    @abstractmethod
    def execute_pipeline(self) -> None:
        """ Executa a geracao das tabelas gold. """
