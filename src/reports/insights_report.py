"""
Relatorio de insights em Markdown gerado a partir da camada gold.

Todos os numeros e frases sao calculados a cada execucao: o relatorio nunca fica
desatualizado em relacao aos dados do lake.
"""
import os
from datetime import datetime

import pandas as pd

from lake.lake import GOLD, SILVER, Lake
from pipelines.shared.pipeline_base import PipelineBase

TIPO_PARTICIPANTE_LABEL = {
    'administrador_carteira': 'Gestoras e administradores fiduciários',
    'administrador_fii': 'Administradores de FII (cadastro legado)',
    'agente_autonomo': 'Assessores de investimento (AAI)',
    'agente_fiduciario': 'Agentes fiduciários',
    'auditor_independente': 'Auditores independentes',
    'consultor_valores_mobiliarios': 'Consultores de valores mobiliários',
    'plataforma_crowdfunding': 'Plataformas de crowdfunding',
}


def brl(value: float) -> str:
    """ Formata valores em reais de forma compacta (ex.: R$ 1,2 bi). """
    if pd.isna(value):
        return '-'
    for divisor, suffix, decimals in [(1e12, 'tri', 2), (1e9, 'bi', 1), (1e6, 'mi', 1)]:
        if abs(value) >= divisor:
            return f'R$ {value / divisor:,.{decimals}f} {suffix}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {value:,.0f}'.replace(',', '.')


def pct(value: float, decimals: int = 1) -> str:
    """ Formata uma fracao como percentual (0.123 -> 12,3%). """
    if pd.isna(value):
        return '-'
    return f'{100 * value:.{decimals}f}%'.replace('.', ',')


def integer(value) -> str:
    """ Formata inteiros com separador de milhar. """
    return f'{int(value):,}'.replace(',', '.')


def md_table(df: pd.DataFrame) -> str:
    """ Converte um DataFrame (ja formatado como texto) em tabela Markdown. """
    header = '| ' + ' | '.join(df.columns) + ' |'
    divider = '|' + '|'.join('---' for _ in df.columns) + '|'
    rows = ['| ' + ' | '.join(str(value) for value in row) + ' |' for row in df.itertuples(index=False)]
    return '\n'.join([header, divider, *rows])


