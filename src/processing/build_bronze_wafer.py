from pathlib import Path
import pandas as pd

from src.ingestion.metadata import latest_versions
from src.ingestion.wafer_parser import parse_wafer_file, extract_sample_test_plan
from src.logger import logger


def build_bronze():
    versions = latest_versions()
    if not versions:
        raise FileNotFoundError("No raw versions found. Run ingestion first.")

    dfs = []
    plan_dfs = []  # <--- Инициализируем список для планов

    for file_stem, raw_path in sorted(versions.items()):
        df = parse_wafer_file(raw_path)
        if df.empty:
            continue

        # Формируем wafer_id и inspection_run_id
        df["wafer_id"] = df["lot_id"]
        df["inspection_run_id"] = (
            df["lot_id"].astype(str) + "-" + df["source_wafer_id"].astype(str)
        )
        dfs.append(df)
        logger.info(
            f"{file_stem}: {len(df)} defects ({df['source_wafer_id'].nunique()} wafers)"
        )

        # Сохраняем SampleTestPlan (с привязкой ко всем пластинам в файле)
        lines = Path(raw_path).read_text(encoding="utf-8").splitlines()
        plan = extract_sample_test_plan(lines)
        if plan:
            plan_df = pd.DataFrame(plan, columns=["x_index", "y_index"])
            # Получаем все уникальные wafer_id из этого файла
            wafer_ids = df["source_wafer_id"].unique()
            lot_id = df["lot_id"].iloc[0] if not df.empty else None

            for wafer_id in wafer_ids:
                plan_copy = plan_df.copy()
                plan_copy["lot_id"] = lot_id
                plan_copy["wafer_id"] = wafer_id
                plan_dfs.append(plan_copy)

    bronze = pd.concat(dfs, ignore_index=True)
    Path("data/bronze").mkdir(parents=True, exist_ok=True)
    bronze.to_parquet("data/bronze/defects.parquet", index=False)

    # Сохраняем общий test_plan.parquet
    if plan_dfs:
        plan_all = pd.concat(plan_dfs, ignore_index=True)
        # Дедуплицируем (если один и тот же план привязан к нескольким пластинам)
        plan_all = plan_all.drop_duplicates(subset=["lot_id", "wafer_id", "x_index", "y_index"])
        plan_all.to_parquet("data/bronze/test_plan.parquet", index=False)
        logger.info(f"Saved test_plan.parquet: {len(plan_all)} frames")

    logger.info(f"Total wafers: {bronze['inspection_run_id'].nunique()}")
    logger.info(f"Total defects: {len(bronze)}")
    logger.info("Saved: data/bronze/defects.parquet")


if __name__ == "__main__":
    build_bronze()