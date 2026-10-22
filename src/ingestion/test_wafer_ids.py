from pathlib import Path

files = sorted(Path("source/wafer").rglob("*.000"))

for file in files:
    wafer_id = file.parent.name
    inspection_run_id = file.stem

    print(
        f"wafer_id={wafer_id} | "
        f"inspection_run_id={inspection_run_id}"
    )