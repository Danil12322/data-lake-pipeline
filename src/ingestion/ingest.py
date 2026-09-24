import csv
from pathlib import Path
import hashlib
from datetime import datetime
import shutil

from logger import logger

SOURCE_DIR = Path("source")
RAW_DIR = Path("data/raw")
METADATA_FILE = Path("data/metadata/files.csv")

def calculate_hash(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def check_file(reader, file_name, current_hash):
    found = False

    for row in reader:
        if row["file_name"] == file_name:
            found = True

            if row["hash"] == current_hash:
                return "UNCHANGED"

    if found:
        return "CHANGED"

    return "NEW"


def get_latest_version(reader, file_name):
    latest_version = 0

    for row in reader:
        if row["file_name"] == file_name:
            version = int(row["version"])

            if version > latest_version:
                latest_version = version

    return latest_version


def ingest_file(file_path):
    current_hash = calculate_hash(file_path)

    with open(METADATA_FILE, "r", newline="") as metadata_file:
        reader = csv.DictReader(metadata_file)
        status = check_file(reader, file_path.name, current_hash)

    logger.info(f"File: {file_path.name}")
    logger.info(f"Hash: {current_hash}")
    logger.info(f"Status: {status}")

    if status == "UNCHANGED":
        return

    with open(METADATA_FILE, "r", newline="") as metadata_file:
        reader = csv.DictReader(metadata_file)
        latest_version = get_latest_version(reader, file_path.name)

    new_version = latest_version + 1

    raw_dir = RAW_DIR / file_path.stem
    raw_dir.mkdir(parents=True, exist_ok=True)

    destination = raw_dir / f"version_{new_version}.csv"

    import shutil
    shutil.copy2(file_path, destination)

    file_size = file_path.stat().st_size
    ingested_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("data/metadata/files.csv", "a", newline="") as metadata_file:
        writer = csv.writer(metadata_file)

        writer.writerow([
            file_path.name,
            current_hash,
            new_version,
            ingested_at,
            file_size
        ])

    logger.info(f"Latest version: {latest_version}")
    logger.info(f"New version: {new_version}")
    logger.info(f"Saved: {destination}")
    logger.info("Metadata updated")



def ingest():
    for file in SOURCE_DIR.glob("*.csv"):
        ingest_file(file)


if __name__ == "__main__":
    ingest()


