"""
Gold: participantes do mercado regulados pela CVM.

- gold_participantes_uf: distribuicao geografica (pessoas juridicas) por tipo e situacao
- gold_participantes_evolucao_anual: novos registros x cancelamentos por ano e saldo acumulado
"""
import pandas as pd

from pipelines.gold.gold_base import GoldPipelineBase


def por_uf(participantes: pd.DataFrame) -> pd.DataFrame:
    """ Quantidade de participantes PJ por tipo, UF e grupo de situacao cadastral. """
    pj = participantes[participantes['tipo_pessoa'].eq('PJ')].copy()
    pj['uf'] = pj['uf'].fillna('NI')
    df = (pj
          .groupby(['tipo_participante', 'uf', 'situacao_grupo'], as_index=False, dropna=False)
          .size()
          .rename(columns={'size': 'quantidade'}))
    ativos = df[df['situacao_grupo'] == 'ATIVO']
    total_ativos = ativos.groupby('tipo_participante')['quantidade'].transform('sum')
    df['pct_ativos_do_tipo'] = (ativos['quantidade'] / total_ativos).round(4)
    return df.sort_values(['tipo_participante', 'quantidade'], ascending=[True, False]).reset_index(drop=True)


def evolucao_anual(participantes: pd.DataFrame) -> pd.DataFrame:
    """
    Novos registros e cancelamentos por ano e tipo de participante.

    O saldo acumulado reconstroi a base ativa ao longo do tempo. Quando a data de
    cancelamento nao e informada, usa-se a data de inicio da situacao 'cancelado'.
    Cadastros sem data de registro (ex.: auditores) ficam de fora.
    """
    base = participantes[participantes['data_registro'].notna()].copy()
    cancelado = base['situacao_grupo'].eq('CANCELADO')
    base['data_saida'] = base['data_cancelamento'].where(
        base['data_cancelamento'].notna() | ~cancelado, base['data_inicio_situacao'])

    registros = (base.assign(ano=base['data_registro'].dt.year)
                 .groupby(['tipo_participante', 'ano']).size().rename('novos_registros'))
    saidas = base[base['data_saida'].notna()]
    cancelamentos = (saidas.assign(ano=saidas['data_saida'].dt.year)
                     .groupby(['tipo_participante', 'ano']).size().rename('cancelamentos'))

    df = pd.concat([registros, cancelamentos], axis=1).fillna(0).astype('int64').reset_index()
    df = df.sort_values(['tipo_participante', 'ano']).reset_index(drop=True)
    df['saldo_liquido'] = df['novos_registros'] - df['cancelamentos']
    df['base_ativa_acumulada'] = df.groupby('tipo_participante')['saldo_liquido'].cumsum()
    return df


class ParticipantesGold(GoldPipelineBase):
    """ Gera as tabelas gold de participantes do mercado. """

    def execute_pipeline(self) -> None:
        participantes = self.read_silver('cvm_participantes')
        self.write_gold(por_uf(participantes), 'gold_participantes_uf')
        self.write_gold(evolucao_anual(participantes), 'gold_participantes_evolucao_anual')
