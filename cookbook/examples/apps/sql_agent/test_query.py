from agents import db_url
from sqlalchemy import create_engine, text

# Tạo kết nối đến database
engine = create_engine(db_url)

# Câu truy vấn test
query = """
SELECT 
    c.sector,
    AVG(prices."Close") as avg_price,
    MAX(prices."Close") as max_price,
    MIN(prices."Close") as min_price,
    COUNT(DISTINCT c.symbol) as num_companies
FROM prices
JOIN companies c ON prices."Ticker" = c.symbol
WHERE c.sector IN ('Technology', 'Healthcare')
GROUP BY c.sector
ORDER BY avg_price DESC;
"""

# Thực thi câu truy vấn
with engine.connect() as conn:
    result = conn.execute(text(query))
    rows = result.fetchall()
    
    # In kết quả
    print("\nKết quả so sánh hiệu suất ngành:")
    print("-" * 80)
    print(f"{'Ngành':<15} {'Giá TB':<12} {'Giá Cao':<12} {'Giá Thấp':<12} {'Số CT':<8}")
    print("-" * 80)
    for row in rows:
        print(f"{row[0]:<15} {row[1]:<12.2f} {row[2]:<12.2f} {row[3]:<12.2f} {row[4]:<8}")
    print("-" * 80) 