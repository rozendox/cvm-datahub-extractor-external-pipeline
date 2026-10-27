"""
Silver: cadastro unificado de participantes do mercado regulados pela CVM.

Os cadastros (gestoras/administradores, assessores, agentes fiduciarios, auditores,
consultores, plataformas de crowdfunding e administradores de FII) tem layouts parecidos,
mas nomes de colunas diferentes. Aqui eles viram uma unica tabela com o mesmo schema.
As tabelas filhas (socios, diretores, responsaveis) permanecem apenas na bronze.
"""
import pandas as pd

from pipelines.silver.silver_base import SilverPipelineBase
from pipelines.silver.transforms import apply_standard_types, clean_strings, to_number
from utils.text import normalize_text

TABLE = 'cvm_participantes'

# fonte -> [(arquivo, tipo_participante, tipo_pessoa)]
PARTICIPANT_FILES = {
    'cad_adm_carteira': [
        ('cad_adm_cart_pf.csv', 'administrador_carteira', 'PF'),
        ('cad_adm_cart_pj.csv', 'administrador_carteira', 'PJ'),
    ],
    'cad_adm_fii': [('cad_adm_fii.csv', 'administrador_fii', 'PJ')],
    'cad_agente_autonomo': [
        ('cad_agente_auton_pf.csv', 'agente_autonomo', 'PF'),
        ('cad_agente_auton_pj.csv', 'agente_autonomo', 'PJ'),
    ],
    'cad_agente_fiduciario': [
        ('cad_agente_fiduc_pf.csv', 'agente_fiduciario', 'PF'),
        ('cad_agente_fiduc_pj.csv', 'agente_fiduciario', 'PJ'),
    ],
    'cad_auditor': [
        ('cad_auditor_pf.csv', 'auditor_independente', 'PF'),
        ('cad_auditor_pj.csv', 'auditor_independente', 'PJ'),
    ],
    'cad_consultor': [
        ('cad_consultor_vlmob_pf.csv', 'consultor_valores_mobiliarios', 'PF'),
        ('cad_consultor_vlmob_pj.csv', 'consultor_valores_mobiliarios', 'PJ'),
    ],
    'cad_crowdfunding': [('cad_crowdfunding.csv', 'plataforma_crowdfunding', 'PJ')],
}

# Cada cadastro usa um nome diferente para a razao social / nome da pessoa
NAME_COLUMNS = ['DENOM_SOCIAL', 'NOME', 'ADMIN', 'AGENTE_FIDUC', 'AUDITOR']

COLUMN_MAP = {
    'CNPJ': 'cnpj',
    'CD_CVM': 'codigo_cvm',
    'DENOM_COMERC': 'nome_comercial',
    'CATEG_REG': 'categoria',
    'SUBCATEG_REG': 'subcategoria',
    'SIT': 'situacao',
    'DT_REG': 'data_registro',
    'DT_CANCEL': 'data_cancelamento',
    'MOTIVO_CANCEL': 'motivo_cancelamento',
    'DT_INI_SIT': 'data_inicio_situacao',
    'MUN': 'municipio',
    'UF': 'uf',
    'VL_PATRIM_LIQ': 'patrimonio_liquido',
    'DT_PATRIM_LIQ': 'data_patrimonio_liquido',
}

OUTPUT_COLUMNS = [
    'tipo_participante', 'tipo_pessoa', 'cnpj', 'codigo_cvm', 'nome', 'nome_comercial',
    'categoria', 'subcategoria', 'situacao', 'situacao_grupo', 'data_registro', 'data_cancelamento',
    'motivo_cancelamento', 'data_inicio_situacao', 'municipio', 'uf', 'patrimonio_liquido',
    'data_patrimonio_liquido', '_source', '_source_file', '_ingestion_date',
]


def situacao_grupo(situacao: str | None) -> str | None:
    """ Agrupa as dezenas de situacoes cadastrais da CVM em poucos grupos analiticos. """
    text = normalize_text(situacao)
    if text is None:
        return None
    if text in {'EM FUNCIONAMENTO NORMAL', 'ATIVO', 'ATIVA'}:
        return 'ATIVO'
    if text.startswith('CANCELAD'):
        return 'CANCELADO'
    if text.startswith(('SUSPENS', 'AFASTAD')):
        return 'SUSPENSO'
    if text.startswith('EM ANALISE'):
        return 'EM_ANALISE'
    return 'OUTROS'


def transform_participantes(raw: pd.DataFrame, tipo_participante: str, tipo_pessoa: str) -> pd.DataFrame:
    """
    Converte um arquivo de cadastro para o schema unificado de participantes.

    :param raw: DataFrame lido da bronze.
    :param tipo_participante: Categoria do participante (ex.: 'agente_autonomo').
    :param tipo_pessoa: 'PF' ou 'PJ'.
    :returns: DataFrame no schema `OUTPUT_COLUMNS`.
    """
    name_column = next((col for col in NAME_COLUMNS if col in raw.columns), None)
    df = raw.rename(columns={**COLUMN_MAP, **({name_column: 'nome'} if name_column else {})})
    df = clean_strings(df)
    df['tipo_participante'] = tipo_participante
    df['tipo_pessoa'] = tipo_pessoa
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[OUTPUT_COLUMNS]

    df = apply_standard_types(df)
    df['patrimonio_liquido'] = to_number(df['patrimonio_liquido'])
    df['uf'] = df['uf'].str.upper()
    df['situacao_grupo'] = df['situacao'].map(situacao_grupo).astype('string')
    return df


class CvmParticipantesSilver(SilverPipelineBase):
    """ Silver do cadastro unificado de participantes. """

    def execute_pipeline(self) -> None:
        frames = []
        for source, files in PARTICIPANT_FILES.items():
            try:
                ingestion_date = self.lake.resolve_bronze_date(source, self.ingestion_date)
            except FileNotFoundError as error:
                self.logger.warning('Fonte ignorada: %s', error)
                continue
            for file_name, tipo_participante, tipo_pessoa in files:
                raw = self.read_bronze_csv(source, file_name, ingestion_date)
                frames.append(transform_participantes(raw, tipo_participante, tipo_pessoa))

        if not frames:
            raise FileNotFoundError('Nenhum cadastro de participantes encontrado na bronze.')

        df = pd.concat(frames, ignore_index=True)
        self.write_silver(df, TABLE)
