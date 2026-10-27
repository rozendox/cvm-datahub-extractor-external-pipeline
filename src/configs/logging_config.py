""" Configuration logging module. """
import os
import logging
from logging.handlers import TimedRotatingFileHandler


def configure_logging():
    """
    Configura o logging da aplicação de forma centralizada.
    Inclui rotação de logs por dia.
    """
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_datefmt = '%Y-%m-%d %H:%M:%S'

    # Diretório para armazenar logs
    log_dir = os.getenv('LOG_DIR', f'{os.getcwd()}/logs')
    os.makedirs(log_dir, exist_ok=True)  # Cria a pasta, se não existir

    log_file = os.path.join(log_dir, 'app.log')

    # Configura o handler de rotação de logs
    file_handler = TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        fmt=log_format, datefmt=log_datefmt))

    # Configuração base
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=log_datefmt,
        handlers=[
            logging.StreamHandler(),  # Exibe logs no console
            file_handler,             # Salva logs em arquivo com rotação diária
        ]
    )
