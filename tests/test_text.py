""" Testes de normalizacao de texto e documentos. """
from utils.text import company_key, extract_cnpj_root, free_text_company_key, only_digits, to_snake_case


def test_to_snake_case_removes_accents_and_symbols():
    assert to_snake_case('Valor_Total_Registrado') == 'valor_total_registrado'
    assert to_snake_case('Patrimônio Líquido (R$)') == 'patrimonio_liquido_r'


def test_company_key_unifies_spelling_variants():
    variants = [
        'OLIVEIRA TRUST DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A.',
        'Oliveira Trust Distribuidora de Títulos e Valores Mobiliários S.A.',
        'OLIVEIRA TRUST DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS SA',
        'OLIVEIRA TRUST DTVM S/A',
        'OLIVEIRA TRUST DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOSS.A.',
    ]
    assert {company_key(v) for v in variants} == {'OLIVEIRA TRUST DTVM'}


def test_company_key_removes_sa_in_the_middle_and_singular_typo():
    assert company_key('Pentágono S.A. Distribuidora de Títulos e Valores Mobiliário') == 'PENTAGONO DTVM'


def test_free_text_company_key_ignores_legal_qualification():
    text = ('PENTÁGONO S.A. DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS, instituição financeira, '
            'com sede na cidade do Rio de Janeiro, inscrita no CNPJ/MF sob o nº 17.343.682/0001-38')
    assert free_text_company_key(text) == 'PENTAGONO DTVM'


def test_extract_cnpj_root_from_free_text():
    assert extract_cnpj_root('VÓRTX DTVM LTDA. - CNPJ: 22.610.500/0001-88') == '22610500'
    assert extract_cnpj_root('inscrita no CNPJ sob o nº 36.113.876/0001 91') == '36113876'
    assert extract_cnpj_root('Oliveira Trust') is None


def test_only_digits_pads_cnpj():
    assert only_digits('7.047.251/0001-70', width=14) == '07047251000170'
    assert only_digits(None) is None
