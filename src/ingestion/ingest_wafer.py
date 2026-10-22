import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import METADATA_PATH, PROJECT_ROOT, RAW_DIR, SOURCE_DIR
from src.ingestion.metadata import load_metadata, save_metadata
from src.logger import logger


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest_wafer_files() -> None:
    """
    Ingests .000 files from source/wafer/ into data/raw/ with versioning.

    For each file:
    - computes SHA-256
    - if the hash matches the latest metadata version — skips (idempotency)
    - otherwise copies to data/raw/{file_stem}/v{N}.000 and appends metadata row

    New versions get processed_at = NULL; Bronze will pick them up later.
    """
    logger.info("=" * 50)
    logger.info("WAFER INGESTION STARTED")
    logger.info("=" * 50)

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")

    source_files = sorted(SOURCE_DIR.rglob("*.000"))
    if not source_files:
        raise ValueError(f"No .000 files found in {SOURCE_DIR}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    metadata = load_metadata()

    new_versions = 0
    unchanged = 0

    for src_path in source_files:
        file_name = src_path.name
        file_hash = sha256_of_file(src_path)
        file_size = src_path.stat().st_size

        history = metadata[metadata["file_name"] == file_name]

        if not history.empty:
            last = history.sort_values("version").iloc[-1]
            if last["hash"] == file_hash:
                logger.info(f"{file_name}: unchanged (v{int(last['version'])})")
                unchanged += 1
                continue

        next_version = 1 if history.empty else int(history["version"].max()) + 1
        target_dir = RAW_DIR / src_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"v{next_version}.000"

        shutil.copy2(src_path, target_path)

        row = {
            "file_name": file_name,
            "hash": file_hash,
            "version": next_version,
            "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file_size": file_size,
            "raw_path": str(target_path.relative_to(PROJECT_ROOT)),
            "processed_at": None,
        }
        metadata = pd.concat([metadata, pd.DataFrame([row])], ignore_index=True)
        new_versions += 1

        logger.info(f"{file_name}: new version v{next_version} ({file_size} bytes)")

    save_metadata(metadata)

    logger.info(f"Ingestion summary: {new_versions} new versions, {unchanged} unchanged")
    logger.info(f"Metadata saved: {METADATA_PATH}")
    logger.info("=" * 50)
    logger.info("WAFER INGESTION: SUCCESS")
    logger.info("=" * 50)


if __name__ == "__main__":
    ingest_wafer_files()