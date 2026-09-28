import duckdb
from pathlib import Path

from logger import logger


def build_silver():
    Path("data/silver").mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()

    con.execute("""
        COPY (
            SELECT
                order_id,
                customer_id,
                product,
                quantity,
                price,
                timestamp,
                total_amount
            FROM 'data/bronze/sales.parquet'
            WHERE quantity > 0
              AND price >= 0
        )
        TO 'data/silver/orders.parquet'
        (FORMAT PARQUET)
    """)

    logger.info("Silver file created")
    logger.info("data/silver/orders.parquet")


if __name__ == "__main__":
    build_silver()