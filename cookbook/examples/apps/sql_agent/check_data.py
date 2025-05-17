import pandas as pd
from sqlalchemy import create_engine
from agents import db_url

def check_data():
    print("Kết nối database...")
    engine = create_engine(db_url)
    
    # Kiểm tra tất cả dữ liệu Microsoft
    query = """
    SELECT "Date", "Close" 
    FROM prices 
    WHERE "Ticker" = 'MSFT'
    ORDER BY "Date" DESC
    LIMIT 5
    """
    
    df = pd.read_sql(query, engine)
    print("\n5 dòng dữ liệu Microsoft gần nhất:")
    print(df)
    
    # Kiểm tra định dạng ngày
    print("\nĐịnh dạng cột Date:", df['Date'].dtype)
    if not df.empty:
        print("Mẫu giá trị Date:", df['Date'].iloc[0])
        print("Mẫu giá trị Close:", df['Close'].iloc[0])
    else:
        print("Không có dữ liệu trong bảng prices")

if __name__ == "__main__":
    check_data() 