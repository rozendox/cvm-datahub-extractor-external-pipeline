"""
Funcoes de padronizacao usadas pela camada silver.

Todas recebem/retornam Series ou DataFrames e nao tem efeitos colaterais,
o que permite testa-las isoladamente (ver tests/).
"""
import pandas as pd

from utils.text import only_digits, to_snake_case


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """ Renomeia as colunas para snake_case e corrige o typo 'Qdte' publicado pela CVM. """
    columns = {col: to_snake_case(col).replace('qdte_', 'qtde_') for col in df.columns}
    return df.rename(columns=columns)


def clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """ Remove espacos nas pontas das colunas de texto e converte vazios em nulo. """
    df = df.copy()
    for col in df.select_dtypes(include=['object', 'string']).columns:
        df[col] = df[col].str.strip().replace('', pd.NA)
    return df


def to_date(series: pd.Series) -> pd.Series:
    """
    Converte texto em data. Aceita ISO (AAAA-MM-DD, padrao da CVM) e DD/MM/AAAA.
    Datas invalidas ou anteriores a 1900 viram nulo (ha registros com 1899-12-31 como placeholder).
    """
    parsed = pd.to_datetime(series, format='%Y-%m-%d', errors='coerce')
    fallback = parsed.isna() & series.notna()
    if fallback.any():
        parsed[fallback] = pd.to_datetime(series[fallback], format='%d/%m/%Y', errors='coerce')
    return parsed.where(parsed >= pd.Timestamp('1900-01-01'))


def to_number(series: pd.Series) -> pd.Series:
    """
    Converte texto em numero.

    A CVM publica com ponto decimal ('5000000.04'). Valores no formato brasileiro
    ('5.000.000,04') tambem sao aceitos: quando ha virgula, os pontos sao separadores de milhar.
    """
    text = series.astype('string').str.strip()
    brazilian = text.str.contains(',', regex=False, na=False)
    text = text.mask(brazilian, text.str.replace('.', '', regex=False).str.replace(',', '.', regex=False))
    return pd.to_numeric(text, errors='coerce').astype('float64')


def to_flag(series: pd.Series) -> pd.Series:
    """ Converte colunas S/N em booleano (nullable). """
    return series.map({'S': True, 'N': False}).astype('boolean')


def flag_columns(df: pd.DataFrame) -> list[str]:
    """ Detecta colunas cujos valores preenchidos sao apenas 'S' e 'N'. """
    return [
        col for col in df.columns
        if df[col].notna().any() and set(df[col].dropna().unique()) <= {'S', 'N'}
    ]


def to_cnpj(series: pd.Series) -> pd.Series:
    """ Normaliza CNPJ para 14 digitos, sem pontuacao. """
    return series.map(lambda value: only_digits(value, width=14)).astype('string')


def apply_standard_types(df: pd.DataFrame, numeric_columns: list[str] | None = None) -> pd.DataFrame:
    """
    Aplica a tipagem padrao da silver:
    - colunas `data_*`  -> datetime
    - colunas `cnpj_*`  -> 14 digitos
    - colunas S/N       -> booleano
    - `numeric_columns` -> float
    """
    df = df.copy()
    for col in df.columns:
        if col.startswith('data_') or col.startswith('dt_'):
            df[col] = to_date(df[col])
        elif col == 'cnpj' or col.startswith('cnpj_'):
            df[col] = to_cnpj(df[col])
    for col in flag_columns(df):
        df[col] = to_flag(df[col])
    for col in numeric_columns or []:
        if col in df.columns:
            df[col] = to_number(df[col])
    return df
