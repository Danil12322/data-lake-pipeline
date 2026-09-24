import duckdb

from logger import logger

def quality_check():
    con = duckdb.connect()

    result = con.execute("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT order_id) AS unique_orders,
            COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_orders,
            COUNT(*) - COUNT(total_amount) AS null_total_amount,
            COUNT(*) FILTER (WHERE quantity <= 0) AS invalid_quantity,
            COUNT(*) FILTER (WHERE price < 0) AS invalid_price
        FROM 'data/bronze/sales.parquet'
    """).fetchone()

    logger.info(f"Total rows: {result[0]}")
    logger.info(f"Unique orders: {result[1]}")
    logger.info(f"Duplicate orders: {result[2]}")
    logger.info(f"NULL total_amount: {result[3]}")
    logger.info(f"Invalid quantity: {result[4]}")
    logger.info(f"Invalid price: {result[5]}")

    bronze_customers = con.execute("""
        SELECT COUNT(DISTINCT customer_id)
        FROM 'data/bronze/sales.parquet'
    """).fetchone()[0]

    gold_customers = con.execute("""
        SELECT COUNT(*)
        FROM 'data/gold/customer_sales.parquet'
    """).fetchone()[0]

    logger.info(f"Bronze customers: {bronze_customers}")
    logger.info(f"Gold customers: {gold_customers}")
    logger.info(f"Customer count matches: {bronze_customers == gold_customers}")

    checks = {
        "No duplicate orders": result[2] == 0,
        "No NULL total_amount": result[3] == 0,
        "No invalid quantity": result[4] == 0,
        "No negative price": result[5] == 0,
        "Customer count matches": bronze_customers == gold_customers,
    }

    logger.info("QUALITY CHECKS")

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