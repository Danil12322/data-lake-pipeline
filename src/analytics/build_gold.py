import duckdb
from pathlib import Path

from logger import logger

def build_gold():
    Path("data/gold").mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    con.execute("""
        COPY (
            SELECT
                customer_id,
                COUNT(*) AS orders_count,
                SUM(total_amount) AS total_spent
            FROM 'data/bronze/sales.parquet'
            GROUP BY customer_id
        )
        TO 'data/gold/customer_sales.parquet'
        (FORMAT PARQUET)
    """)

    logger.info("Gold file created")
    logger.info("data/gold/customer_sales.parquet")


if __name__ == "__main__":
    build_gold()