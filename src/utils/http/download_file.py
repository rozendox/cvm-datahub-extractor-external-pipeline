""" Download file module """
import os

import requests

from configs import settings


def download_file(url: str, file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Faz o download de um arquivo em streaming para o disco.

    :param url: URL do arquivo.
    :type url: str
    :param file_path: Caminho local de destino.
    :type file_path: str
    :returns: Caminho do arquivo baixado.
    :rtype: str
    :raises requests.HTTPError: Se o servidor responder com erro (ex.: 404 de arquivo ainda nao publicado).
    """
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)

    timeout = (settings.HTTP_CONNECT_TIMEOUT, settings.HTTP_READ_TIMEOUT)
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                file.write(chunk)

    return file_path
