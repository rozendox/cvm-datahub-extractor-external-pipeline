"""
Gold: indicadores do mercado de ofertas publicas (Resolucao CVM 160).

Visoes construidas apenas com dados abertos da CVM:

- gold_ofertas_volume_mensal: volume e quantidade de ofertas por mes e tipo de ativo
- gold_ofertas_ranking_coordenadores: league table de coordenadores lideres por ano e classe
- gold_ofertas_perfil_investidor: quem compra cada tipo de ativo (PF, fundos, estrangeiros...)
- gold_securitizacao_painel: painel de CRI/CRA/CR emitidos (substitui info_ativos_cri_cra)
- gold_securitizadoras_ranking: ranking de securitizadoras
- gold_agentes_fiduciarios_ranking: market share de agentes fiduciarios x cadastro CVM
- gold_fundos_gestoras_ranking: gestoras com mais ofertas de fundos x cadastro CVM

Rankings usam apenas ofertas encerradas (negocios concluidos). Volumes sao em R$ (valor registrado).
"""
import pandas as pd

from pipelines.gold.gold_base import (GoldPipelineBase, RegistryMatcher, add_share_and_rank, mode_or_first,
                                      registry_of)
from pipelines.silver.cvm_ofertas_silver import TIPOS_SECURITIZACAO, investor_columns

CATEGORIAS_INVESTIDOR = {
    'pessoa_natural': 'Pessoas físicas',
    'clube_investimento': 'Clubes de investimento',
    'fundos_investimento': 'Fundos de investimento',
    'entidade_previdencia_privada': 'Previdência privada',
    'companhia_seguradora': 'Seguradoras',
    'investidor_estrangeiro': 'Investidores estrangeiros',
    'instit_intermed_partic_consorcio_distrib': 'Instituições do consórcio de distribuição',
    'instit_financ_emissora_partic_consorcio': 'Inst. financeiras ligadas à emissora/consórcio',
    'demais_instit_financ': 'Demais instituições financeiras',
    'demais_pessoa_juridica_emissora_partic_consorcio': 'PJ ligadas à emissora/consórcio',
    'demais_pessoa_juridica': 'Demais pessoas jurídicas',
    'soc_adm_emp_prop_demais_pess_jurid_emiss_partic_consorcio': 'Sócios/administradores ligados à emissora',
}


def volume_mensal(ofertas: pd.DataFrame) -> pd.DataFrame:
    """ Quantidade e volume de ofertas por mes de registro, classe e tipo de ativo. """
    validas = ofertas[ofertas['oferta_valida'] & ofertas['mes_registro'].notna()].copy()
    validas['volume_encerradas'] = validas['valor_total_registrado'].where(validas['oferta_encerrada'])
    df = (validas
          .groupby(['mes_registro', 'classe_ativo', 'tipo_ativo'], as_index=False)
          .agg(qtd_ofertas=('numero_requerimento', 'nunique'),
               volume_registrado=('valor_total_registrado', 'sum'),
               qtd_encerradas=('oferta_encerrada', 'sum'),
               volume_encerradas=('volume_encerradas', 'sum'),
               volume_colocado_estimado=('volume_colocado_estimado', 'sum')))
    df['ticket_medio'] = (df['volume_registrado'] / df['qtd_ofertas']).round(2)
    return df.sort_values(['mes_registro', 'classe_ativo', 'tipo_ativo']).reset_index(drop=True)


def ranking_coordenadores(ofertas: pd.DataFrame) -> pd.DataFrame:
    """ League table de coordenadores lideres por ano e classe de ativo (ofertas encerradas). """
    encerradas = ofertas[ofertas['oferta_encerrada'] & ofertas['cnpj_lider'].notna()]
    df = (encerradas
          .groupby(['ano_registro', 'classe_ativo', 'cnpj_lider'], as_index=False)
          .agg(nome_lider=('nome_lider', mode_or_first),
               qtd_ofertas=('numero_requerimento', 'nunique'),
               volume_total=('valor_total_registrado', 'sum')))
    return add_share_and_rank(df, 'volume_total', ['ano_registro', 'classe_ativo'])


