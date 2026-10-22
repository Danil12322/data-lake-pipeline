import duckdb

from src.config import BRONZE_PATH, SILVER_PATH, sql_path
from src.logger import logger


def build_silver():
    """
    Builds the Silver layer from Bronze.

    Applies:
    - deduplication by (wafer_id, inspection_run_id, defect_id),
      keeping the latest appended version (file_row_number DESC)
    - station-specific filters:
        1333034:       x_size > 0 AND y_size > 0 AND defect_area > 0
        TBI-0207-1122: 0 < d_size < 200000
    - size_category classification: Small (< 0.5), Medium (< 1.2), Large (>= 1.2)

    Writes to data/silver/defects_clean.parquet.
    """
    SILVER_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    con.execute(f"""
        COPY (
            WITH dedup AS (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY wafer_id, inspection_run_id, defect_id
                        ORDER BY file_row_number DESC
                    ) AS rn
                FROM read_parquet('{sql_path(BRONZE_PATH)}', file_row_number = true)
            )
            SELECT
                wafer_id,
                inspection_run_id,
                inspection_station,
                lot_id,
                source_wafer_id,
                slot,
                setup_id,
                step_id,
                result_timestamp,
                defect_id,
                x_rel,
                y_rel,
                x_size,
                y_size,
                defect_area,
                d_size,
                class_number,

                CASE
                    WHEN d_size < 0.5 THEN 'Small'
                    WHEN d_size < 1.2 THEN 'Medium'
                    ELSE 'Large'
                END AS size_category

            FROM dedup
            WHERE rn = 1
              AND (
                (
                    inspection_station = '1333034'
                    AND x_size > 0
                    AND y_size > 0
                    AND defect_area > 0
                )
                OR
                (
                    inspection_station = 'TBI-0207-1122'
                    AND d_size > 0
                    AND d_size < 200000
                )
              )
        )
        TO '{sql_path(SILVER_PATH)}'
        (FORMAT PARQUET)
    """)

    count = con.execute(f"""
        SELECT COUNT(*)
        FROM '{sql_path(SILVER_PATH)}'
    """).fetchone()[0]

    logger.info(f"Silver defects: {count}")
    logger.info(f"Saved: {sql_path(SILVER_PATH)}")


if __name__ == "__main__":
    build_silver()