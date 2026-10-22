import duckdb

from src.config import GOLD_PATH, sql_path
from src.logger import logger


def query_gold():
    """
    Prints top-20 inspection runs sorted by risk_score descending.

    Columns: wafer_id, inspection_run_id, inspection_station,
    defects_count, avg_defect_area, max_defect_size,
    large_defects, zero_area_defects, risk_score.
    """
    con = duckdb.connect()

    logger.info("=" * 50)
    logger.info("RISK SCORE: TOP RUNS")
    logger.info("=" * 50)

    result = con.execute(f"""
        SELECT
            wafer_id,
            inspection_run_id,
            inspection_station,
            defects_count,
            ROUND(avg_defect_area, 4) AS avg_defect_area,
            ROUND(max_defect_size, 4) AS max_defect_size,
            large_defects,
            zero_area_defects,
            risk_score
        FROM '{sql_path(GOLD_PATH)}'
        ORDER BY risk_score DESC
        LIMIT 20
    """).df()

    logger.info("\n" + result.to_string(index=False))


if __name__ == "__main__":
    query_gold()