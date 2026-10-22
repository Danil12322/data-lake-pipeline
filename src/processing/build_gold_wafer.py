import duckdb

from src.config import BRONZE_PATH, GOLD_PATH, SILVER_PATH, sql_path
from src.logger import logger


def build_gold():
    """
    Builds the Gold layer from Bronze + Silver.

    One row = one inspection run. Includes:
    - metadata from Bronze (wafer_id, inspection_run_id, inspection_station, ...)
    - aggregates from Silver: defects_count, avg_defect_area, max_defect_size,
      large_defects, zero_area_defects
    - risk_score: min-max normalized combination of 5 features, clamped to [0, 1]

    Bronze is used for metadata (LEFT JOIN) so that runs with zero valid defects
    after Silver filtering are preserved in Gold with defects_count = 0.

    Writes to data/gold/wafer_metrics.parquet.
    """
    GOLD_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    con.execute(f"""
        COPY (

        WITH base AS (
            SELECT
                b.wafer_id,
                b.inspection_run_id,
                b.inspection_station,
                b.lot_id,
                b.source_wafer_id,
                b.slot,
                b.setup_id,
                b.step_id,
                b.result_timestamp,
                COUNT(s.defect_id) AS defects_count,
                ROUND(AVG(CASE WHEN s.defect_area > 0 THEN s.defect_area END), 6) AS avg_defect_area,
                MAX(s.d_size) AS max_defect_size,
                SUM(CASE WHEN s.size_category = 'Large' THEN 1 ELSE 0 END) AS large_defects,
                SUM(CASE WHEN s.defect_area = 0 THEN 1 ELSE 0 END) AS zero_area_defects
            FROM (
                SELECT DISTINCT
                    wafer_id,
                    inspection_run_id,
                    inspection_station,
                    lot_id,
                    source_wafer_id,
                    slot,
                    setup_id,
                    step_id,
                    result_timestamp
                FROM '{sql_path(BRONZE_PATH)}'
            ) b
            LEFT JOIN '{sql_path(SILVER_PATH)}' s
                ON b.wafer_id = s.wafer_id
               AND b.inspection_run_id = s.inspection_run_id
            GROUP BY
                b.wafer_id,
                b.inspection_run_id,
                b.inspection_station,
                b.lot_id,
                b.source_wafer_id,
                b.slot,
                b.setup_id,
                b.step_id,
                b.result_timestamp
        ),
        ranges AS (
            SELECT
                MIN(defects_count) AS min_defects,
                MAX(defects_count) AS max_defects,
                MIN(LN(1 + COALESCE(avg_defect_area, 0))) AS min_log_area,
                MAX(LN(1 + COALESCE(avg_defect_area, 0))) AS max_log_area,
                MIN(COALESCE(max_defect_size, 0)) AS min_max_size,
                MAX(COALESCE(max_defect_size, 0)) AS max_max_size,
                MIN(large_defects) AS min_large,
                MAX(large_defects) AS max_large,
                MIN(CASE WHEN defects_count > 0
                         THEN zero_area_defects * 1.0 / defects_count
                         ELSE 0 END) AS min_zero_ratio,
                MAX(CASE WHEN defects_count > 0
                         THEN zero_area_defects * 1.0 / defects_count
                         ELSE 0 END) AS max_zero_ratio
            FROM base
        ),
        scored AS (
            SELECT
                b.*,
                CASE WHEN r.max_defects > r.min_defects
                     THEN (b.defects_count - r.min_defects) * 1.0
                          / (r.max_defects - r.min_defects)
                     ELSE 0 END AS n_defects,
                CASE WHEN r.max_log_area > r.min_log_area
                     THEN (LN(1 + COALESCE(b.avg_defect_area, 0)) - r.min_log_area) * 1.0
                          / (r.max_log_area - r.min_log_area)
                     ELSE 0 END AS n_log_avg_area,
                CASE WHEN r.max_max_size > r.min_max_size
                     THEN (COALESCE(b.max_defect_size, 0) - r.min_max_size) * 1.0
                          / (r.max_max_size - r.min_max_size)
                     ELSE 0 END AS n_max_size,
                CASE WHEN r.max_large > r.min_large
                     THEN (b.large_defects - r.min_large) * 1.0
                          / (r.max_large - r.min_large)
                     ELSE 0 END AS n_large,
                CASE WHEN r.max_zero_ratio > r.min_zero_ratio
                     THEN (
                            (CASE WHEN b.defects_count > 0
                                  THEN b.zero_area_defects * 1.0 / b.defects_count
                                  ELSE 0 END) - r.min_zero_ratio
                          ) * 1.0
                          / (r.max_zero_ratio - r.min_zero_ratio)
                     ELSE 0 END AS n_zero_ratio
            FROM base b
            CROSS JOIN ranges r
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
            defects_count,
            avg_defect_area,
            max_defect_size,
            large_defects,
            zero_area_defects,
            ROUND(
                GREATEST(0, LEAST(1,
                    n_defects      * 0.40
                  + n_log_avg_area * 0.20
                  + n_max_size     * 0.20
                  + n_large        * 0.10
                  - n_zero_ratio   * 0.10
                )),
                4
            ) AS risk_score
        FROM scored
        ORDER BY wafer_id, inspection_run_id

        )

        TO '{sql_path(GOLD_PATH)}'
        (FORMAT PARQUET)
    """)

    count = con.execute(f"""
        SELECT COUNT(*) FROM '{sql_path(GOLD_PATH)}'
    """).fetchone()[0]

    logger.info(f"Gold wafers: {count}")
    logger.info(f"Saved: {sql_path(GOLD_PATH)}")


if __name__ == "__main__":
    build_gold()