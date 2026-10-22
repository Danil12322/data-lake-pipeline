import duckdb

from src.config import GOLD_PATH, SILVER_PATH, BRONZE_PATH, sql_path
from src.logger import logger


def view_gold(limit: int = 20):
    """Prints the first N rows of Gold."""
    con = duckdb.connect()

    result = con.execute(f"""
        SELECT *
        FROM '{sql_path(SILVER_PATH)}'
        LIMIT {limit}
    """).df()

    logger.info(f"Gold preview (first {limit} rows):")
    logger.info("\n" + result.to_string(index=False))


if __name__ == "__main__":
    view_gold()