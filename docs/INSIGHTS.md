# Insights: mercado de capitais brasileiro (dados abertos da CVM)

> Gerado automaticamente em 26/10/2026 21:08 a partir da camada gold (`lake`). Não edite manualmente: rode `python src/main.py --layers report`.

## 1. Mercado de ofertas públicas (Resolução CVM 160)

Volume registrado das ofertas **encerradas**, por ano de registro. Base: 14.352 ofertas válidas desde jan/2023 (início da Resolução 160).

| Ano | Ofertas encerradas | Renda fixa | Fundos | Renda variável | Total |
|---|---|---|---|---|---|
| 2023 | 2.753 | R$ 353,4 bi | R$ 169,4 bi | R$ 31,3 bi | R$ 554,2 bi |
| 2024 | 3.808 | R$ 642,4 bi | R$ 259,3 bi | R$ 25,0 bi | R$ 926,7 bi |
| 2025 | 4.171 | R$ 658,6 bi | R$ 351,3 bi | R$ 15,5 bi | R$ 1,03 tri |
| 2026 (parcial) | 2.098 | R$ 353,9 bi | R$ 229,2 bi | R$ 37,8 bi | R$ 620,8 bi |

- Em 2025, o volume de ofertas encerradas cresceu **10,7%** em relação a 2024.
- Ativos com maior volume em 2025: **DEBENTURE** (44,5%), **FIDC** (12,4%), **FII** (11,0%), **FIF** (5,8%).

## 2. Quem lidera as ofertas (league table de coordenadores)

**Renda fixa - 2025** (top 3 concentram 55,8% do volume)

| # | Coordenador líder | Ofertas | Volume | Market share |
|---|---|---|---|---|
| 1 | ITAU BBA ASSESSORIA FINANCEIRA S.A | 350 | R$ 188,9 bi | 28,7% |
| 2 | BANCO BRADESCO BBI S.A. | 173 | R$ 107,4 bi | 16,3% |
| 3 | BTG PACTUAL INVESTMENT BANKING LTDA. | 77 | R$ 71,2 bi | 10,8% |
| 4 | XP INVESTIMENTOS CCTVM S.A. | 87 | R$ 65,0 bi | 9,9% |
| 5 | BANCO SANTANDER (BRASIL) S.A. | 75 | R$ 43,2 bi | 6,6% |

**Cotas de fundos - 2025** (top 3 concentram 52,6% do volume)

| # | Coordenador líder | Ofertas | Volume | Market share |
|---|---|---|---|---|
| 1 | ITAU BBA ASSESSORIA FINANCEIRA S.A | 93 | R$ 71,5 bi | 20,3% |
| 2 | XP INVESTIMENTOS CCTVM S.A. | 128 | R$ 63,9 bi | 18,2% |
| 3 | BTG PACTUAL SERVIÇOS FINANCEIROS S/A DTVM | 302 | R$ 49,6 bi | 14,1% |
| 4 | SINGULARE CORRETORA DE TITULOS E VALORES MOBILIARIOS S.A. | 435 | R$ 19,0 bi | 5,4% |
| 5 | BANCO DAYCOVAL S.A. | 157 | R$ 14,2 bi | 4,0% |

## 3. Quem compra cada ativo

Participação de cada tipo de investidor na quantidade subscrita das ofertas encerradas.

| Ativo | Ofertas na base | Top 3 compradores | Pessoas físicas |
|---|---|---|---|
| DEBENTURE | 1.908 | Inst. financeiras ligadas à emissora/consórcio (38,6%); Fundos de investimento (21,0%); Demais instituições financeiras (19,6%) | 2,4% |
| CRI | 1.581 | Fundos de investimento (56,7%); Inst. financeiras ligadas à emissora/consórcio (22,3%); Pessoas físicas (7,7%) | 7,7% |
| CRA | 542 | Inst. financeiras ligadas à emissora/consórcio (55,8%); Fundos de investimento (32,6%); Pessoas físicas (6,7%) | 6,7% |
| NOTA_COMERCIAL | 768 | Inst. financeiras ligadas à emissora/consórcio (67,9%); Fundos de investimento (26,0%); Instituições do consórcio de distribuição (6,1%) | 0,0% |
| FII | 1.066 | Fundos de investimento (45,0%); Pessoas físicas (28,5%); Investidores estrangeiros (11,8%) | 28,5% |
| FIDC | 3.579 | Fundos de investimento (57,4%); Inst. financeiras ligadas à emissora/consórcio (23,2%); Demais instituições financeiras (6,0%) | 3,5% |
| FIAGRO | 137 | Fundos de investimento (64,7%); Pessoas físicas (16,3%); Sócios/administradores ligados à emissora (13,1%) | 16,3% |

