import duckdb

from src.config import GOLD_PATH, SILVER_PATH, sql_path
from src.logger import logger


def analyze_stations(con):
    """Per-station aggregates. Stations are not directly comparable (different scales)."""
    logger.info("=" * 60)
    logger.info("1. STATIONS OVERVIEW")
    logger.info("=" * 60)
    logger.info(
        "NOTE: inspection stations have different measurement scales. "
        "Do NOT compare avg_defect_area / max_defect_size directly."
    )

    result = con.execute(f"""
        SELECT
            inspection_station,
            COUNT(*) AS runs,
            SUM(defects_count) AS total_defects,
            ROUND(AVG(defects_count), 2) AS avg_defects_per_run,
            ROUND(AVG(avg_defect_area), 2) AS avg_area,
            ROUND(AVG(max_defect_size), 2) AS avg_max_size,
            SUM(large_defects) AS total_large,
            SUM(zero_area_defects) AS total_zero_area
        FROM '{sql_path(GOLD_PATH)}'
        GROUP BY inspection_station
        ORDER BY total_defects DESC
    """).df()

    logger.info("\n" + result.to_string(index=False))


def analyze_lots(con):
    """Top-5 worst lots by average risk_score."""
    logger.info("\n" + "=" * 60)
    logger.info("2. TOP-5 WORST LOTS BY AVG RISK SCORE")
    logger.info("=" * 60)

    result = con.execute(f"""
        SELECT
            lot_id,
            COUNT(*) AS runs,
            SUM(defects_count) AS total_defects,
            ROUND(AVG(risk_score), 4) AS avg_risk_score,
            ROUND(MAX(risk_score), 4) AS max_risk_score
        FROM '{sql_path(GOLD_PATH)}'
        GROUP BY lot_id
        ORDER BY avg_risk_score DESC
        LIMIT 5
    """).df()

    logger.info("\n" + result.to_string(index=False))


def analyze_classes(con):
    """Defect classes distribution from Silver."""
    logger.info("\n" + "=" * 60)
    logger.info("3. DEFECT CLASSES DISTRIBUTION")
    logger.info("=" * 60)

    result = con.execute(f"""
        WITH totals AS (
            SELECT COUNT(*) AS total FROM '{sql_path(SILVER_PATH)}'
        )
        SELECT
            class_number,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / (SELECT total FROM totals), 2) AS share_pct,
            ROUND(AVG(d_size), 4) AS avg_d_size,
            ROUND(AVG(defect_area), 4) AS avg_area
        FROM '{sql_path(SILVER_PATH)}'
        GROUP BY class_number
        ORDER BY count DESC
    """).df()

    logger.info("\n" + result.to_string(index=False))


def analyze_alerts(con):
    """Runs with risk_score > 0.4 — candidates for engineer review."""
    logger.info("\n" + "=" * 60)
    logger.info("4. ALERT: RUNS WITH risk_score > 0.4")
    logger.info("=" * 60)

    result = con.execute(f"""
        SELECT
            wafer_id,
            inspection_run_id,
            inspection_station,
            defects_count,
            large_defects,
            zero_area_defects,
            risk_score
        FROM '{sql_path(GOLD_PATH)}'
        WHERE risk_score > 0.4
        ORDER BY risk_score DESC
    """).df()

    if result.empty:
        logger.info("No runs above threshold.")
    else:
        logger.info("\n" + result.to_string(index=False))


def station_lot_analysis():
    """
    Station & lot analytics on Gold and Silver layers.

    Prints four views:
    1. Stations overview (runs, defects, sizes, large/zero-area counts)
    2. Top-5 worst lots by average risk_score
    3. Defect classes distribution
    4. Runs with risk_score > 0.4 (alerts)
    """
    con = duckdb.connect()

    logger.info("=" * 60)
    logger.info("STATION & LOT ANALYSIS")
    logger.info("=" * 60)

    analyze_stations(con)
    analyze_lots(con)
    analyze_classes(con)
    analyze_alerts(con)

    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    station_lot_analysis()