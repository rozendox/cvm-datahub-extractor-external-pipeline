""" Testes das tabelas analiticas da gold. """
import pandas as pd
import pytest

from factories import oferta, ofertas_raw, participante
from pipelines.gold.ofertas_gold import ranking_agentes_fiduciarios, ranking_coordenadores, volume_mensal
from pipelines.gold.participantes_gold import evolucao_anual
from pipelines.silver.cvm_ofertas_silver import transform_ofertas


@pytest.fixture(name='participantes')
def fixture_participantes():
    return pd.DataFrame([
        participante('agente_fiduciario', 'OLIVEIRA TRUST DTVM S.A.', cnpj='36113876000191'),
        participante('agente_fiduciario', 'Pentágono S.A. Distribuidora de Títulos e Valores Mobiliários',
                     cnpj='17343682000138'),
        participante('agente_fiduciario', 'PENTAGONO ANTIGA LTDA', cnpj='17343682000100', situacao='CANCELADA'),
    ])


def test_volume_mensal_ignores_invalid_offers():
    ofertas = transform_ofertas(ofertas_raw(
        oferta(1, valor='100.0'),
        oferta(2, valor='300.0', status='Registro Concedido'),
        oferta(3, valor='999.0', status='Registro Caducado'),
    ))
    row = volume_mensal(ofertas).iloc[0]
    assert row['qtd_ofertas'] == 2
    assert row['volume_registrado'] == 400.0
    assert row['volume_encerradas'] == 100.0


def test_ranking_coordenadores_shares_sum_to_one():
    ofertas = transform_ofertas(ofertas_raw(
        oferta(1, valor='300.0', lider='Banco A', cnpj_lider='11.111.111/0001-11'),
        oferta(2, valor='100.0', lider='Banco B', cnpj_lider='22.111.111/0001-11'),
        oferta(3, valor='100.0', lider='BANCO A S.A.', cnpj_lider='11.111.111/0001-11'),
        oferta(4, valor='50.0', lider='Banco A', cnpj_lider='11.111.111/0001-11'),
    ))
    ranking = ranking_coordenadores(ofertas)
    assert ranking['market_share'].sum() == pytest.approx(1.0)
    # Agrupa pelo CNPJ e exibe a grafia mais frequente
    assert ranking.iloc[0][['nome_lider', 'qtd_ofertas', 'ranking']].tolist() == ['Banco A', 3, 1]


def test_ranking_agentes_fiduciarios_resolves_spelling_variants(participantes):
    ofertas = transform_ofertas(ofertas_raw(
        oferta(1, agente='OLIVEIRA TRUST DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS S.A.'),
        oferta(2, agente='Oliveira Trust'),  # prefixo unico no cadastro
        oferta(3, agente='Oliveira Trust Dtvm S/A, inscrita no CNPJ sob o nº 36.113.876/0004-34'),
        oferta(4, agente='PENTAGONO DTVM'),  # deve casar com o registro ativo, nao com o cancelado
        oferta(5, agente='Agente Desconhecido Ltda'),
    ))
    ranking = ranking_agentes_fiduciarios(ofertas, participantes).set_index('nome')

    oliveira = ranking.loc['OLIVEIRA TRUST DTVM S.A.']
    assert oliveira['qtd_ofertas'] == 3
    assert oliveira['variacoes_de_grafia'] == 3
    assert oliveira['cnpj'] == '36113876000191'

    assert ranking.loc['Pentágono S.A. Distribuidora de Títulos e Valores Mobiliários', 'cnpj'] == '17343682000138'
    assert not ranking.loc['Agente Desconhecido Ltda', 'encontrado_no_cadastro']


def test_evolucao_anual_accumulates_active_base():
    df = pd.DataFrame([
        {**participante('agente_autonomo', 'A', data_registro='2020-01-01'), 'data_cancelamento': pd.NaT,
         'data_inicio_situacao': pd.NaT},
        {**participante('agente_autonomo', 'B', data_registro='2020-06-01', situacao='CANCELADA'),
         'data_cancelamento': pd.NaT, 'data_inicio_situacao': pd.Timestamp('2021-03-01')},
    ])
    result = evolucao_anual(df).set_index('ano')
    assert result.loc[2020, ['novos_registros', 'cancelamentos', 'base_ativa_acumulada']].tolist() == [2, 0, 2]
    assert result.loc[2021, ['novos_registros', 'cancelamentos', 'base_ativa_acumulada']].tolist() == [0, 1, 1]
