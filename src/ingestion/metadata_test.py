import csv
from pathlib import Path
import shutil

def check_file(reader, file_name, current_hash):
    for row in reader:
        if row["file_name"] == file_name:
            if row["hash"] == current_hash:
                return "UNCHANGED"
            else:
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

with open("data/metadata/files.csv", "r", newline="") as file:
    reader = csv.DictReader(file)
    result = check_file(
        reader,
        "sales_001.csv",
        "784bc34efe2086de8c940670e2526ae7618526a50f1297838fc9e9cef9c146a7"
    )

    print(result)

with open("data/metadata/files.csv", "r", newline="") as file:
    reader = csv.DictReader(file)
    latest_version = get_latest_version(
        reader,
        "sales_001.csv"
    )

    print("Latest version:", latest_version)
