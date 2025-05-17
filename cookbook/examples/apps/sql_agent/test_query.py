import pandas as pd
from sqlalchemy import create_engine, text
from agents import db_url

def test_timezone_query():
    print("Kết nối database...")
    engine = create_engine(db_url)

    # Test: Lấy giá đóng cửa của Microsoft ngày 15/3/2024 với xử lý timezone
    print("\nTest: Lấy giá đóng cửa của Microsoft (timezone aware)")
    query = """
    SELECT 
        p."Date",
        p."Close" as closing_price
    FROM prices p
    WHERE p."Ticker" = 'MSFT'
    AND p."Date" AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York'::date = '2024-03-15'::date
    LIMIT 1;
    """
    result = pd.read_sql(text(query), engine)
    print("Kết quả:", result)

    # Kiểm tra thêm các giá trị ngày thực tế
    print("\nKiểm tra các giá trị ngày thực tế của MSFT:")
    check_query = """
    SELECT "Date", "Close"
    FROM prices
    WHERE "Ticker" = 'MSFT'
    ORDER BY "Date" DESC
    LIMIT 5;
    """
    check_result = pd.read_sql(text(check_query), engine)
    print(check_result)

if __name__ == "__main__":
    test_timezone_query() 