## 4. Securitização e agentes fiduciários

**Securitizadoras** (CRI, CRA e CR encerrados desde 2023)

| # | Securitizadora | Ofertas | Volume | Market share | Lastro pulverizado |
|---|---|---|---|---|---|
| 1 | OPEA SECURITIZADORA S.A. | 621 | R$ 134,4 bi | 31,6% | 16,1% |
| 2 | ECO. SEC. DTOS. CREDIT. AGRONEGÓCIOS S/A | 168 | R$ 58,4 bi | 13,7% | 7,7% |
| 3 | VIRGO COMPANHIA DE SECURITIZAÇÃO | 338 | R$ 49,1 bi | 11,6% | 14,5% |
| 4 | VERT COMPANHIA SECURITIZADORA | 163 | R$ 37,6 bi | 8,8% | 42,3% |
| 5 | TRUE SECURITIZADORA S.A. | 225 | R$ 30,7 bi | 7,2% | 21,3% |

**Agentes fiduciários**: os 3 maiores concentram **95,9%** do volume de renda fixa encerrado: Pentágono S.A. Distribuidora de Títulos e Valores Mobiliários (39,4%), OLIVEIRA TRUST DTVM S.A. (33,2%), VORTX DISTRIBUIDORA DE TITULOS E VALORES MOBILIARIOS LTDA. (23,3%).

- O campo de agente fiduciário é texto livre: só os 3 líderes aparecem com **285 grafias diferentes**. A resolução de entidades (CNPJ citado no texto, razão social, nome comercial e prefixo único) casa **98,5%** do volume com o cadastro oficial da CVM.

## 5. Gestoras com mais ofertas de fundos

Cotas de FII, FIDC, FIP, FIF, FIAGRO e FI-Infra encerradas desde 2023. 940 gestoras distintas; o top 10 responde por 28,4% do volume. 89,7% do volume foi casado com o cadastro de administradores de carteira da CVM.

| # | Gestora | Ofertas | Volume | Market share | Tipos de fundo |
|---|---|---|---|---|---|
| 1 | ITAU UNIBANCO ASSET MANAGEMENT LTDA. | 58 | R$ 56,5 bi | 5,6% | FI-INFRA, FIAGRO, FIAGRO-FII, FIDC, FIF, FII, FIP |
| 2 | XP VISTA ASSET MANAGEMENT LTDA. | 84 | R$ 40,0 bi | 4,0% | FI-INFRA, FIAGRO, FIAGRO-FII, FIDC, FIF, FII, FIP |
| 3 | OLIVEIRA TRUST SERVICER S/A | 54 | R$ 31,7 bi | 3,1% | FIAGRO, FIDC, FIF, FII |
| 4 | BANCO BRADESCO S.A. | 34 | R$ 28,4 bi | 2,8% | FI-INFRA, FIDC, FIF, FII, FIP |
| 5 | BTG PACTUAL GESTORA DE RECURSOS LTDA | 55 | R$ 27,6 bi | 2,7% | FIAGRO, FIAGRO-FIDC, FIF, FII, FIP |
| 6 | KINEA INVESTIMENTOS LTDA. | 53 | R$ 27,0 bi | 2,7% | FI-INFRA, FIAGRO-FII, FIDC, FIF, FII, FIP |
| 7 | ANGÁ ADMINISTRAÇÃO DE RECURSOS LTDA. | 71 | R$ 23,7 bi | 2,3% | FIDC |
| 8 | TRX GESTORA DE RECURSOS LTDA | 16 | R$ 18,5 bi | 1,8% | FII |

## 6. Fundos imobiliários (informe anual 2025)

1.158 FIIs/classes reportaram R$ 494,7 bi em valor contábil de ativos imobiliários.

