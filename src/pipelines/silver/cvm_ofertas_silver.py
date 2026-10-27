"""
Silver: ofertas publicas de distribuicao (Resolucao CVM 160).

Uma linha por requerimento de oferta, com colunas em snake_case, tipos corretos,
classificacao do ativo e metricas de colocacao derivadas da distribuicao por tipo de investidor.
"""
import pandas as pd

from pipelines.silver.silver_base import SilverPipelineBase
from pipelines.silver.transforms import apply_standard_types, clean_strings, standardize_columns
from utils.text import normalize_text

SOURCE = 'ofertas_distribuicao'
SOURCE_FILE = 'oferta_resolucao_160.csv'
TABLE = 'cvm_ofertas'

# Valor mobiliario (normalizado) -> (tipo_ativo, classe_ativo)
TIPOS_ATIVO = {
    'CERTIFICADOS DE RECEBIVEIS IMOBILIARIOS': ('CRI', 'renda_fixa'),
    'CERTIFICADOS DE RECEBIVEIS DO AGRONEGOCIO': ('CRA', 'renda_fixa'),
    'CERTIFICADOS DE RECEBIVEIS': ('CR', 'renda_fixa'),
    'OUTROS TITULOS DE SECURITIZACAO': ('OUTROS_SECURITIZACAO', 'renda_fixa'),
    'CERTIFICADO DE DIREITOS CREDITORIOS DO AGRONEGOCIO': ('CDCA', 'renda_fixa'),
    'CEDULA DE PRODUTO RURAL FINANCEIRA': ('CPR-F', 'renda_fixa'),
    'DEBENTURES': ('DEBENTURE', 'renda_fixa'),
    'DEBENTURES CONVERSIVEIS': ('DEBENTURE_CONVERSIVEL', 'renda_fixa'),
    'NOTAS COMERCIAIS': ('NOTA_COMERCIAL', 'renda_fixa'),
    'NOTAS PROMISSORIAS': ('NOTA_PROMISSORIA', 'renda_fixa'),
    'COTAS DE FII': ('FII', 'fundos'),
    'COTAS DE FIDC': ('FIDC', 'fundos'),
    'COTAS DE FIP': ('FIP', 'fundos'),
    'COTAS DE FIF': ('FIF', 'fundos'),
    'COTAS DE FIAGRO': ('FIAGRO', 'fundos'),
    'COTAS DE FIAGRO - FII': ('FIAGRO-FII', 'fundos'),
    'COTAS DE FIAGRO - FIDC': ('FIAGRO-FIDC', 'fundos'),
    'COTAS DE FIAGRO - FIP': ('FIAGRO-FIP', 'fundos'),
    'COTAS DE FUNDOS DE INFRA': ('FI-INFRA', 'fundos'),
    'COTAS DE FUNCINE': ('FUNCINE', 'fundos'),
    'ACOES': ('ACOES', 'renda_variavel'),
    'CERTIFICADO DE DEPOSITO DE ACOES (UNIT)': ('UNIT', 'renda_variavel'),
}

# Ativos emitidos por securitizadoras
TIPOS_SECURITIZACAO = ['CRI', 'CRA', 'CR', 'OUTROS_SECURITIZACAO']

# Status que indicam que a oferta nao aconteceu (ou nao esta acontecendo)
STATUS_INVALIDOS = {'OFERTA REVOGADA', 'REGISTRO CADUCADO', 'REQUERIMENTO EXPIRADO', 'OFERTA SUSPENSA'}
STATUS_ENCERRADA = 'OFERTA ENCERRADA'

# Taxa de colocacao acima deste limite indica unidades inconsistentes entre os campos da CVM
TAXA_COLOCACAO_MAXIMA = 1.05

NUMERIC_COLUMNS = ['valor_total_registrado', 'qtde_total_registrada']


def investor_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """ Colunas de numero de investidores e de quantidade subscrita por tipo de investidor. """
    num_cols = [c for c in df.columns if c.startswith('num_invest_')]
    qtde_cols = [c for c in df.columns if c.startswith('qtde_vm_')]
    return num_cols, qtde_cols


def transform_ofertas(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma o CSV bruto de ofertas na tabela silver.

    :param raw: DataFrame lido da bronze (todas as colunas como texto).
    :type raw: pd.DataFrame
    :returns: DataFrame tipado e enriquecido.
    :rtype: pd.DataFrame
    """
    df = clean_strings(standardize_columns(raw))
    df = df.rename(columns={'emissao': 'numero_emissao', 'status_requerimento': 'status'})

    num_cols, qtde_cols = investor_columns(df)
    df = apply_standard_types(df, NUMERIC_COLUMNS + num_cols + qtde_cols)

    df['numero_emissao'] = df['numero_emissao'].str.replace(r'\.0$', '', regex=True)
    df['status'] = df['status'].map(normalize_text).astype('string')

    tipo_classe = df['valor_mobiliario'].map(normalize_text).map(
        lambda value: TIPOS_ATIVO.get(value, (value, 'outros')))
    df['tipo_ativo'] = tipo_classe.str[0].astype('string')
    df['classe_ativo'] = tipo_classe.str[1].astype('string')

    df['oferta_valida'] = ~df['status'].isin(STATUS_INVALIDOS)
    df['oferta_encerrada'] = df['status'].eq(STATUS_ENCERRADA)

    df['ano_registro'] = df['data_registro'].dt.year.astype('Int64')
    df['mes_registro'] = df['data_registro'].dt.to_period('M').dt.to_timestamp()
    df['dias_distribuicao'] = (df['data_encerramento'] - df['data_registro']).dt.days.astype('Int64')

    # Colocacao: soma das quantidades subscritas por tipo de investidor (preenchida no encerramento)
    qtde_colocada = df[qtde_cols].sum(axis=1, min_count=1)
    df['qtde_colocada'] = qtde_colocada.where(df['oferta_encerrada'] & (qtde_colocada > 0))
    taxa = df['qtde_colocada'] / df['qtde_total_registrada'].where(df['qtde_total_registrada'] > 0)
    df['taxa_colocacao_inconsistente'] = taxa > TAXA_COLOCACAO_MAXIMA
    df['taxa_colocacao'] = taxa.where(~df['taxa_colocacao_inconsistente']).clip(upper=1.0)
    df['volume_colocado_estimado'] = df['valor_total_registrado'] * df['taxa_colocacao']

    return df


class CvmOfertasSilver(SilverPipelineBase):
    """ Silver das ofertas publicas de distribuicao. """

    def execute_pipeline(self) -> None:
        ingestion_date = self.lake.resolve_bronze_date(SOURCE, self.ingestion_date)
        raw = self.read_bronze_csv(SOURCE, SOURCE_FILE, ingestion_date)
        df = transform_ofertas(raw)

        unmapped = df.loc[df['classe_ativo'] == 'outros', 'tipo_ativo'].dropna().unique().tolist()
        if unmapped:
            self.logger.warning('Valores mobiliarios sem classificacao (classe "outros"): %s', unmapped)
        self.logger.info('Taxa de colocacao inconsistente em %s ofertas encerradas.',
                         int(df['taxa_colocacao_inconsistente'].sum()))

        self.write_silver(df, TABLE)
