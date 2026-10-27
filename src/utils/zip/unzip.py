"""Unzip a zip file."""
import os

from zipfile import ZipFile


def unzip_file(file_path: str, output_folder: str, remove_zip_file: bool = False):
    """Unzip a file to a folder."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'File not found: {file_path}')

    with ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(output_folder)

    if not remove_zip_file:
        return

    os.remove(file_path)
