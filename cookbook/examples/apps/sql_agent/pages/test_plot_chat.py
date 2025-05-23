import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Cấu hình trang
st.set_page_config(
    page_title="Plot Chat Tester",
    page_icon="💬",
    layout="wide"
)

# API endpoint
API_URL = "http://localhost:8000"

def call_plot_api(command: str) -> dict:
    """Gọi API để tạo biểu đồ"""
    try:
        response = requests.post(
            f"{API_URL}/plot/command",
            json={"command": command}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"API error: {response.text}"}
    except Exception as e:
        return {"error": str(e)}

# Khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Giao diện Streamlit
st.title("💬 Plot Chat Tester")
st.write("Test chức năng plot thông qua chat API")

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "plot_url" in message:
            st.image(message["plot_url"], caption=message["content"])
        else:
            st.markdown(message["content"])

# Input chat
if prompt := st.chat_input("Nhập câu hỏi của bạn về biểu đồ chứng khoán..."):
    # Thêm tin nhắn người dùng vào lịch sử
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Xử lý câu hỏi và hiển thị phản hồi
    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý..."):
            response = call_plot_api(prompt)
            
            if "error" in response:
                st.error(response["error"])
                st.session_state.messages.append({"role": "assistant", "content": response["error"]})
            else:
                st.image(response["plot_url"], caption=response["message"])
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["message"],
                    "plot_url": response["plot_url"]
                })

# Hiển thị hướng dẫn
with st.expander("Hướng dẫn sử dụng"):
    st.write("""
    Bạn có thể hỏi về biểu đồ chứng khoán bằng cách:
    1. Chỉ định mã chứng khoán trong ngoặc đơn (ví dụ: (MSFT), (AAPL))
    2. Chỉ định khoảng thời gian (ví dụ: from June 1, 2024 to September 30, 2024)
    
    Ví dụ:
    - "Plot the time series of Microsoft (MSFT) stock closing price from June 1, 2024 to September 30, 2024"
    - "Show me the stock price of Apple (AAPL) from January 1, 2024 to March 31, 2024"
    - "Plot Google (GOOGL) stock price from April 1, 2024 to June 30, 2024"
    """)

# Nút quay lại trang chính
if st.button("Quay lại trang chính"):
    st.switch_page("app.py") 