| Segmento | Fundos | % fundos | Valor contábil | % valor | Gestão ativa |
|---|---|---|---|---|---|
| MULTICATEGORIA | 470 | 40,6% | R$ 220,4 bi | 44,6% | 90,0% |
| OUTROS | 367 | 31,7% | R$ 137,3 bi | 27,8% | 91,5% |
| SHOPPINGS | 68 | 5,9% | R$ 52,7 bi | 10,6% | 58,8% |
| LOGISTICA | 87 | 7,5% | R$ 47,1 bi | 9,5% | 80,5% |
| ESCRITORIOS | 61 | 5,3% | R$ 24,0 bi | 4,9% | 59,0% |
| HOSPITAL | 16 | 1,4% | R$ 4,7 bi | 0,9% | 50,0% |
| RESIDENCIAL | 62 | 5,3% | R$ 3,8 bi | 0,8% | 90,3% |
| VAREJO | 13 | 1,1% | R$ 3,3 bi | 0,7% | 76,9% |
| HOTEL | 8 | 0,7% | R$ 1,3 bi | 0,3% | 50,0% |
| HIBRIDO | 2 | 0,2% | R$ 140,6 mi | 0,0% | 100,0% |
| TITULOS E VAL. MOB. | 2 | 0,2% | R$ 70,6 mi | 0,0% | 100,0% |
| EDUCACIONAL | 2 | 0,2% | R$ 0 | 0,0% | 50,0% |

**Administradores**: os 5 maiores somam 73,3% do valor contábil.

| # | Administrador | Fundos | Valor contábil | % valor |
|---|---|---|---|---|
| 1 | BRL TRUST DTVM S.A. | 106 | R$ 141,6 bi | 28,6% |
| 2 | BTG PACTUAL SERVICOS FINANCEIROS S.A. DISTRIBUIDOR | 202 | R$ 111,3 bi | 22,5% |
| 3 | XP INVESTIMENTOS CORRETORA DE CÂMBIO, TÍTULOS E VAL MOB S/A | 76 | R$ 38,8 bi | 7,8% |
| 4 | BANCO GENIAL S.A. | 61 | R$ 37,8 bi | 7,6% |
| 5 | INTRAG DISTRIBUIDORA DE TÍTULOS E VALORES MOBILIÁRIOS LTDA | 25 | R$ 33,2 bi | 6,7% |

- Transações no exercício: R$ 151,3 bi em aquisições contra R$ 147,2 bi em alienações (saldo comprador de R$ 4,1 bi).
- 14 de 69 administradores informados nos informes não têm CNPJ no cadastro de administradores de carteira; o cadastro específico de administradores de FII (cad_adm_fii) está 100% cancelado e não serve mais como referência.

## 7. Participantes do mercado

**Assessores de investimento (AAI)**: registros e cancelamentos por ano.

| Ano | Novos registros | Cancelamentos | Saldo |
|---|---|---|---|
| 2020 | 4.354 | 1.180 | 3.174 |
| 2021 | 5.855 | 1.634 | 4.221 |
| 2022 | 6.604 | 1.591 | 5.013 |
| 2023 | 5.285 | 2.245 | 3.040 |
| 2024 | 3.967 | 2.126 | 1.841 |
| 2025 | 3.678 | 2.951 | 727 |
| 2026 (parcial) | 2.976 | 3.970 | -994 |

- O pico de novos assessores foi em 2022 (6.604 registros). Desde então o saldo líquido encolhe ano a ano e em 2026 os cancelamentos superaram os novos registros.

**Concentração geográfica** (pessoas jurídicas em funcionamento):

| Participante (PJ ativo) | Quantidade | SP + RJ | Maior UF fora do eixo |
|---|---|---|---|
| Gestoras e administradores fiduciários | 1.558 | 85,8% | MG |
| Assessores de investimento (AAI) | 1.400 | 63,2% | RS |
| Agentes fiduciários | 32 | 90,6% | CE |
| Auditores independentes | 481 | 43,0% | PR |
| Consultores de valores mobiliários | 584 | 56,5% | RS |
| Plataformas de crowdfunding | 89 | 68,5% | RS |

## 8. Qualidade de dados observada

- **640** de 12.841 ofertas encerradas (5,0%) têm quantidade subscrita por investidores maior que 105% da quantidade registrada (unidades inconsistentes entre campos). Elas ficam fora das métricas de colocação.
- 0 ofertas com valor mobiliário não mapeado (classe "outros").
- Datas placeholder (ex.: 1899-12-31) nas transações de FII são descartadas na silver.
- Prestadores de serviço (agente fiduciário, gestor) são texto livre: ver match rates nas seções 4 e 5.
