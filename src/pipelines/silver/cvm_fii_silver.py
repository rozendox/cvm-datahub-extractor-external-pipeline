"""
Silver: informe anual estruturado de FII.

Gera quatro tabelas, sempre mantendo apenas a versao mais recente de cada informe
(a CVM republica o documento com Versao 2, 3... quando o administrador reapresenta):
- cvm_fii_geral: cadastro do fundo/classe no informe (segmento, mandato, administrador)
- cvm_fii_ativo_valor_contabil: ativos imobiliarios e seu valor contabil
- cvm_fii_ativo_transacao: aquisicoes e alienacoes de ativos no exercicio
- cvm_fii_ativo_adquirido: ativos adquiridos e origem dos recursos
"""
import re

import pandas as pd

from pipelines.silver.silver_base import SilverPipelineBase
from pipelines.silver.transforms import apply_standard_types, clean_strings, standardize_columns
from utils.text import normalize_text

SOURCE = 'fii_informe_anual'

# prefixo do arquivo na bronze -> (tabela silver, colunas numericas)
FII_TABLES = {
    'inf_anual_fii_geral': ('cvm_fii_geral', ['quantidade_cotas_emitidas']),
    'inf_anual_fii_ativo_valor_contabil': ('cvm_fii_ativo_valor_contabil', ['valor']),
    'inf_anual_fii_ativo_transacao': ('cvm_fii_ativo_transacao', ['valor_envolvido']),
    'inf_anual_fii_ativo_adquirido': ('cvm_fii_ativo_adquirido', ['montante_investido']),
}

INFORME_KEY = ['cnpj_fundo_classe', 'data_referencia']


def keep_latest_version(df: pd.DataFrame) -> pd.DataFrame:
    """ Mantem somente as linhas da maior versao de cada informe (fundo + data de referencia). """
    latest = df.groupby(INFORME_KEY)['versao'].transform('max')
    return df[df['versao'] == latest].reset_index(drop=True)


def transform_fii(raw: pd.DataFrame, numeric_columns: list[str]) -> pd.DataFrame:
    """
    Padroniza um arquivo do informe anual de FII.

    :param raw: DataFrame lido da bronze.
    :param numeric_columns: Colunas a converter para numero.
    :returns: DataFrame tipado, apenas com a versao mais recente de cada informe.
    """
    df = clean_strings(standardize_columns(raw))
    df = apply_standard_types(df, numeric_columns + ['versao'])
    df['ano_referencia'] = df['data_referencia'].dt.year.astype('Int64')
    for col in ['segmento_atuacao', 'mandato', 'tipo_gestao', 'natureza_transacao']:
        if col in df.columns:
            df[col] = df[col].map(normalize_text).astype('string')
    return keep_latest_version(df)


class CvmFiiSilver(SilverPipelineBase):
    """ Silver do informe anual de FII. """

    def execute_pipeline(self) -> None:
        ingestion_date = self.lake.resolve_bronze_date(SOURCE, self.ingestion_date)
        files = self.lake.bronze_files(SOURCE, ingestion_date)

        for prefix, (table, numeric_columns) in FII_TABLES.items():
            pattern = re.compile(rf'^{prefix}_\d{{4}}\.csv$')
            matches = [name for name in files if pattern.match(name)]
            if not matches:
                raise FileNotFoundError(
                    f'Arquivo {prefix}_<ano>.csv nao encontrado na bronze {SOURCE}/{ingestion_date}.')
            raw = pd.concat([self.read_bronze_csv(SOURCE, name, ingestion_date) for name in matches],
                            ignore_index=True)
            self.write_silver(transform_fii(raw, numeric_columns), table)
