""" Configuracoes globais da aplicacao. """
import json
import os
from datetime import date

from dotenv import load_dotenv

load_dotenv(f'{os.getcwd()}/.env', verbose=False)

# Raiz do data lake. Caminho local (padrao) ou URI remota, ex.: s3://meu-bucket/cvm-lake
LAKE_ROOT = os.environ.get('LAKE_ROOT', 'lake')

# Opcoes repassadas ao fsspec (ex.: {"profile": "datalake"} para S3). JSON em string.
LAKE_STORAGE_OPTIONS = json.loads(os.environ.get('LAKE_STORAGE_OPTIONS', '{}'))

# Timeout (segundos) para conexao e leitura dos downloads do portal de dados abertos da CVM
HTTP_CONNECT_TIMEOUT = int(os.environ.get('HTTP_CONNECT_TIMEOUT', '15'))
HTTP_READ_TIMEOUT = int(os.environ.get('HTTP_READ_TIMEOUT', '300'))

# Pasta onde o relatorio de insights e gerado
REPORT_OUTPUT_PATH = os.environ.get('REPORT_OUTPUT_PATH', 'docs/INSIGHTS.md')


def today() -> date:
    """ Data de referencia padrao da execucao. """
    return date.today()
