import pandas as pd
from sqlalchemy import create_engine
from agents import db_url

def check_date():
    print("Kết nối database...")
    engine = create_engine(db_url)
    
    # Kiểm tra dữ liệu Microsoft
    query = """
    SELECT "Date", "Close" 
    FROM prices 
    WHERE "Ticker" = 'MSFT' 
    AND "Date" >= '2024-03-14' 
    AND "Date" <= '2024-03-16'
    ORDER BY "Date";
    """
    
    df = pd.read_sql(query, engine)
    print("\nDữ liệu Microsoft từ 14/3 đến 16/3/2024:")
    print(df)
    
    # Kiểm tra định dạng ngày
    print("\nĐịnh dạng cột Date:", df['Date'].dtype)
    print("Mẫu giá trị Date:", df['Date'].iloc[0] if not df.empty else "Không có dữ liệu")

if __name__ == "__main__":
    check_date() 