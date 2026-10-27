""" Testes das transformacoes bronze -> silver. """
import pandas as pd
import pytest

from factories import oferta, ofertas_raw
from pipelines.silver.cvm_fii_silver import keep_latest_version
from pipelines.silver.cvm_ofertas_silver import transform_ofertas
from pipelines.silver.cvm_participantes_silver import situacao_grupo, transform_participantes


def test_transform_ofertas_types_and_classification():
    df = transform_ofertas(ofertas_raw(
        oferta(1, tipo='Certificados de Recebíveis Imobiliários', valor='5000000.04'),
        oferta(2, tipo='Cotas de FIAGRO - FIDC', status='Oferta Revogada'),
        oferta(3, tipo='Ações', status='Registro Concedido'),
    ))
    assert df['tipo_ativo'].tolist() == ['CRI', 'FIAGRO-FIDC', 'ACOES']
    assert df['classe_ativo'].tolist() == ['renda_fixa', 'fundos', 'renda_variavel']
    assert df['valor_total_registrado'].iloc[0] == pytest.approx(5000000.04)
    assert df['oferta_valida'].tolist() == [True, False, True]
    assert df['oferta_encerrada'].tolist() == [True, False, False]
    assert df['numero_emissao'].iloc[0] == '1'
    assert df['cnpj_lider'].iloc[0] == '11111111000111'
    assert df['mes_registro'].iloc[0] == pd.Timestamp('2025-03-01')
    assert df['dias_distribuicao'].iloc[0] == 31


def test_transform_ofertas_placement_rate_flags_inconsistent_units():
    df = transform_ofertas(ofertas_raw(
        oferta(1, qtde='1000', pf='200', fundos='600'),       # 80% colocado
        oferta(2, qtde='1000', pf='0', fundos='5000000'),     # unidade inconsistente
        oferta(3, qtde='1000', status='Registro Concedido'),  # ainda em distribuicao
    ))
    assert df['taxa_colocacao'].iloc[0] == pytest.approx(0.8)
    assert df['volume_colocado_estimado'].iloc[0] == pytest.approx(800000.0)
    assert bool(df['taxa_colocacao_inconsistente'].iloc[1]) is True
    assert pd.isna(df['taxa_colocacao'].iloc[1])
    assert pd.isna(df['qtde_colocada'].iloc[2])


@pytest.mark.parametrize('situacao, grupo', [
    ('EM FUNCIONAMENTO NORMAL', 'ATIVO'),
    ('Em Funcionamento Normal', 'ATIVO'),
    ('CANCELADA', 'CANCELADO'),
    ('SUSPENSO(A) - A PEDIDO', 'SUSPENSO'),
    ('Em Análise', 'EM_ANALISE'),
    ('LIQUIDAÇÃO EXTRAJUDICIAL', 'OUTROS'),
    (None, None),
])
def test_situacao_grupo(situacao, grupo):
    assert situacao_grupo(situacao) == grupo


def test_transform_participantes_maps_different_layouts():
    pf = transform_participantes(pd.DataFrame({'AUDITOR': ['Fulano'], 'SIT': ['ATIVO'], 'DT_INI_SIT': ['2020-01-02']})
                                 .astype('string'), 'auditor_independente', 'PF')
    pj = transform_participantes(pd.DataFrame({'CNPJ': ['1.234.567/0001-89'], 'DENOM_SOCIAL': ['Empresa SA'],
                                               'SIT': ['CANCELADA'], 'DT_REG': ['2001-05-06'], 'UF': ['sp']})
                                 .astype('string'), 'agente_autonomo', 'PJ')
    assert pf['nome'].iloc[0] == 'Fulano' and pd.isna(pf['cnpj'].iloc[0])
    assert pj['cnpj'].iloc[0] == '01234567000189'
    assert pj['uf'].iloc[0] == 'SP'
    assert pj['situacao_grupo'].iloc[0] == 'CANCELADO'
    assert pj['data_registro'].iloc[0] == pd.Timestamp('2001-05-06')
    assert list(pf.columns) == list(pj.columns)


def test_keep_latest_version_of_each_report():
    df = pd.DataFrame({
        'cnpj_fundo_classe': ['A', 'A', 'B'],
        'data_referencia': pd.to_datetime(['2025-12-01'] * 3),
        'versao': [1.0, 2.0, 1.0],
        'valor': [10.0, 20.0, 30.0],
    })
    assert keep_latest_version(df)['valor'].tolist() == [20.0, 30.0]