def perfil_investidor(ofertas: pd.DataFrame) -> pd.DataFrame:
    """
    Distribuicao da quantidade subscrita por tipo de investidor, para cada tipo de ativo.
    Considera ofertas encerradas com taxa de colocacao consistente.
    """
    _, qtde_cols = investor_columns(ofertas)
    base = ofertas[ofertas['oferta_encerrada'] & ofertas['taxa_colocacao'].notna()]
    rows = []
    for qtde_col in qtde_cols:
        categoria = qtde_col.removeprefix('qtde_vm_')
        grouped = base.groupby('tipo_ativo').agg(
            qtde_subscrita=(qtde_col, 'sum'),
            num_investidores=(f'num_invest_{categoria}', 'sum'))
        grouped['categoria_investidor'] = CATEGORIAS_INVESTIDOR.get(categoria, categoria)
        rows.append(grouped.reset_index())
    df = pd.concat(rows, ignore_index=True)
    df['participacao'] = (df['qtde_subscrita'] / df.groupby('tipo_ativo')['qtde_subscrita'].transform('sum')).round(4)
    ofertas_por_tipo = base.groupby('tipo_ativo')['numero_requerimento'].nunique().rename('qtd_ofertas_base')
    df = df.merge(ofertas_por_tipo, on='tipo_ativo')
    return (df[df['qtde_subscrita'] > 0]
            .sort_values(['tipo_ativo', 'participacao'], ascending=[True, False])
            .reset_index(drop=True))


SECURITIZACAO_COLUMNS = [
    'numero_requerimento', 'numero_processo', 'tipo_ativo', 'status', 'cnpj_emissor', 'nome_emissor',
    'numero_emissao', 'data_requerimento', 'data_registro', 'data_encerramento', 'dias_distribuicao',
    'valor_total_registrado', 'qtde_total_registrada', 'taxa_colocacao', 'volume_colocado_estimado',
    'tipo_lastro', 'descricao_lastro', 'descricao_garantias', 'identificacao_devedores_coobrigados',
    'agente_fiduciario', 'cnpj_lider', 'nome_lider', 'grupo_coordenador', 'publico_alvo',
    'titulo_incentivado', 'titulo_classificado_como_sustentavel', 'regime_fiduciario',
    'destinacao_recursos', 'mercado_negociacao', 'bookbuilding',
]


def painel_securitizacao(ofertas: pd.DataFrame) -> pd.DataFrame:
    """ Painel analitico de CRI/CRA/CR (uma linha por oferta valida), apenas com dados da CVM. """
    painel = ofertas[ofertas['oferta_valida'] & ofertas['tipo_ativo'].isin(TIPOS_SECURITIZACAO)]
    return painel[SECURITIZACAO_COLUMNS].sort_values('data_registro', ascending=False).reset_index(drop=True)


def ranking_securitizadoras(ofertas: pd.DataFrame) -> pd.DataFrame:
    """ Ranking de securitizadoras por volume de CRI/CRA/CR encerrados. """
    base = ofertas[ofertas['oferta_encerrada'] & ofertas['tipo_ativo'].isin(TIPOS_SECURITIZACAO)].copy()
    base['pulverizado'] = base['tipo_lastro'].map(lambda value: value == 'Pulverizado' if pd.notna(value) else pd.NA)
    for tipo in ['CRI', 'CRA']:
        base[f'volume_{tipo.lower()}'] = base['valor_total_registrado'].where(base['tipo_ativo'] == tipo, 0.0)
    df = (base
          .groupby('cnpj_emissor', as_index=False)
          .agg(nome_emissor=('nome_emissor', mode_or_first),
               qtd_ofertas=('numero_requerimento', 'nunique'),
               qtd_emissoes=('numero_emissao', 'nunique'),
               volume_total=('valor_total_registrado', 'sum'),
               volume_cri=('volume_cri', 'sum'),
               volume_cra=('volume_cra', 'sum'),
               pct_lastro_pulverizado=('pulverizado', lambda s: s.dropna().astype(float).mean())))
    df['pct_lastro_pulverizado'] = df['pct_lastro_pulverizado'].round(4)
    return add_share_and_rank(df, 'volume_total')


