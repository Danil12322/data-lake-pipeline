import duckdb

from src.logger import logger


def check_invalid_sizes():
    con = duckdb.connect()

    logger.info("=" * 50)
    logger.info("INVALID SIZE DIAGNOSTICS")
    logger.info("=" * 50)

    # 1. Какие значения у «невалидных» записей
    logger.info("Distribution of x_size / y_size / defect_area for invalid rows:")
    result = con.execute("""
        SELECT
            x_size,
            y_size,
            defect_area,
            d_size,
            class_number,
            size_category,
            COUNT(*) AS cnt
        FROM 'data/silver/defects_clean.parquet'
        WHERE x_size <= 0 OR y_size <= 0 OR defect_area <= 0
        GROUP BY ALL
        ORDER BY cnt DESC
    """).df()
    logger.info("\n" + result.to_string(index=False))

    # 2. Распределение по wafer'ам
    logger.info("\nInvalid rows per wafer:")
    result = con.execute("""
        SELECT
            wafer_id,
            inspection_run_id,
            COUNT(*) AS invalid_cnt
        FROM 'data/silver/defects_clean.parquet'
        WHERE x_size <= 0 OR y_size <= 0 OR defect_area <= 0
        GROUP BY ALL
        ORDER BY invalid_cnt DESC
    """).df()
    logger.info("\n" + result.to_string(index=False))

    # 3. Сравнение Silver и Bronze
    logger.info("\nSame defect_ids in Bronze vs Silver:")
    result = con.execute("""
        SELECT
            s.wafer_id,
            s.defect_id,
            b.x_size AS bronze_x_size,
            b.y_size AS bronze_y_size,
            b.defect_area AS bronze_area,
            s.x_size AS silver_x_size,
            s.y_size AS silver_y_size,
            s.defect_area AS silver_area
        FROM 'data/silver/defects_clean.parquet' s
        JOIN 'data/bronze/defects.parquet' b
            ON b.wafer_id = s.wafer_id
           AND b.defect_id = s.defect_id
        WHERE s.x_size <= 0 OR s.y_size <= 0 OR s.defect_area <= 0
        LIMIT 30
    """).df()
    logger.info("\n" + result.to_string(index=False))


if __name__ == "__main__":
    check_invalid_sizes()