import hashlib
from pathlib import Path
from datetime import datetime


def calculate_hash(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()

now = datetime.now()
file = Path("source/sales_001.csv")

print("Hash: ", calculate_hash(file))
print("Size: ", file.stat().st_size)
print("Time: ", now)