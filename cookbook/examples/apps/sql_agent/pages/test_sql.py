import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd

# Kết nối database
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
engine = create_engine(db_url)

def run_sql_query(query):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        return f"Lỗi: {str(e)}"

st.title("SQL Query Tester")
st.write("Nhập câu lệnh SQL của bạn vào đây:")

# Text area để nhập SQL
sql_query = st.text_area("SQL Query", height=150)

# Nút để chạy query
if st.button("Chạy Query"):
    if sql_query:
        st.write("Kết quả:")
        result = run_sql_query(sql_query)
        if isinstance(result, pd.DataFrame):
            st.dataframe(result)
        else:
            st.error(result)
    else:
        st.warning("Vui lòng nhập câu lệnh SQL")

# Hiển thị một số ví dụ
st.write("Ví dụ:")
examples = [
    "SELECT \"Close\" FROM prices WHERE \"Ticker\" = 'AAPL' AND \"Date\" = '2024-01-01' LIMIT 1",
    "SELECT * FROM companies LIMIT 5",
    "SELECT \"Ticker\", \"Date\", \"Close\" FROM prices WHERE \"Ticker\" = 'MSFT' ORDER BY \"Date\" DESC LIMIT 5"
]

for example in examples:
    if st.button(f"Chạy: {example}"):
        st.write("Kết quả:")
        result = run_sql_query(example)
        if isinstance(result, pd.DataFrame):
            st.dataframe(result)
        else:
            st.error(result)

# Nút quay lại trang chính
if st.button("Quay lại trang chính"):
    st.switch_page("app.py") 