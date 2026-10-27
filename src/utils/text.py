""" Funcoes de normalizacao de texto e documentos. """
import re

import pandas as pd
import unidecode

# Tipo societario removido na chave de comparacao de nomes de empresas.
# 'S.A.' aparece no meio do nome com frequencia ('PENTAGONO S.A. DTVM'), entao sai de qualquer posicao.
_COMPANY_SA = re.compile(r'\bS ?/? ?A\b|(?<=S)S A$')
_COMPANY_SUFFIXES = re.compile(r'\b(LTDA|EIRELI|ME|EPP)$')

# Formas longas -> abreviacoes usadas no mercado (os cadastros da CVM misturam as duas)
_COMPANY_ABBREVIATIONS = [
    (re.compile(r'\bDISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS?\b'), 'DTVM'),
    (re.compile(r'\bCORRETORA DE CAMBIO TITULOS E VALORES MOBILIARIOS?\b'), 'CCTVM'),
    (re.compile(r'\bCORRETORA DE TITULOS E VALORES MOBILIARIOS?\b'), 'CTVM'),
    (re.compile(r'\bD T V M\b'), 'DTVM'),
    (re.compile(r'\bC T V M\b'), 'CTVM'),
]


def to_snake_case(name: str) -> str:
    """ Converte um nome de coluna para snake_case ASCII. Ex.: 'Valor_Total_Registrado' -> 'valor_total_registrado'. """
    ascii_name = unidecode.unidecode(str(name)).strip().lower()
    return re.sub(r'[^a-z0-9]+', '_', ascii_name).strip('_')


def normalize_text(value) -> str | None:
    """ Remove acentos, espacos extras e coloca em caixa alta. Mantem nulos como None. """
    if value is None or pd.isna(value):
        return None
    text = re.sub(r'\s+', ' ', unidecode.unidecode(str(value))).strip().upper()
    return text or None


def company_key(value) -> str | None:
    """
    Chave de comparacao de nomes de empresas vindos de campos de texto livre.

    Ex.: 'Vórtx Distribuidora de Títulos e Valores Mobiliários Ltda.' e
    'VORTX DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA' geram a mesma chave.
    """
    text = normalize_text(value)
    if text is None:
        return None
    text = re.sub(r'[^A-Z0-9/ ]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+', ' ', _COMPANY_SA.sub(' ', text)).strip()
    for pattern, abbreviation in _COMPANY_ABBREVIATIONS:
        text = pattern.sub(abbreviation, text)
    previous = None
    while previous != text:
        previous = text
        text = _COMPANY_SUFFIXES.sub('', text).strip()
    return text or None


_CNPJ_IN_TEXT = re.compile(r'\d{2}\.?\d{3}\.?\d{3}\s?/?\s?\d{4}\s?-?\s?\d{2}')
_FREE_TEXT_CUT = re.compile(r',|\bINSCRIT[AO]\b|\bCNPJ\b|\bINSTITUICAO FINANCEIRA\b')


def extract_cnpj_root(value) -> str | None:
    """
    Extrai a raiz (8 primeiros digitos) do primeiro CNPJ citado num texto livre.
    A raiz identifica a empresa independentemente da filial (0001, 0004...).
    """
    if value is None or pd.isna(value):
        return None
    match = _CNPJ_IN_TEXT.search(str(value))
    return re.sub(r'\D', '', match.group())[:8] if match else None


def free_text_company_key(value) -> str | None:
    """
    Chave de nome para campos de texto livre que as vezes trazem qualificacao juridica
    apos o nome (ex.: 'OLIVEIRA TRUST DTVM S.A., instituicao financeira, com sede ...').
    """
    text = normalize_text(value)
    if text is None:
        return None
    return company_key(_FREE_TEXT_CUT.split(text, maxsplit=1)[0])


def only_digits(value, width: int | None = None) -> str | None:
    """ Mantem apenas digitos (CNPJ/CPF). Completa com zeros a esquerda quando `width` e informado. """
    if value is None or pd.isna(value):
        return None
    digits = re.sub(r'\D', '', str(value))
    if not digits:
        return None
    return digits.zfill(width) if width else digits
