"""
Ponto de entrada do pipeline medallion de dados abertos da CVM.

Exemplos:
    python src/main.py                                  # bronze -> silver -> gold -> relatorio
    python src/main.py --layers silver gold report      # reprocessa sem baixar novamente
    python src/main.py --layers bronze --sources ofertas_distribuicao cad_agente_fiduciario
    python src/main.py --layers silver --ingestion-date 2026-10-26
    python src/main.py --layers bronze --include-heavy  # inclui a carteira dos fundos (CDA, ~GBs)
"""
import argparse
import logging
import sys
from datetime import date

from configs import settings
from configs.logging_config import configure_logging
from configs.sources import SOURCES
from lake.lake import Lake
from pipelines.bronze.cvm_bronze_ingestor import CvmBronzeIngestor
from pipelines.gold.fii_gold import FiiGold
from pipelines.gold.ofertas_gold import OfertasGold
from pipelines.gold.participantes_gold import ParticipantesGold
from pipelines.silver.cvm_fii_silver import CvmFiiSilver
from pipelines.silver.cvm_ofertas_silver import CvmOfertasSilver
from pipelines.silver.cvm_participantes_silver import CvmParticipantesSilver
from reports.insights_report import InsightsReport

LAYERS = ['bronze', 'silver', 'gold', 'report']


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """ Le os argumentos de linha de comando. """
    parser = argparse.ArgumentParser(description='Pipeline medallion de dados abertos da CVM.')
    parser.add_argument('--layers', nargs='+', choices=LAYERS, default=LAYERS,
                        help='Camadas a executar, em ordem (padrao: todas).')
    parser.add_argument('--sources', nargs='+', choices=sorted(SOURCES),
                        help='Fontes da camada bronze (padrao: todas, exceto as pesadas).')
    parser.add_argument('--include-heavy', action='store_true',
                        help='Inclui fontes pesadas na bronze (ex.: fi_carteira_cda).')
    parser.add_argument('--ingestion-date', type=date.fromisoformat,
                        help='Data da particao bronze. Na bronze define a particao gravada; '
                             'na silver, qual particao ler (padrao: a mais recente).')
    parser.add_argument('--lake-root', default=settings.LAKE_ROOT,
                        help='Raiz do lake: pasta local ou URI (ex.: s3://bucket/prefixo).')
    return parser.parse_args(argv)


def selected_sources(args: argparse.Namespace) -> list:
    """ Fontes da bronze de acordo com os argumentos. """
    if args.sources:
        return [SOURCES[name] for name in args.sources]
    return [source for source in SOURCES.values() if args.include_heavy or not source.heavy]


def build_pipelines(args: argparse.Namespace, lake: Lake) -> list:
    """ Monta a lista de pipelines na ordem de execucao das camadas. """
    ingestion_date = args.ingestion_date.isoformat() if args.ingestion_date else None
    pipelines = []
    for layer in LAYERS:
        if layer not in args.layers:
            continue
        if layer == 'bronze':
            run_date = args.ingestion_date or settings.today()
            pipelines += [CvmBronzeIngestor(source, lake, run_date) for source in selected_sources(args)]
        elif layer == 'silver':
            pipelines += [CvmOfertasSilver(lake, ingestion_date), CvmParticipantesSilver(lake, ingestion_date),
                          CvmFiiSilver(lake, ingestion_date)]
        elif layer == 'gold':
            pipelines += [OfertasGold(lake), FiiGold(lake), ParticipantesGold(lake)]
        elif layer == 'report':
            pipelines.append(InsightsReport(lake, settings.REPORT_OUTPUT_PATH))
    return pipelines


def main(argv: list[str] | None = None) -> int:
    """ Startup application. Retorna 0 em caso de sucesso e 1 se alguma pipeline falhar. """
    configure_logging()
    args = parse_args(argv)
    lake = Lake(args.lake_root)
    logger = logging.getLogger('main')
    logger.info('Lake root: %s | layers: %s', lake.root, ' -> '.join(args.layers))

    failures = [pipeline.name for pipeline in build_pipelines(args, lake) if not pipeline.run()]
    if failures:
        logger.error('%s pipeline(s) failed: %s', len(failures), ', '.join(failures))
        return 1
    logger.info('All pipelines finished successfully.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
