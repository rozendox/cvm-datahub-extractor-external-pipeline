# Revisão do pipeline legado

Registro técnico da refatoração que transformou o extrator original (Google Drive + fornecedor
de dados pago + Selenium) neste pipeline medallion baseado apenas em dados abertos da CVM.

## 1. O que foi removido

| Componente | Motivo |
|---|---|
| 9 ingestores, 7 transformers e 1 sanitizer de um **fornecedor de dados pago** | Fonte proprietária, acessada por scraping com Selenium e login de usuário. Sem licença, não pode ser redistribuída num repositório público. |
| `utils/selenium` | Usado apenas pelo fornecedor pago. |
| `utils/google/drive` (upload, download, leitor dinâmico de pastas, atualização de Sheets) | As camadas landing/raw/curated viviam em pastas do Google Drive com IDs fixos no código. Substituídas pelo lake medallion local/S3. |
| `pipelines/curators` | Merges CVM × fonte proprietária para dashboards no Looker Studio (ver seção 2). |
| `mock_drive/`, `playground/`, `.env.dev`, `.env.prod` | Cópias de dados com IDs de pastas do Drive, notebooks de exploração da fonte proprietária e configurações da conta de serviço antiga. |

## 2. Saídas que dependiam da fonte proprietária e os merges revisados

### 2.1 `DashDadosMercadoCurator` → `info_ativos_cri_cra.csv` + `info_fundo.csv` (Google Sheets)

Fluxo: três bases da fonte proprietária (informações adicionais, emissões de crédito privado, emissões em
andamento) eram unidas por **OUTER JOIN** em `merge_key = CODIGO_ISIN ou CODIGO_CETIP`. O resultado
era unido às ofertas CRI/CRA da CVM por **INNER JOIN** em
`big_key = NOME_EMISSOR + "_" + NUMERO_EMISSAO`.

Problemas encontrados:

1. **Junção por nome em texto livre.** A chave dependia do nome do emissor escrito igual nas
   duas fontes. Para isso existia um dicionário fixo com 10 de-paras de nomes de emissores.
   Um deles é suspeito: mapeia *TRUE ADMINISTRADORA FIDUCIÁRIA DE GARANTIAS S.A.* para
   *10B TRUE COD FUNDO DE INVESTIMENTO EM PARTICIPAÇÕES*, que é um fundo, não a mesma entidade.
2. **INNER JOIN silencioso.** Toda emissão sem correspondência exata era descartada sem log nem
   métrica de cobertura. O dashboard não informava quantas emissões ficavam de fora.
3. **Granularidade diferente (risco de dupla contagem).** A CVM tem uma linha por oferta
   (requerimento) e a fonte proprietária uma linha por série/ativo (ISIN). A junção 1:N replica o volume da
   oferta (`VOLUME_EMISSAO_cvm`) em cada série, e somar essa coluna no BI superestima o volume.
4. **`df.fillna('')` sem atribuição** (nos dois curators): a linha não tinha efeito.
5. **A curadoria não era executada:** `main()` nunca chamava `dash_dados_mercado_curator()`, então
   as planilhas desse dashboard não eram atualizadas pela rotina.

### 2.2 `DashInfoGestorasCurator` → `info_gestoras_fundos.csv` (Google Sheets)

Dependia 100% da base de gestoras da fonte proprietária. A classe também carregava uma cópia não utilizada
do merge da seção 2.1.

### 2.3 Atualizadores Looker (`*_looker_att`, `*_updater_looker`)

Gravavam bases da fonte proprietária diretamente em planilhas do Google usadas pelo Looker Studio.

### 2.4 O que substitui cada saída

