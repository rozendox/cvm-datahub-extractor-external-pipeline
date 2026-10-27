# Migração do data lake local para o AWS S3

O pipeline já nasceu preparado para o S3: **nenhuma linha de código precisa mudar**.
Toda leitura e escrita passa pela classe [`Lake`](../src/lake/lake.py), que usa o
[fsspec](https://filesystem-spec.readthedocs.io/). O fsspec expõe a mesma API para disco local,
S3, GCS, Azure Blob etc. O backend é escolhido pelo prefixo da raiz do lake:

| `LAKE_ROOT`                  | Onde os dados ficam                      |
|------------------------------|------------------------------------------|
| `lake` (padrão)              | `./lake/bronze`, `./lake/silver`, ...    |
| `s3://meu-bucket/cvm-lake`   | `s3://meu-bucket/cvm-lake/bronze`, ...   |

> O teste `tests/test_lake.py::test_lake_works_with_non_local_filesystem` roda o lake sobre
> `memory://`, um backend não local do fsspec, para garantir que nenhum trecho depende do disco.

---

## Passo a passo

### 1. Criar o bucket

```sh
aws s3api create-bucket --bucket meu-bucket-cvm-lake --region sa-east-1 \
  --create-bucket-configuration LocationConstraint=sa-east-1

# Bloqueio de acesso público, versionamento e criptografia padrão
aws s3api put-public-access-block --bucket meu-bucket-cvm-lake \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket meu-bucket-cvm-lake --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket meu-bucket-cvm-lake \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

### 2. Permissões (IAM, menor privilégio)

Política para o usuário/role que executa o pipeline, restrita ao prefixo do lake:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListarPrefixoDoLake",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::meu-bucket-cvm-lake",
      "Condition": { "StringLike": { "s3:prefix": ["cvm-lake", "cvm-lake/*"] } }
    },
    {
      "Sid": "LerEscreverObjetosDoLake",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::meu-bucket-cvm-lake/cvm-lake/*"
    }
  ]
}
```

### 3. Instalar a dependência do S3

```sh
pip install -r requirements/requirements.s3.txt   # adiciona o s3fs
```

### 4. Credenciais

O `s3fs` usa a cadeia padrão de credenciais da AWS (a mesma do `boto3`), na ordem:
variáveis `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` → perfil em `~/.aws/credentials` →
role da instância/tarefa (EC2, ECS, Lambda).

- **Local:** `aws configure --profile datalake` e `LAKE_STORAGE_OPTIONS={"profile": "datalake"}`.
- **Na AWS:** anexe a política do passo 2 à *task role* / *instance profile*. Nenhuma chave em arquivo.

> Nunca coloque chaves de acesso no `.env` versionado. O `.gitignore` bloqueia `.env`; use o `.env.example` como modelo.

### 5. Apontar o pipeline para o bucket

```sh
# .env
LAKE_ROOT=s3://meu-bucket-cvm-lake/cvm-lake
LAKE_STORAGE_OPTIONS={"profile": "datalake", "client_kwargs": {"region_name": "sa-east-1"}}
```

Ou pontualmente, pela linha de comando:

```sh
python src/main.py --lake-root s3://meu-bucket-cvm-lake/cvm-lake
```

### 6. Levar o histórico local para o S3 (opcional)

A bronze local guarda todas as ingestões anteriores. Para não perder esse histórico:

```sh
aws s3 sync lake/ s3://meu-bucket-cvm-lake/cvm-lake/ --exclude "*/.DS_Store"
```

Depois, valide reprocessando silver e gold a partir da bronze remota:

```sh
python src/main.py --layers silver gold report --lake-root s3://meu-bucket-cvm-lake/cvm-lake
```

---

## Consultando o lake com Athena

O layout foi pensado para catálogos de dados: cada tabela silver/gold ocupa um prefixo próprio
(`<camada>/<tabela>/data.parquet`), as colunas estão em `snake_case` minúsculo (o Glue converte
tudo para minúsculas) e as cópias CSV ficam fora dessas pastas (`exports/`).

Opção 1: um **Glue Crawler** apontando para `s3://meu-bucket-cvm-lake/cvm-lake/gold/` cria uma
tabela por pasta automaticamente.

Opção 2: DDL explícito no Athena (exemplo com o schema real de uma tabela gold):

```sql
CREATE DATABASE IF NOT EXISTS cvm_gold;

CREATE EXTERNAL TABLE cvm_gold.ofertas_volume_mensal (
  mes_registro             timestamp,
  classe_ativo             string,
  tipo_ativo               string,
  qtd_ofertas              bigint,
  volume_registrado        double,
  qtd_encerradas           bigint,
  volume_encerradas        double,
  volume_colocado_estimado double,
  ticket_medio             double
)
STORED AS PARQUET
LOCATION 's3://meu-bucket-cvm-lake/cvm-lake/gold/gold_ofertas_volume_mensal/';

-- Volume de debêntures encerradas por ano
SELECT year(mes_registro) AS ano, round(sum(volume_encerradas) / 1e9, 1) AS volume_bi
FROM cvm_gold.ofertas_volume_mensal
WHERE tipo_ativo = 'DEBENTURE'
GROUP BY 1 ORDER BY 1;
```

A bronze (CSV bruto, `;`, Latin-1) pode ser catalogada com partição por `ingestion_date`
caso seja útil auditar versões anteriores dos arquivos da CVM.

---

## Agendamento na AWS

O pipeline é um processo batch (`python src/main.py`) que termina com código de saída
`0` (sucesso) ou `1` (alguma etapa falhou). Opções, da mais simples à mais robusta:

| Opção | Quando usar |
|---|---|
| **ECS Fargate + EventBridge Scheduler** (recomendado) | Execução diária sem servidor; sem limite de tempo; a *task role* dá acesso ao bucket. |
| AWS Batch | Se a fonte pesada `fi_carteira_cda` (vários GB) entrar na rotina. |
| Lambda | Só bronze das fontes pequenas: limite de 15 min e 10 GB de `/tmp`. |
| MWAA (Airflow gerenciado) | Se o projeto crescer para várias DAGs com dependências entre si. |

Um `Dockerfile` mínimo para ECS/Batch:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/requirements.s3.txt
COPY src/ src/
ENTRYPOINT ["python", "src/main.py"]
```

---

## Custos e retenção

- **Lifecycle na bronze:** os arquivos brutos raramente são relidos depois de processados.
  Mova `bronze/` para *S3 Glacier Instant Retrieval* após 90 dias:

  ```json
  {"Rules": [{"ID": "bronze-para-glacier-ir", "Status": "Enabled",
              "Filter": {"Prefix": "cvm-lake/bronze/"},
              "Transitions": [{"Days": 90, "StorageClass": "GLACIER_IR"}]}]}
  ```

- Silver e gold são sobrescritas a cada execução; com versionamento ligado, configure
  `NoncurrentVersionExpiration` (ex.: 30 dias) para não acumular versões antigas.
- O volume atual é pequeno (dezenas de MB por ingestão sem a CDA), então o custo de
  armazenamento é desprezível. O que pesa é a CDA, se habilitada.

---

## Pontos de atenção

- **Cache de listagem:** o `s3fs` mantém cache de listagens. As escritas do próprio processo
  invalidam esse cache, mas se outro processo escrever no mesmo prefixo durante a execução,
  use `LAKE_STORAGE_OPTIONS={"use_listings_cache": false}`.
- **Escrita atômica:** no S3 um `PUT` de objeto é atômico. Leitores nunca veem um Parquet pela metade.
  Silver e gold, porém, são sobrescritas tabela a tabela. Se várias tabelas precisarem mudar
  juntas (transação), o próximo passo natural é um formato de tabela como **Apache Iceberg**
  (S3 Tables ou Glue + Athena), que também traz *time travel* e *schema evolution*.
- **Região:** mantenha bucket e computação na mesma região (ex.: `sa-east-1`) para evitar
  custo de transferência.
