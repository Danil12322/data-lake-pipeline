import pandas as pd

from src.config import BRONZE_PATH, sql_path
from src.ingestion.metadata import mark_processed, unprocessed_versions
from src.ingestion.wafer_parser import parse_wafer_file
from src.logger import logger


def build_bronze():
    """
    Builds the Bronze layer from unprocessed raw versions.

    Incremental, append-only:
    - reads only versions with processed_at IS NULL from ingestion_log.csv
    - parses each .000 file, adds wafer_id and inspection_run_id
    - appends new defects to the existing Bronze (or creates it)
    - marks processed versions in metadata

    Writes to data/bronze/defects.parquet.
    """
    pending = unprocessed_versions()

    if not pending:
        logger.info("No unprocessed versions. Bronze unchanged.")
        return

    dfs = []
    processed_rows = []

    for item in pending:
        file_stem = item["file_stem"]
        raw_path = item["raw_path"]

        df = parse_wafer_file(raw_path)

        wafer_id = file_stem.rsplit("-", 1)[0]

        df["wafer_id"] = wafer_id
        df["inspection_run_id"] = file_stem

        dfs.append(df)
        processed_rows.append(item["row_index"])

        logger.info(f"{file_stem}: {len(df)} defects")

    new_data = pd.concat(dfs, ignore_index=True)

    # Append-only: добавляем к существующему Bronze, если он есть
    if BRONZE_PATH.exists():
        existing = pd.read_parquet(BRONZE_PATH)
        bronze = pd.concat([existing, new_data], ignore_index=True)
        logger.info(f"Appended {len(new_data)} new defects to existing Bronze")
    else:
        bronze = new_data
        logger.info(f"Created new Bronze with {len(new_data)} defects")

    BRONZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    bronze.to_parquet(BRONZE_PATH, index=False)

    mark_processed(processed_rows)

    logger.info(f"Total wafers in Bronze: {bronze['wafer_id'].nunique()}")
    logger.info(f"Total defects in Bronze: {len(bronze)}")
    logger.info(f"Marked {len(processed_rows)} versions as processed")
    logger.info(f"Saved: {sql_path(BRONZE_PATH)}")


if __name__ == "__main__":
    build_bronze()