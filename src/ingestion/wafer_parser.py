from pathlib import Path
import pandas as pd


def extract_inspection_station(lines, start_idx=0):
    for line in lines[start_idx:]:
        if line.startswith("InspectionStationID"):
            parts = line.split('"')
            if len(parts) >= 6:
                return parts[5]
    return None


def extract_quoted_value(lines, field_name, start_idx=0):
    for line in lines[start_idx:]:
        if line.startswith(field_name):
            parts = line.split('"')
            if len(parts) >= 2:
                return parts[1]
    return None


def extract_sample_center(lines, start_idx=0):
    for line in lines[start_idx:]:
        if line.startswith("SampleCenterLocation"):
            parts = line.replace(";", "").split()
            if len(parts) >= 3:
                return float(parts[1]), float(parts[2])
    return None, None


def extract_die_pitch(lines, start_idx=0):
    for line in lines[start_idx:]:
        if line.startswith("DiePitch"):
            parts = line.replace(";", "").split()
            if len(parts) >= 3:
                return float(parts[1]), float(parts[2])
    return None, None


def extract_slot(lines, start_idx=0):
    for line in lines[start_idx:]:
        if line.startswith("Slot"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1].rstrip(";"))
    return None


def extract_sample_test_plan(lines):
    """Извлекает список кадров из SampleTestPlan."""
    for i, line in enumerate(lines):
        if line.startswith("SampleTestPlan"):
            plan = []
            j = i + 1
            while j < len(lines):
                line = lines[j].strip()
                if not line or line.startswith("AreaPerTest") or line.startswith("DefectRecordSpec"):
                    break
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        x = int(parts[0])
                        y = int(parts[1])
                        plan.append((x, y))
                    except ValueError:
                        break
                j += 1
            return plan
    return []


def parse_wafer_file(file_path: str) -> pd.DataFrame:
    lines = Path(file_path).read_text(encoding="utf-8").splitlines()
    records = []

    start_indices = [
        i + 1 for i, line in enumerate(lines) if line.startswith("DefectList")
    ]

    if not start_indices:
        raise ValueError(f"DefectList not found in {file_path}")

    for block_idx, start in enumerate(start_indices):
        header_start = 0 if block_idx == 0 else start_indices[block_idx - 1] + 1

        inspection_station = extract_inspection_station(lines[:start], header_start)
        lot_id = extract_quoted_value(lines[:start], "LotID", header_start)
        source_wafer_id = extract_quoted_value(lines[:start], "WaferID", header_start)
        setup_id = extract_quoted_value(lines[:start], "SetupID", header_start)
        step_id = extract_quoted_value(lines[:start], "StepID", header_start)
        result_timestamp = None
        for line in lines[header_start:start]:
            if line.startswith("ResultTimestamp"):
                result_timestamp = line[len("ResultTimestamp"):].strip().rstrip(";")
                break

        sample_center_x, sample_center_y = extract_sample_center(lines[:start], header_start)
        die_pitch_x, die_pitch_y = extract_die_pitch(lines[:start], header_start)
        slot = extract_slot(lines[:start], header_start)

        end = start_indices[block_idx + 1] - 1 if block_idx + 1 < len(start_indices) else len(lines)

        for line in lines[start:end]:
            line = line.strip()
            if not line:
                break
            if line.startswith("SummarySpec") or line.startswith("EndOfFile"):
                break
            if not line[0].isdigit():
                break
            line = line.rstrip(";")
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
                "sample_center_x": sample_center_x,
                "sample_center_y": sample_center_y,
                "die_pitch_x": die_pitch_x,
                "die_pitch_y": die_pitch_y,
            })

    return pd.DataFrame(records)