""" Classe base das pipelines da camada silver. """
from abc import abstractmethod

import pandas as pd

from lake.lake import SILVER, Lake
from pipelines.shared.pipeline_base import PipelineBase


class SilverPipelineBase(PipelineBase):
    """ Le a particao bronze mais recente (ou a informada) e grava tabelas tipadas na silver. """

    def __init__(self, lake: Lake, ingestion_date: str | None = None):
        """
        :param lake: Data lake.
        :type lake: Lake
        :param ingestion_date: Particao bronze a processar (AAAA-MM-DD). Padrao: a mais recente.
        :type ingestion_date: str | None
        """
        super().__init__()
        self.lake = lake
        self.ingestion_date = ingestion_date

    def read_bronze_csv(self, source: str, file_name: str, ingestion_date: str) -> pd.DataFrame:
        """ Le um CSV da bronze e adiciona as colunas de linhagem. """
        path = f'{self.lake.bronze_partition(source, ingestion_date)}/{file_name}'
        df = self.lake.read_csv(path)
        df['_source'] = source
        df['_source_file'] = file_name
        df['_ingestion_date'] = pd.Timestamp(ingestion_date)
        return df

    def write_silver(self, df: pd.DataFrame, table: str) -> None:
        """ Grava a tabela na silver e registra o volume processado. """
        path = self.lake.write_table(df, SILVER, table)
        self.logger.info('Silver table "%s" written: %s rows -> %s', table, len(df), path)

    @abstractmethod
    def execute_pipeline(self) -> None:
        """ Executa a transformacao bronze -> silver. """
