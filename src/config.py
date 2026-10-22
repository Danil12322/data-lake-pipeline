from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = PROJECT_ROOT / "source" / "wafer"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
LOGS_DIR = PROJECT_ROOT / "logs"

METADATA_PATH = METADATA_DIR / "ingestion_log.csv"
BRONZE_PATH = BRONZE_DIR / "defects.parquet"
SILVER_PATH = SILVER_DIR / "defects_clean.parquet"
GOLD_PATH = GOLD_DIR / "wafer_metrics.parquet"


def sql_path(path: Path) -> str:
    """Converts Path to a forward-slash string suitable for DuckDB SQL."""
    return str(path).replace("\\", "/")