from pathlib import Path
from src.ingestion.wafer_parser import parse_wafer_file

# Ищем все .000 файлы во всех подпапках
files = sorted(Path("source").rglob("*.000"))

if not files:
    raise FileNotFoundError("No .000 files found in source")

print(f"Found {len(files)} wafer files\n")

wafer_file = files[0]
print("Using:", wafer_file)
print()

df = parse_wafer_file(wafer_file)

print(df.head())
print()
print(df.dtypes)
print()
print("Rows:", len(df))