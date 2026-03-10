from sqlalchemy import create_engine
import pandas as pd

# 🔐 Replace YOUR_PASSWORD
engine = create_engine(
    "postgresql://postgres:newpassword123@localhost:5432/inventory_ai"
)

query = """
SELECT *
FROM (
    SELECT 
        p.id,
        p.name,
        p.reorder_level,
        p.stock_quantity
            + COALESCE(SUM(
                CASE 
                    WHEN t.transaction_type = 'restock' THEN t.quantity
                    WHEN t.transaction_type = 'sale' THEN -t.quantity
                END
            ), 0) AS current_stock
    FROM products p
    LEFT JOIN transactions t ON p.id = t.product_id
    GROUP BY p.id
) inventory_status
WHERE current_stock <= reorder_level;
"""

df = pd.read_sql(query, engine)

if df.empty:
    print("✅ All products are sufficiently stocked.")
else:
    print("🚨 REORDER ALERT 🚨")
    print(df)