class InsightsReport(PipelineBase):
    """ Gera docs/INSIGHTS.md a partir das tabelas gold. """

    def __init__(self, lake: Lake, output_path: str):
        super().__init__()
        self.lake = lake
        self.output_path = output_path

    def gold(self, table: str) -> pd.DataFrame:
        """ Le uma tabela da gold. """
        return self.lake.read_table(GOLD, table)

    # Secoes

    def section_ofertas(self) -> tuple[list[str], int]:
        volume = self.gold('gold_ofertas_volume_mensal')
        volume['ano'] = volume['mes_registro'].dt.year
        months_per_year = volume.groupby('ano')['mes_registro'].nunique()
        complete_years = months_per_year[months_per_year == 12].index
        last_year = int(complete_years.max())

        por_ano = volume.pivot_table(index='ano', columns='classe_ativo', values='volume_encerradas',
                                     aggfunc='sum', fill_value=0)
        por_ano['total'] = por_ano.sum(axis=1)
        qtd = volume.groupby('ano')['qtd_encerradas'].sum()
        table = pd.DataFrame({
            'Ano': por_ano.index.astype(str) + ['' if y in complete_years else ' (parcial)' for y in por_ano.index],
            'Ofertas encerradas': [integer(qtd[y]) for y in por_ano.index],
            'Renda fixa': por_ano.get('renda_fixa', 0).map(brl).values,
            'Fundos': por_ano.get('fundos', 0).map(brl).values,
            'Renda variável': por_ano.get('renda_variavel', 0).map(brl).values,
            'Total': por_ano['total'].map(brl).values,
        })

        previous = por_ano.loc[last_year - 1, 'total'] if last_year - 1 in por_ano.index else None
        growth = por_ano.loc[last_year, 'total'] / previous - 1 if previous else None

        tipos = (volume[volume['ano'] == last_year].groupby('tipo_ativo')['volume_encerradas'].sum()
                 .sort_values(ascending=False))
        share_tipos = tipos / tipos.sum()
        top_tipos = ', '.join(f'**{tipo}** ({pct(share)})' for tipo, share in share_tipos.head(4).items())

        lines = [
            '## 1. Mercado de ofertas públicas (Resolução CVM 160)',
            '',
            'Volume registrado das ofertas **encerradas**, por ano de registro. '
            f'Base: {integer(volume["qtd_ofertas"].sum())} '
            'ofertas válidas desde jan/2023 (início da Resolução 160).',
            '',
            md_table(table),
            '',
        ]
        if growth is not None:
            direction = 'cresceu' if growth >= 0 else 'caiu'
            lines.append(f'- Em {last_year}, o volume de ofertas encerradas {direction} **{pct(abs(growth))}** '
                         f'em relação a {last_year - 1}.')
        lines.append(f'- Ativos com maior volume em {last_year}: {top_tipos}.')
        lines.append('')
        return lines, last_year

    def section_coordenadores(self, year: int) -> list[str]:
        ranking = self.gold('gold_ofertas_ranking_coordenadores')
        lines = ['## 2. Quem lidera as ofertas (league table de coordenadores)', '']
        for classe, label in [('renda_fixa', 'Renda fixa'), ('fundos', 'Cotas de fundos')]:
            top = ranking[(ranking['ano_registro'] == year) & (ranking['classe_ativo'] == classe)].head(5)
            if top.empty:
                continue
            lines += [
                f'**{label} - {year}** (top 3 concentram {pct(top["market_share"].head(3).sum())} do volume)',
                '',
                md_table(pd.DataFrame({
                    '#': top['ranking'].astype(str),
                    'Coordenador líder': top['nome_lider'],
                    'Ofertas': top['qtd_ofertas'].map(integer),
                    'Volume': top['volume_total'].map(brl),
                    'Market share': top['market_share'].map(pct),
                })),
                '',
            ]
        return lines

    def section_investidores(self) -> list[str]:
        perfil = self.gold('gold_ofertas_perfil_investidor')
        lines = [
            '## 3. Quem compra cada ativo',
            '',
            'Participação de cada tipo de investidor na quantidade subscrita das ofertas encerradas.',
            '',
        ]
        rows = []
        for tipo in ['DEBENTURE', 'CRI', 'CRA', 'NOTA_COMERCIAL', 'FII', 'FIDC', 'FIAGRO']:
            subset = perfil[perfil['tipo_ativo'] == tipo].head(3)
            if subset.empty:
                continue
            ranking = '; '.join(f'{row.categoria_investidor} ({pct(row.participacao)})'
                                for row in subset.itertuples())
            pf = perfil[(perfil['tipo_ativo'] == tipo) & (perfil['categoria_investidor'] == 'Pessoas físicas')]
            rows.append({'Ativo': tipo, 'Ofertas na base': integer(subset['qtd_ofertas_base'].iloc[0]),
                         'Top 3 compradores': ranking,
                         'Pessoas físicas': pct(pf['participacao'].iloc[0]) if not pf.empty else '-'})
        lines += [md_table(pd.DataFrame(rows)), '']
        return lines

    def section_securitizacao(self) -> list[str]:
        securitizadoras = self.gold('gold_securitizadoras_ranking').head(5)
        fiduciarios = self.gold('gold_agentes_fiduciarios_ranking')
        match_volume = (fiduciarios['volume_total'] * fiduciarios['encontrado_no_cadastro']).sum() / \
            fiduciarios['volume_total'].sum()
        variacoes = int(fiduciarios.head(3)['variacoes_de_grafia'].sum())
        top_fiduciarios = fiduciarios.head(3)
        return [
            '## 4. Securitização e agentes fiduciários',
            '',
            '**Securitizadoras** (CRI, CRA e CR encerrados desde 2023)',
            '',
            md_table(pd.DataFrame({
                '#': securitizadoras['ranking'].astype(str),
                'Securitizadora': securitizadoras['nome_emissor'],
                'Ofertas': securitizadoras['qtd_ofertas'].map(integer),
                'Volume': securitizadoras['volume_total'].map(brl),
                'Market share': securitizadoras['market_share'].map(pct),
                'Lastro pulverizado': securitizadoras['pct_lastro_pulverizado'].map(pct),
            })),
            '',
            f'**Agentes fiduciários**: os 3 maiores concentram **{pct(top_fiduciarios["market_share"].sum())}** '
            'do volume de renda fixa encerrado: ' +
            ', '.join(f'{row.nome} ({pct(row.market_share)})' for row in top_fiduciarios.itertuples()) + '.',
            '',
            '- O campo de agente fiduciário é texto livre: só os 3 líderes aparecem com '
            f'**{integer(variacoes)} grafias diferentes**. A resolução de entidades '
            '(CNPJ citado no texto, razão social, nome comercial e prefixo único) '
            f'casa **{pct(match_volume)}** do volume com o cadastro oficial da CVM.',
            '',
        ]

    def section_gestoras(self) -> list[str]:
        gestoras = self.gold('gold_fundos_gestoras_ranking')
        match_volume = (gestoras['volume_total'] * gestoras['encontrado_no_cadastro']).sum() / \
            gestoras['volume_total'].sum()
        top = gestoras.head(8)
        return [
            '## 5. Gestoras com mais ofertas de fundos',
            '',
            f'Cotas de FII, FIDC, FIP, FIF, FIAGRO e FI-Infra encerradas desde 2023. '
            f'{len(gestoras)} gestoras distintas; o top 10 responde por {pct(gestoras.head(10)["market_share"].sum())} '
            f'do volume. {pct(match_volume)} do volume foi casado com o cadastro de administradores '
            'de carteira da CVM.',
            '',
            md_table(pd.DataFrame({
                '#': top['ranking'].astype(str),
                'Gestora': top['nome'],
                'Ofertas': top['qtd_ofertas'].map(integer),
                'Volume': top['volume_total'].map(brl),
                'Market share': top['market_share'].map(pct),
                'Tipos de fundo': top['tipos_ativo'],
            })),
            '',
        ]

    def section_fii(self) -> list[str]:
        segmentos = self.gold('gold_fii_segmentos')
        administradores = self.gold('gold_fii_administradores_ranking')
        transacoes = self.gold('gold_fii_transacoes_mensais')
        geral = self.lake.read_table(SILVER, 'cvm_fii_geral')
        ano = int(geral['ano_referencia'].max())

        totais = transacoes.groupby('natureza_transacao')['valor_total'].sum()
        aquisicao, alienacao = totais.get('AQUISICAO', 0.0), totais.get('ALIENACAO', 0.0)
        top_adm = administradores.head(5)
        nao_encontrados = int((~administradores['encontrado_no_cadastro']).sum())
        return [
            f'## 6. Fundos imobiliários (informe anual {ano})',
            '',
            f'{integer(segmentos["qtd_fundos"].sum())} FIIs/classes reportaram '
            f'{brl(segmentos["valor_contabil_ativos"].sum())} '
            'em valor contábil de ativos imobiliários.',
            '',
            md_table(pd.DataFrame({
                'Segmento': segmentos['segmento_atuacao'],
                'Fundos': segmentos['qtd_fundos'].map(integer),
                '% fundos': segmentos['pct_fundos'].map(pct),
                'Valor contábil': segmentos['valor_contabil_ativos'].map(brl),
                '% valor': segmentos['pct_valor_contabil'].map(pct),
                'Gestão ativa': segmentos['pct_gestao_ativa'].map(pct),
            })),
            '',
            f'**Administradores**: os 5 maiores somam {pct(top_adm["pct_valor_contabil"].sum())} do valor contábil.',
            '',
            md_table(pd.DataFrame({
                '#': top_adm['ranking'].astype(str),
                'Administrador': top_adm['nome_administrador'],
                'Fundos': top_adm['qtd_fundos'].map(integer),
                'Valor contábil': top_adm['valor_contabil_ativos'].map(brl),
                '% valor': top_adm['pct_valor_contabil'].map(pct),
            })),
            '',
            f'- Transações no exercício: {brl(aquisicao)} em aquisições contra {brl(alienacao)} em alienações '
            f'(saldo comprador de {brl(aquisicao - alienacao)}).',
            f'- {nao_encontrados} de {len(administradores)} administradores informados nos informes não têm CNPJ no '
            'cadastro de administradores de carteira; o cadastro específico de administradores de FII (cad_adm_fii) '
            'está 100% cancelado e não serve mais como referência.',
            '',
        ]

    def section_participantes(self) -> list[str]:
        evolucao = self.gold('gold_participantes_evolucao_anual')
        uf = self.gold('gold_participantes_uf')
        current_year = datetime.now().year

        aai = evolucao[(evolucao['tipo_participante'] == 'agente_autonomo') & (evolucao['ano'] >= current_year - 6)]
        pico = aai.loc[aai['novos_registros'].idxmax()]
        saldo_pos_pico = aai[aai['ano'] > pico['ano']]['saldo_liquido']
        tendencia = ''
        if len(saldo_pos_pico) >= 2 and saldo_pos_pico.is_monotonic_decreasing:
            tendencia = ' Desde então o saldo líquido encolhe ano a ano'
            negativos = aai[aai['saldo_liquido'] < 0]['ano']
            if not negativos.empty:
                tendencia += f' e em {int(negativos.min())} os cancelamentos superaram os novos registros'
            tendencia += '.'

        ativos = uf[uf['situacao_grupo'] == 'ATIVO']
        concentration = []
        for tipo, group in ativos.groupby('tipo_participante'):
            share_sp_rj = group[group['uf'].isin(['SP', 'RJ'])]['quantidade'].sum() / group['quantidade'].sum()
            concentration.append({'Participante (PJ ativo)': TIPO_PARTICIPANTE_LABEL.get(tipo, tipo),
                                  'Quantidade': integer(group['quantidade'].sum()),
                                  'SP + RJ': pct(share_sp_rj),
                                  'Maior UF fora do eixo': group[~group['uf'].isin(['SP', 'RJ'])]
                                  .sort_values('quantidade', ascending=False)['uf'].head(1).str.cat()})
        return [
            '## 7. Participantes do mercado',
            '',
            '**Assessores de investimento (AAI)**: registros e cancelamentos por ano.',
            '',
            md_table(pd.DataFrame({
                'Ano': aai['ano'].astype(str) + [' (parcial)' if a == current_year else '' for a in aai['ano']],
                'Novos registros': aai['novos_registros'].map(integer),
                'Cancelamentos': aai['cancelamentos'].map(integer),
                'Saldo': aai['saldo_liquido'].map(integer),
            })),
            '',
            f'- O pico de novos assessores foi em {int(pico["ano"])} ({integer(pico["novos_registros"])} registros).'
            f'{tendencia}',
            '',
            '**Concentração geográfica** (pessoas jurídicas em funcionamento):',
            '',
            md_table(pd.DataFrame(concentration)),
            '',
        ]

    def section_qualidade(self) -> list[str]:
        ofertas = self.lake.read_table(SILVER, 'cvm_ofertas')
        encerradas = ofertas[ofertas['oferta_encerrada']]
        inconsistentes = int(ofertas['taxa_colocacao_inconsistente'].sum())
        outros = int((ofertas['classe_ativo'] == 'outros').sum())
        return [
            '## 8. Qualidade de dados observada',
            '',
            f'- **{integer(inconsistentes)}** de {integer(len(encerradas))} ofertas encerradas '
            f'({pct(inconsistentes / len(encerradas))}) têm quantidade subscrita por investidores maior que 105% da '
            'quantidade registrada (unidades inconsistentes entre campos). Elas ficam fora das métricas de colocação.',
            f'- {integer(outros)} ofertas com valor mobiliário não mapeado (classe "outros").',
            '- Datas placeholder (ex.: 1899-12-31) nas transações de FII são descartadas na silver.',
            '- Prestadores de serviço (agente fiduciário, gestor) são texto livre: ver match rates nas seções 4 e 5.',
            '',
        ]

    def execute_pipeline(self) -> None:
        sections, last_year = self.section_ofertas()
        content = [
            '# Insights: mercado de capitais brasileiro (dados abertos da CVM)',
            '',
            f'> Gerado automaticamente em {datetime.now():%d/%m/%Y %H:%M} a partir da camada gold '
            f'(`{self.lake.root}`). Não edite manualmente: rode `python src/main.py --layers report`.',
            '',
            *sections,
            *self.section_coordenadores(last_year),
            *self.section_investidores(),
            *self.section_securitizacao(),
            *self.section_gestoras(),
            *self.section_fii(),
            *self.section_participantes(),
            *self.section_qualidade(),
        ]
        os.makedirs(os.path.dirname(self.output_path) or '.', exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as file:
            file.write('\n'.join(content))
        self.logger.info('Insights report written to %s', self.output_path)
