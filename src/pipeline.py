from src.logger import logger
from src.ingestion.ingest_wafer import ingest_wafer_files
from src.processing.build_bronze_wafer import build_bronze
from src.processing.build_silver_wafer import build_silver
from src.processing.build_gold_wafer import build_gold
from src.analytics.quality_check import quality_check


def main():
    logger.info("=" * 50)
    logger.info("WAFER DATA LAKE PIPELINE STARTED")
    logger.info("=" * 50)

    logger.info("[0/5] INGESTION")
    ingest_wafer_files()

    logger.info("[1/5] BRONZE")
    build_bronze()

    logger.info("[2/5] SILVER")
    build_silver()

    logger.info("[3/5] GOLD")
    build_gold()

    logger.info("[4/5] DATA QUALITY CHECKS")
    quality_check()

    logger.info("=" * 50)
    logger.info("WAFER DATA LAKE PIPELINE: SUCCESS")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()