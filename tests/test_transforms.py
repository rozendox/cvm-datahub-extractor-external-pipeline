""" Testes das funcoes de padronizacao da silver. """
import pandas as pd

from pipelines.silver.transforms import standardize_columns, to_date, to_flag, to_number


def test_to_number_keeps_cvm_decimal_point():
    # Regressao: o pipeline antigo removia o '.' e dividia por 10, inflando em 10x
    # qualquer valor com 2 casas decimais (5000000.04 virava 50000000.4).
    result = to_number(pd.Series(['5000000.04', '1400000000.0', '176000']))
    assert result.tolist() == [5000000.04, 1400000000.0, 176000.0]


def test_to_number_accepts_brazilian_format_and_invalid_values():
    result = to_number(pd.Series(['1.234.567,89', '', None, 'abc']))
    assert result.iloc[0] == 1234567.89
    assert result.iloc[1:].isna().all()


def test_to_date_iso_brazilian_and_placeholder():
    result = to_date(pd.Series(['2025-06-01', '15/03/2024', '1899-12-31', None]))
    assert result.iloc[0] == pd.Timestamp('2025-06-01')
    assert result.iloc[1] == pd.Timestamp('2024-03-15')
    assert result.iloc[2:].isna().all()


def test_to_flag():
    assert to_flag(pd.Series(['S', 'N', None])).tolist() == [True, False, pd.NA]


def test_standardize_columns_fixes_cvm_typo():
    df = standardize_columns(pd.DataFrame(columns=['Qdte_VM_Soc_Adm', 'Num_Invest_Pessoa_Natural']))
    assert list(df.columns) == ['qtde_vm_soc_adm', 'num_invest_pessoa_natural']
