import duckdb
from pathlib import Path

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

print("Gold file created:")
print("data/gold/customer_sales.parquet")

result = con.execute("""
    SELECT *
    FROM 'data/gold/customer_sales.parquet'
    ORDER BY total_spent DESC
""").fetchdf()

print(result)