| Saída antiga | Situação | Substituto (gold) |
|---|---|---|
| `info_ativos_cri_cra` (CVM ⨝ fonte proprietária) | Reconstruída só com CVM | `gold_securitizacao_painel` (CRI, CRA, CR e outros títulos de securitização) + `gold_securitizadoras_ranking` |
| `info_fundo` (CVM) | Migrada | `gold_ofertas_volume_mensal` (classe `fundos`) + `gold_fundos_gestoras_ranking` |
| `info_gestoras_fundos` (fonte proprietária) | Reconstruída só com CVM | `gold_fundos_gestoras_ranking`: ofertas de fundos × cadastro de administradores de carteira |
| Planilhas Looker da fonte proprietária | Removidas | Sem equivalente aberto nas fontes configuradas |

**Campos perdidos com a saída da fonte proprietária:** ISIN/CETIP, série, indexador, percentual do indexador,
spread, vencimento, duration, LTV e estoque na B3. Esses dados não existem nos arquivos da CVM
usados aqui. Fontes públicas que poderiam cobrir parte deles: dados de debêntures da ANBIMA e
arquivos públicos da B3.

**Como o novo pipeline evita os problemas da 2.1:**

- As junções com cadastros usam **resolução de entidades** (CNPJ citado no texto → razão social →
  nome comercial → prefixo único), sempre com preferência pelo registro ativo, em vez de dicionário fixo.
- Toda junção registra e publica sua **taxa de cobertura** (match rate por volume) no log e no relatório.
- Rankings agrupam pela entidade resolvida (CNPJ) e nunca multiplicam linhas: a granularidade de
  cada tabela gold está documentada no módulo que a gera.

## 3. Bugs corrigidos no código CVM mantido

| Bug | Impacto | Correção |
|---|---|---|
| `format_big_numbers` removia o `.` decimal e dividia por 10 | Valores com 2 casas decimais ficavam **10× maiores** (`5000000.04` → `50000000.4`) | `transforms.to_number` respeita o ponto decimal da CVM; teste de regressão em `tests/test_transforms.py` |
| Ingestor de ofertas filtrava 11 tipos de valor mobiliário fixos | 11 tipos descartados em silêncio (ex.: 799 ofertas de **notas comerciais**, ações, FI-Infra, CPR-F) | Silver mantém todos e classifica por `classe_ativo`; tipos novos geram *warning* |
| `download_file` com `timeout=5` e sem `raise_for_status()` | Arquivos grandes falhavam; um 404 em HTML era salvo como `.zip` e quebrava no unzip | Download em streaming, timeouts configuráveis, erro HTTP explícito |
| `PipelineBase.run` engolia exceções | Execução terminava com código 0 mesmo com falhas | `run()` retorna sucesso/falha e `main.py` sai com código 1 se algo falhar |
| `CvmOfertaDistribuicaoTransformer` chamado duas vezes no `main()` | Processamento e upload duplicados | Orquestração por camadas no `main.py` |
| Prefixo `CAD_CONSULTOR` no código × `CAD_CONSULTORES` no `.env.dev` | Ingestor só funcionava com o `.env` local | Fontes centralizadas em `configs/sources.py` (sem ~150 variáveis de ambiente) |
| Padrões de pasta com typo no `.env` (`==%s`, `%s/<fonte>//`) | Criavam pastas lixo como `%s/` e `=/` na raiz | Caminhos montados pela classe `Lake` |
| IDs de pastas do Drive fixos no código | Acoplamento a uma conta específica | Removidos |
| Cadastro `cad_adm_fii` usado como referência de administradores de FII | Cadastro está **100% cancelado** (legado pré-Resolução CVM 175) | Administradores cruzados por CNPJ com `cad_adm_carteira` |

## 4. Segurança

- O histórico do git contém um arquivo de ambiente com a **chave privada de uma conta de serviço
  do Google Cloud** (commit `558ecfc`, arquivo removido depois, mas ainda recuperável pelo histórico).
  Antes de tornar o repositório público: revogar a chave no GCP e reescrever o histórico
  (`git filter-repo`) ou publicar a partir de um histórico novo.
- O novo pipeline não usa nenhuma credencial: as fontes da CVM são públicas.
