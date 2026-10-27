""" Testes da camada de armazenamento (fsspec local). """
import pandas as pd
import pytest

from lake.lake import GOLD, Lake


@pytest.fixture(name='lake')
def fixture_lake(tmp_path):
    return Lake(str(tmp_path / 'lake'), storage_options={})


def test_table_roundtrip_with_csv_copy(lake):
    df = pd.DataFrame({'nome': ['Ação'], 'valor': [1.5]})
    lake.write_table(df, GOLD, 'exemplo', csv_copy=True)

    pd.testing.assert_frame_equal(lake.read_table(GOLD, 'exemplo'), df)
    csv = lake.read_bytes(lake.export_path(GOLD, 'exemplo')).decode('utf-8-sig')
    assert csv.splitlines() == ['nome;valor', 'Ação;1,5']
    # A pasta da tabela deve conter somente Parquet (exigencia de Glue/Athena)
    assert lake.fs.ls(lake.path(GOLD, 'exemplo'), detail=False)[0].endswith('data.parquet')


def test_lake_works_with_non_local_filesystem():
    # memory:// usa a mesma API do fsspec que o s3:// - garante que nada depende do disco local
    lake = Lake('memory://cvm-lake-test', storage_options={})
    lake.write_bytes(f'{lake.bronze_partition("fonte", "2026-03-01")}/dados.csv', 'A;B\n1;2\n'.encode())
    assert lake.resolve_bronze_date('fonte') == '2026-03-01'
    assert lake.read_csv(f'{lake.bronze_partition("fonte", "2026-03-01")}/dados.csv')['B'].tolist() == ['2']
    lake.write_table(pd.DataFrame({'x': [1]}), GOLD, 'tabela', csv_copy=True)
    assert lake.read_table(GOLD, 'tabela')['x'].tolist() == [1]


def test_resolve_bronze_date_uses_latest_partition(lake):
    for ingestion_date in ['2026-01-01', '2026-02-01']:
        lake.write_bytes(f'{lake.bronze_partition("fonte", ingestion_date)}/dados.csv', b'a;b\n1;2\n')
    lake.write_json(f'{lake.bronze_partition("fonte", "2026-02-01")}/_manifest.json', {'ok': True})

    assert lake.resolve_bronze_date('fonte') == '2026-02-01'
    assert lake.resolve_bronze_date('fonte', '2026-01-01') == '2026-01-01'
    assert lake.bronze_files('fonte', '2026-02-01') == ['dados.csv']
    with pytest.raises(FileNotFoundError):
        lake.resolve_bronze_date('fonte_inexistente')


def test_read_csv_falls_back_to_latin1(lake):
    path = f'{lake.bronze_partition("fonte", "2026-01-01")}/latin1.csv'
    lake.write_bytes(path, 'NOME;SIT\nPentágono;ATIVO\n'.encode('latin-1'))
    df = lake.read_csv(path)
    assert df['NOME'].iloc[0] == 'Pentágono'
