from pathlib import Path
import pandas as pd

def extract_inspection_station(lines):
    for line in lines:
        if line.startswith("InspectionStationID"):
            parts = line.split('"')

            if len(parts) >= 6:
                return parts[5]

    return None

def extract_quoted_value(lines, field_name):
    for line in lines:
        if line.startswith(field_name):
            parts = line.split('"')

            if len(parts) >= 2:
                return parts[1]

    return None

def extract_result_timestamp(lines):
    for line in lines:
        if line.startswith("ResultTimestamp"):
            value = line[len("ResultTimestamp"):].strip()
            return value.rstrip(";")

    return None

def parse_wafer_file(file_path: str) -> pd.DataFrame:
    lines = Path(file_path).read_text(encoding="utf-8").splitlines()
    inspection_station = extract_inspection_station(lines)
    lot_id = extract_quoted_value(lines, "LotID")
    source_wafer_id = extract_quoted_value(lines, "WaferID")
    setup_id = extract_quoted_value(lines, "SetupID")
    step_id = extract_quoted_value(lines, "StepID")
    result_timestamp = extract_result_timestamp(lines)

    slot = None

    for line in lines:
        if line.startswith("Slot"):
            parts = line.split()

            if len(parts) >= 2:
                slot = int(parts[1].rstrip(";"))

            break

    start = None

    for i, line in enumerate(lines):
        if line.startswith("DefectList"):
            start = i + 1
            break

    if start is None:
        raise ValueError("DefectList not found")

    records = []

    for line in lines[start:]:
        line = line.strip()

        if not line or line.startswith("SummarySpec"):
            break
        line = line.strip().rstrip(";")
        parts = line.split()

        if len(parts) < 12:
            continue

        records.append({
            "defect_id": int(parts[0]),
            "x_rel": float(parts[1]),
            "y_rel": float(parts[2]),
            "x_index": int(parts[3]),
            "y_index": int(parts[4]),
            "x_size": float(parts[5]),
            "y_size": float(parts[6]),
            "defect_area": float(parts[7]),
            "d_size": float(parts[8]),
            "class_number": int(parts[9]),
            "test": int(parts[10]),
            "image_count": int(parts[11]),
            "inspection_station": inspection_station,
            "lot_id": lot_id,
            "source_wafer_id": source_wafer_id,
            "slot": slot,
            "setup_id": setup_id,
            "step_id": step_id,
            "result_timestamp": result_timestamp,
        })

    return pd.DataFrame(records)