def _ranking_with_registry(base: pd.DataFrame, name_column: str, registry: pd.DataFrame,
                           registry_columns: list[str]) -> pd.DataFrame:
    """
    Agrupa ofertas por um prestador de servico informado em texto livre (ex.: agente fiduciario),
    resolvendo as variacoes de grafia para a mesma entidade do cadastro da CVM.
    Nomes nao encontrados no cadastro sao agrupados pela chave normalizada do nome.
    """
    base = base[base[name_column].notna()]
    resolved = RegistryMatcher(registry).resolve(base[name_column], registry_columns)
    base = base.merge(resolved, left_on=name_column, right_on='nome_original', how='left')
    base['nome_exibicao'] = base['nome_cadastro'].fillna(base[name_column])
    df = (base
          .groupby('chave_entidade', as_index=False)
          .agg(nome=('nome_exibicao', mode_or_first),
               variacoes_de_grafia=(name_column, 'nunique'),
               qtd_ofertas=('numero_requerimento', 'nunique'),
               volume_total=('valor_total_registrado', 'sum'),
               tipos_ativo=('tipo_ativo', lambda s: ', '.join(sorted(s.dropna().unique()))),
               **{col: (col, 'first') for col in registry_columns}))
    df['encontrado_no_cadastro'] = df['cnpj'].notna()
    return add_share_and_rank(df, 'volume_total')


def ranking_agentes_fiduciarios(ofertas: pd.DataFrame, participantes: pd.DataFrame) -> pd.DataFrame:
    """ Market share de agentes fiduciarios em ofertas de renda fixa encerradas, com dados cadastrais. """
    base = ofertas[ofertas['oferta_encerrada'] & ofertas['classe_ativo'].eq('renda_fixa')]
    registry = registry_of(participantes, 'agente_fiduciario')
    return _ranking_with_registry(base, 'agente_fiduciario', registry, ['cnpj', 'situacao', 'uf'])


def ranking_gestoras_fundos(ofertas: pd.DataFrame, participantes: pd.DataFrame) -> pd.DataFrame:
    """ Gestoras com mais volume em ofertas de cotas de fundos encerradas, com dados cadastrais. """
    base = ofertas[ofertas['oferta_encerrada'] & ofertas['classe_ativo'].eq('fundos')]
    registry = registry_of(participantes, 'administrador_carteira')
    return _ranking_with_registry(base, 'gestor', registry, ['cnpj', 'categoria', 'situacao', 'uf'])


class OfertasGold(GoldPipelineBase):
    """ Gera as tabelas gold de ofertas publicas. """

    def execute_pipeline(self) -> None:
        ofertas = self.read_silver('cvm_ofertas')
        participantes = self.read_silver('cvm_participantes')

        self.write_gold(volume_mensal(ofertas), 'gold_ofertas_volume_mensal')
        self.write_gold(ranking_coordenadores(ofertas), 'gold_ofertas_ranking_coordenadores')
        self.write_gold(perfil_investidor(ofertas), 'gold_ofertas_perfil_investidor')
        self.write_gold(painel_securitizacao(ofertas), 'gold_securitizacao_painel')
        self.write_gold(ranking_securitizadoras(ofertas), 'gold_securitizadoras_ranking')

        for table, df in [
            ('gold_agentes_fiduciarios_ranking', ranking_agentes_fiduciarios(ofertas, participantes)),
            ('gold_fundos_gestoras_ranking', ranking_gestoras_fundos(ofertas, participantes)),
        ]:
            match_rate = (df['volume_total'] * df['encontrado_no_cadastro']).sum() / df['volume_total'].sum()
            self.logger.info('%s: %.1f%% do volume casado com o cadastro CVM.', table, 100 * match_rate)
            self.write_gold(df, table)
