from pathlib import Path
import pandas as pd

from src.ingestion.wafer_parser import parse_wafer_file


def test_parse_demo_file():
    """Проверяет, что парсер корректно читает демо-файл."""
    demo_path = Path("source/wafer/M000001_DEMO/M000001_DEMO-01.000")
    assert demo_path.exists(), f"Demo file not found: {demo_path}"

    df = parse_wafer_file(str(demo_path))

    # Проверяем, что DataFrame не пустой
    assert not df.empty, "Parsed DataFrame is empty"

    # Проверяем, что все нужные колонки на месте
    expected_columns = [
        "defect_id", "x_rel", "y_rel", "x_index", "y_index",
        "x_size", "y_size", "defect_area", "d_size",
        "class_number", "test", "image_count",
        "inspection_station", "lot_id", "source_wafer_id",
        "slot", "setup_id", "step_id", "result_timestamp",
        "sample_center_x", "sample_center_y",
        "die_pitch_x", "die_pitch_y",
    ]
    for col in expected_columns:
        assert col in df.columns, f"Missing column: {col}"

    # Проверяем, что в демо-файле 2 дефекта
    assert len(df) == 2, f"Expected 2 defects, got {len(df)}"

    # Проверяем, что метаданные извлекаются
    assert df["lot_id"].iloc[0] is not None, "lot_id is None"
    assert df["source_wafer_id"].iloc[0] is not None, "source_wafer_id is None"

    print(f"✅ Parsed {len(df)} defects from {demo_path.name}")
    print(df.head())


if __name__ == "__main__":
    test_parse_demo_file()
    print("All parser tests passed!")