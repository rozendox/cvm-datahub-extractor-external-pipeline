"""
Catalogo das fontes de dados abertos da CVM (https://dados.cvm.gov.br).

Cada fonte vira uma pasta na camada bronze do lake. As URLs que dependem do periodo
(ano ou mes de referencia) usam placeholders resolvidos na data de execucao.
"""
import re
from dataclasses import dataclass
from datetime import date

import requests

CVM_BASE_URL = 'https://dados.cvm.gov.br/dados'


@dataclass(frozen=True)
class CvmSource:
    """ Fonte de dados da CVM. """

    name: str
    description: str
    url: str
    meta_url: str | None = None
    # None (arquivo unico), 'previous_year', 'current_year' ou 'latest_month'
    period: str | None = None
    # Fontes pesadas ficam fora da execucao padrao (use --include-heavy)
    heavy: bool = False

    def resolve_url(self, run_date: date) -> str:
        """
        Resolve a URL final do arquivo de acordo com o periodo da fonte.

        :param run_date: Data de referencia da execucao.
        :type run_date: date
        :returns: URL pronta para download.
        :rtype: str
        """
        if self.period == 'previous_year':
            return self.url.format(year=run_date.year - 1)
        if self.period == 'current_year':
            return self.url.format(year=run_date.year)
        if self.period == 'latest_month':
            return self._latest_month_url()
        return self.url

    def _latest_month_url(self) -> str:
        """ Busca no indice da CVM o arquivo mensal mais recente publicado. """
        index_url = self.url.rsplit('/', 1)[0] + '/'
        pattern = re.escape(self.url.rsplit('/', 1)[1]).replace(r'\{yyyymm\}', r'(\d{6})')
        response = requests.get(index_url, timeout=30)
        response.raise_for_status()
        months = sorted(set(re.findall(pattern, response.text)))
        if not months:
            raise RuntimeError(f'Nenhum arquivo mensal encontrado em {index_url}')
        return self.url.format(yyyymm=months[-1])


SOURCES: dict[str, CvmSource] = {source.name: source for source in [
    CvmSource(
        name='ofertas_distribuicao',
        description='Ofertas publicas de distribuicao (Resolucao CVM 160 e historico ICVM 400/476)',
        url=f'{CVM_BASE_URL}/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip',
    ),
    CvmSource(
        name='cad_adm_carteira',
        description='Cadastro de administradores de carteira (gestoras e administradores fiduciarios)',
        url=f'{CVM_BASE_URL}/ADM_CART/CAD/DADOS/cad_adm_cart.zip',
        meta_url=f'{CVM_BASE_URL}/ADM_CART/CAD/META/meta_cad_adm_cart.zip',
    ),
    CvmSource(
        name='cad_adm_fii',
        description='Cadastro de administradores de FII',
        url=f'{CVM_BASE_URL}/ADM_FII/CAD/DADOS/cad_adm_fii.csv',
        meta_url=f'{CVM_BASE_URL}/ADM_FII/CAD/META/meta_cad_adm_fii.txt',
    ),
    CvmSource(
        name='cad_agente_autonomo',
        description='Cadastro de agentes autonomos de investimento (assessores)',
        url=f'{CVM_BASE_URL}/AGENTE_AUTON/CAD/DADOS/cad_agente_auton.zip',
        meta_url=f'{CVM_BASE_URL}/AGENTE_AUTON/CAD/META/meta_cad_agente_auton.zip',
    ),
    CvmSource(
        name='cad_agente_fiduciario',
        description='Cadastro de agentes fiduciarios',
        url=f'{CVM_BASE_URL}/AGENTE_FIDUC/CAD/DADOS/cad_agente_fiduc.zip',
        meta_url=f'{CVM_BASE_URL}/AGENTE_FIDUC/CAD/META/meta_cad_agente_fiduc.zip',
    ),
    CvmSource(
        name='cad_auditor',
        description='Cadastro de auditores independentes',
        url=f'{CVM_BASE_URL}/AUDITOR/CAD/DADOS/cad_auditor.zip',
        meta_url=f'{CVM_BASE_URL}/AUDITOR/CAD/META/meta_cad_auditor.zip',
    ),
    CvmSource(
        name='cad_consultor',
        description='Cadastro de consultores de valores mobiliarios',
        url=f'{CVM_BASE_URL}/CONSULTOR_VLMOB/CAD/DADOS/cad_consultor_vlmob.zip',
        meta_url=f'{CVM_BASE_URL}/CONSULTOR_VLMOB/CAD/META/meta_cad_consultor_vlmob.zip',
    ),
    CvmSource(
        name='cad_crowdfunding',
        description='Cadastro de plataformas de crowdfunding de investimento',
        url=f'{CVM_BASE_URL}/CROWDFUNDING/CAD/DADOS/cad_crowdfunding.zip',
        meta_url=f'{CVM_BASE_URL}/CROWDFUNDING/CAD/META/meta_cad_crowdfunding.zip',
    ),
    CvmSource(
        name='fii_informe_anual',
        description='Informe anual estruturado de FII (ultimo ano completo)',
        url=f'{CVM_BASE_URL}/FII/DOC/INF_ANUAL/DADOS/inf_anual_fii_{{year}}.zip',
        period='previous_year',
    ),
    CvmSource(
        name='fii_informe_trimestral',
        description='Informe trimestral estruturado de FII (ano corrente)',
        url=f'{CVM_BASE_URL}/FII/DOC/INF_TRIMESTRAL/DADOS/inf_trimestral_fii_{{year}}.zip',
        period='current_year',
    ),
    CvmSource(
        name='fi_carteira_cda',
        description='Composicao e diversificacao das carteiras de fundos (CDA, mes mais recente)',
        url=f'{CVM_BASE_URL}/FI/DOC/CDA/DADOS/cda_fi_{{yyyymm}}.zip',
        period='latest_month',
        heavy=True,
    ),
]}
