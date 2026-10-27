"""
Camada bronze: copia fiel dos arquivos publicados pela CVM.

Os arquivos sao baixados, descompactados e gravados sem nenhuma alteracao em
bronze/cvm/<fonte>/ingestion_date=AAAA-MM-DD/, junto de um _manifest.json com a
linhagem (URL de origem, horario, tamanho e hash SHA-256 de cada arquivo).
Reprocessar a silver/gold nunca exige baixar de novo: a bronze e o historico imutavel.
"""
import hashlib
import os
import tempfile
from datetime import date, datetime

from configs.sources import CvmSource
from lake.lake import Lake
from pipelines.shared.pipeline_base import PipelineBase
from utils.http.download_file import download_file
from utils.zip.unzip import unzip_file


def _sha256(file_path: str) -> str:
    digest = hashlib.sha256()
    with open(file_path, 'rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class CvmBronzeIngestor(PipelineBase):
    """ Ingestor generico de uma fonte da CVM para a camada bronze. """

    def __init__(self, source: CvmSource, lake: Lake, run_date: date):
        """
        :param source: Fonte do catalogo `configs.sources`.
        :type source: CvmSource
        :param lake: Data lake de destino.
        :type lake: Lake
        :param run_date: Data de ingestao (define a particao).
        :type run_date: date
        """
        super().__init__()
        self.name = f'{self.name}[{source.name}]'
        self.source = source
        self.lake = lake
        self.run_date = run_date

    def _download_and_extract(self, url: str, work_folder: str) -> list[str]:
        """ Baixa o arquivo da URL e, se for ZIP, extrai o conteudo. Retorna os arquivos locais. """
        os.makedirs(work_folder, exist_ok=True)
        file_path = download_file(url, os.path.join(work_folder, url.rsplit('/', 1)[-1]))
        if file_path.lower().endswith('.zip'):
            unzip_file(file_path, work_folder, remove_zip_file=True)
        return sorted(
            os.path.join(root, name)
            for root, _, names in os.walk(work_folder)
            for name in names
        )

    def _upload(self, local_files: list[str], destination: str) -> list[dict]:
        """ Envia os arquivos para o lake e devolve os metadados de cada um para o manifest. """
        uploaded = []
        for local_file in local_files:
            file_name = os.path.basename(local_file)
            self.lake.upload_file(local_file, f'{destination}/{file_name}')
            uploaded.append({
                'file': file_name,
                'size_bytes': os.path.getsize(local_file),
                'sha256': _sha256(local_file),
            })
        return uploaded

    def execute_pipeline(self) -> None:
        """
        Executa a ingestao:
        1. Resolve a URL do periodo (ano/mes) quando aplicavel.
        2. Baixa e descompacta dados e dicionario de dados (meta).
        3. Grava os arquivos na particao bronze do dia e o manifest de linhagem.
        """
        url = self.source.resolve_url(self.run_date)
        partition = self.lake.bronze_partition(self.source.name, self.run_date.isoformat())
        self.logger.info('Downloading %s ...', url)

        with tempfile.TemporaryDirectory(prefix=f'cvm_{self.source.name}_') as work_folder:
            data_files = self._download_and_extract(url, os.path.join(work_folder, 'data'))
            files = self._upload(data_files, partition)

            meta_files = []
            if self.source.meta_url:
                local_meta = self._download_and_extract(self.source.meta_url, os.path.join(work_folder, 'meta'))
                meta_files = self._upload(local_meta, f'{partition}/_meta')

        self.lake.write_json(f'{partition}/_manifest.json', {
            'source': self.source.name,
            'description': self.source.description,
            'url': url,
            'meta_url': self.source.meta_url,
            'ingestion_date': self.run_date.isoformat(),
            'ingested_at': datetime.now().isoformat(timespec='seconds'),
            'files': files,
            'meta_files': meta_files,
        })
        self.logger.info('%s file(s) written to %s', len(files), partition)
