import duckdb

from src.config import BRONZE_PATH, GOLD_PATH, SILVER_PATH, sql_path
from src.ingestion.metadata import latest_versions, source_files_count
from src.logger import logger


def quality_check():
    """
    Runs 19 data quality invariants across Raw, Bronze, Silver and Gold.

    Checks:
    - Raw: every source file has a raw version, no missing/empty raw files
    - Bronze/Silver/Gold: layers are not empty
    - Silver: no duplicate defects, no NULL coordinates,
              no negative sizes/area, all d_size > 0
    - Gold: no duplicate inspection runs, no NULL defects_count,
            Gold.total_defects == Silver.rows,
            all Silver runs present in Gold,
            runs with non-zero-area defects have non-NULL avg_defect_area,
            risk_score within [0, 1]

    Raises SystemExit(1) if any check fails.
    """
    con = duckdb.connect()

    # 1. Базовые счётчики по слоям
    bronze_rows = con.execute(f"""
        SELECT COUNT(*) FROM '{sql_path(BRONZE_PATH)}'
    """).fetchone()[0]

    silver_rows = con.execute(f"""
        SELECT COUNT(*) FROM '{sql_path(SILVER_PATH)}'
    """).fetchone()[0]

    gold_rows = con.execute(f"""
        SELECT COUNT(*) FROM '{sql_path(GOLD_PATH)}'
    """).fetchone()[0]

    logger.info(f"Bronze rows: {bronze_rows}")
    logger.info(f"Silver rows: {silver_rows}")
    logger.info(f"Gold runs: {gold_rows}")

    # 1b. Проверки raw ↔ source
    raw_versions = latest_versions()
    source_count = source_files_count()

    logger.info(f"Source files: {source_count}")
    logger.info(f"Raw versions (latest per file): {len(raw_versions)}")

    missing_raw_files = 0
    empty_raw_files = 0
    for file_stem, raw_path in raw_versions.items():
        if not raw_path.exists():
            missing_raw_files += 1
        elif raw_path.stat().st_size == 0:
            empty_raw_files += 1

    logger.info(f"Missing raw files: {missing_raw_files}")
    logger.info(f"Empty raw files: {empty_raw_files}")

    # 2. Проверки Silver
    silver_stats = con.execute(f"""
        SELECT
            COUNT(*) - COUNT(DISTINCT (wafer_id, inspection_run_id, defect_id)) AS duplicate_defects,
            COUNT(*) - COUNT(x_rel) AS null_x_rel,
            COUNT(*) - COUNT(y_rel) AS null_y_rel,
            COUNT(*) FILTER (WHERE x_size < 0) AS invalid_x_size,
            COUNT(*) FILTER (WHERE y_size < 0) AS invalid_y_size,
            COUNT(*) FILTER (WHERE defect_area < 0) AS invalid_area,
            COUNT(*) FILTER (WHERE d_size <= 0) AS invalid_d_size
        FROM '{sql_path(SILVER_PATH)}'
    """).fetchone()

    logger.info(f"Duplicate defects: {silver_stats[0]}")
    logger.info(f"NULL x_rel: {silver_stats[1]}")
    logger.info(f"NULL y_rel: {silver_stats[2]}")
    logger.info(f"Negative x_size: {silver_stats[3]}")
    logger.info(f"Negative y_size: {silver_stats[4]}")
    logger.info(f"Negative defect_area: {silver_stats[5]}")
    logger.info(f"Non-positive d_size: {silver_stats[6]}")

    # 3. Проверки Gold
    gold_stats = con.execute(f"""
        SELECT
            COUNT(*) - COUNT(DISTINCT (wafer_id, inspection_run_id, inspection_station))
                AS duplicate_runs,
            COUNT(*) - COUNT(defects_count) AS null_defects_count,
            SUM(defects_count) AS total_defects,
            COUNT(*) FILTER (
                WHERE defects_count > zero_area_defects
                  AND avg_defect_area IS NULL
            ) AS runs_with_defects_but_no_avg,
            COUNT(*) FILTER (WHERE risk_score < 0 OR risk_score > 1)
                AS invalid_risk_score
        FROM '{sql_path(GOLD_PATH)}'
    """).fetchone()

    logger.info(f"Duplicate inspection runs: {gold_stats[0]}")
    logger.info(f"NULL defects_count: {gold_stats[1]}")
    logger.info(f"Gold total defects: {gold_stats[2]}")
    logger.info(f"Runs with non-zero-area defects but NULL avg: {gold_stats[3]}")
    logger.info(f"Invalid risk_score (outside [0,1]): {gold_stats[4]}")

    # 4. Согласованность Gold <-> Silver
    missing_runs = con.execute(f"""
        SELECT COUNT(*)
        FROM (
            SELECT wafer_id, inspection_run_id, inspection_station
            FROM '{sql_path(SILVER_PATH)}'
            GROUP BY ALL
        ) s
        ANTI JOIN '{sql_path(GOLD_PATH)}' g
            ON s.wafer_id = g.wafer_id
           AND s.inspection_run_id = g.inspection_run_id
           AND s.inspection_station = g.inspection_station
    """).fetchone()[0]

    logger.info(f"Silver runs missing in Gold: {missing_runs}")

    # 5. Итоговые проверки
    checks = {
        "Source files >= raw versions": source_count >= len(raw_versions),
        "No missing raw files": missing_raw_files == 0,
        "No empty raw files": empty_raw_files == 0,
        "Bronze not empty": bronze_rows > 0,
        "Silver not empty": silver_rows > 0,
        "Gold not empty": gold_rows > 0,
        "No duplicate defects in Silver": silver_stats[0] == 0,
        "No NULL x_rel in Silver": silver_stats[1] == 0,
        "No NULL y_rel in Silver": silver_stats[2] == 0,
        "No negative x_size in Silver": silver_stats[3] == 0,
        "No negative y_size in Silver": silver_stats[4] == 0,
        "No negative defect_area in Silver": silver_stats[5] == 0,
        "All defects have positive d_size": silver_stats[6] == 0,
        "No duplicate inspection runs in Gold": gold_stats[0] == 0,
        "No NULL defects_count in Gold": gold_stats[1] == 0,
        "Gold total defects == Silver rows": gold_stats[2] == silver_rows,
        "All Silver runs present in Gold": missing_runs == 0,
        "Runs with non-zero-area defects have avg_defect_area": gold_stats[3] == 0,
        "Risk score within [0, 1]": gold_stats[4] == 0,
    }

    logger.info("QUALITY CHECKS")
    logger.info("=" * 50)

    all_passed = True
    for name, passed in checks.items():
        if passed:
            logger.info(f"PASS: {name}")
        else:
            logger.error(f"FAIL: {name}")
            all_passed = False

    if all_passed:
        logger.info("DATA QUALITY: PASS")
    else:
        logger.error("DATA QUALITY: FAIL")
        raise SystemExit(1)


if __name__ == "__main__":
    quality_check()