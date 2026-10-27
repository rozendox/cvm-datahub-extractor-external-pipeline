"""
Gold: panorama dos Fundos de Investimento Imobiliario a partir do informe anual.

- gold_fii_segmentos: fundos e valor contabil dos ativos por segmento de atuacao
- gold_fii_administradores_ranking: administradores por numero de fundos e valor contabil,
  cruzados por CNPJ com o cadastro de administradores de carteira da CVM
- gold_fii_transacoes_mensais: aquisicoes x alienacoes de ativos ao longo do exercicio

Cada fundo entra com o informe mais recente do exercicio (alguns entregam semestralmente).
"""
import pandas as pd

from pipelines.gold.gold_base import GoldPipelineBase, add_share_and_rank, mode_or_first, prefer_active


def latest_informes(geral: pd.DataFrame) -> pd.DataFrame:
    """ Ultimo informe de cada fundo/classe no exercicio. """
    latest = geral.groupby('cnpj_fundo_classe')['data_referencia'].transform('max')
    return geral[geral['data_referencia'] == latest].drop_duplicates('cnpj_fundo_classe')


def valor_contabil_por_fundo(valor_contabil: pd.DataFrame) -> pd.DataFrame:
    """ Soma do valor contabil dos ativos de cada informe (fundo + data de referencia). """
    return (valor_contabil
            .groupby(['cnpj_fundo_classe', 'data_referencia'], as_index=False)
            .agg(valor_contabil_ativos=('valor', 'sum'), qtd_ativos=('nome_ativo', 'count')))


def _fundos_com_valor(geral: pd.DataFrame, valor_contabil: pd.DataFrame) -> pd.DataFrame:
    fundos = latest_informes(geral)
    fundos = fundos.merge(valor_contabil_por_fundo(valor_contabil),
                          on=['cnpj_fundo_classe', 'data_referencia'], how='left')
    fundos['valor_contabil_ativos'] = fundos['valor_contabil_ativos'].fillna(0.0)
    fundos['qtd_ativos'] = fundos['qtd_ativos'].fillna(0).astype('Int64')
    return fundos


def segmentos(geral: pd.DataFrame, valor_contabil: pd.DataFrame) -> pd.DataFrame:
    """ Numero de fundos, valor contabil e perfil de gestao por segmento de atuacao. """
    fundos = _fundos_com_valor(geral, valor_contabil)
    fundos['segmento_atuacao'] = fundos['segmento_atuacao'].fillna('NAO INFORMADO')
    fundos['gestao_ativa'] = fundos['tipo_gestao'].eq('ATIVA')
    df = (fundos
          .groupby('segmento_atuacao', as_index=False)
          .agg(qtd_fundos=('cnpj_fundo_classe', 'nunique'),
               qtd_ativos_imobiliarios=('qtd_ativos', 'sum'),
               valor_contabil_ativos=('valor_contabil_ativos', 'sum'),
               pct_gestao_ativa=('gestao_ativa', 'mean')))
    df['pct_gestao_ativa'] = df['pct_gestao_ativa'].round(4)
    df['pct_fundos'] = (df['qtd_fundos'] / df['qtd_fundos'].sum()).round(4)
    return add_share_and_rank(df, 'valor_contabil_ativos', share_column='pct_valor_contabil')


def ranking_administradores(geral: pd.DataFrame, valor_contabil: pd.DataFrame,
                            participantes: pd.DataFrame) -> pd.DataFrame:
    """
    Administradores de FII por quantidade de fundos e valor contabil dos ativos.

    O cruzamento com o cadastro e feito por CNPJ (chave exata) contra o cadastro de
    administradores de carteira: o antigo cadastro especifico de administradores de FII
    (cad_adm_fii) esta integralmente cancelado desde a Resolucao CVM 175.
    """
    fundos = _fundos_com_valor(geral, valor_contabil)
    df = (fundos[fundos['cnpj_administrador'].notna()]
          .groupby('cnpj_administrador', as_index=False)
          .agg(nome_administrador=('nome_administrador', mode_or_first),
               qtd_fundos=('cnpj_fundo_classe', 'nunique'),
               valor_contabil_ativos=('valor_contabil_ativos', 'sum')))
    df['pct_fundos'] = (df['qtd_fundos'] / df['qtd_fundos'].sum()).round(4)

    registry = (prefer_active(participantes[(participantes['tipo_participante'] == 'administrador_carteira')
                                            & participantes['cnpj'].notna()])
                .drop_duplicates('cnpj')
                [['cnpj', 'categoria', 'situacao', 'uf']]
                .rename(columns={'cnpj': 'cnpj_administrador', 'categoria': 'categoria_cvm',
                                 'situacao': 'situacao_cvm', 'uf': 'uf'}))
    df = df.merge(registry, on='cnpj_administrador', how='left')
    df['encontrado_no_cadastro'] = df['situacao_cvm'].notna()
    return add_share_and_rank(df, 'valor_contabil_ativos', share_column='pct_valor_contabil')


def transacoes_mensais(transacoes: pd.DataFrame) -> pd.DataFrame:
    """
    Aquisicoes, alienacoes e locacoes de ativos por mes, restritas ao exercicio do informe
    (descarta datas de transacao fora do ano de referencia, comuns como placeholder).
    """
    validas = transacoes[transacoes['data_transacao'].dt.year == transacoes['ano_referencia']].copy()
    validas['mes_transacao'] = validas['data_transacao'].dt.to_period('M').dt.to_timestamp()
    df = (validas
          .groupby(['mes_transacao', 'natureza_transacao'], as_index=False)
          .agg(qtd_transacoes=('ativo_negociado', 'count'),
               qtd_fundos=('cnpj_fundo_classe', 'nunique'),
               valor_total=('valor_envolvido', 'sum')))
    return df.sort_values(['mes_transacao', 'natureza_transacao']).reset_index(drop=True)


class FiiGold(GoldPipelineBase):
    """ Gera as tabelas gold de FII. """

    def execute_pipeline(self) -> None:
        geral = self.read_silver('cvm_fii_geral')
        valor_contabil = self.read_silver('cvm_fii_ativo_valor_contabil')
        transacoes = self.read_silver('cvm_fii_ativo_transacao')
        participantes = self.read_silver('cvm_participantes')

        self.write_gold(segmentos(geral, valor_contabil), 'gold_fii_segmentos')

        administradores = ranking_administradores(geral, valor_contabil, participantes)
        self.logger.info('Administradores de FII encontrados no cadastro CVM: %s de %s.',
                         int(administradores['encontrado_no_cadastro'].sum()), len(administradores))
        self.write_gold(administradores, 'gold_fii_administradores_ranking')

        self.write_gold(transacoes_mensais(transacoes), 'gold_fii_transacoes_mensais')
