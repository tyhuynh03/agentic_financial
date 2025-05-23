from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from datetime import datetime
import os
from pathlib import Path
from typing import Optional
import re

# Khởi tạo FastAPI app
app = FastAPI()

# Cấu hình
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
output_dir = Path(__file__).parent.joinpath("output")
output_dir.mkdir(parents=True, exist_ok=True)

class PlotRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str

class PlotCommand(BaseModel):
    command: str

def parse_plot_command(command: str) -> dict:
    """Phân tích câu lệnh plot để lấy thông tin"""
    # Tìm mã chứng khoán
    ticker_pattern = r'\(([A-Z]+)\)'
    ticker_match = re.search(ticker_pattern, command)
    if not ticker_match:
        raise HTTPException(status_code=400, detail="Không tìm thấy mã chứng khoán")
    ticker = ticker_match.group(1)

    # Xác định loại biểu đồ
    plot_type = "time_series"  # mặc định
    if "histogram" in command.lower():
        plot_type = "histogram"
    elif "boxplot" in command.lower():
        plot_type = "boxplot"

    # Tìm ngày bắt đầu và kết thúc
    date_pattern = r'from\s+(\w+\s+\d+,\s+\d{4})\s+to\s+(\w+\s+\d+,\s+\d{4})'
    date_match = re.search(date_pattern, command)
    if not date_match:
        # Thử tìm năm với nhiều cách diễn đạt khác nhau
        year_patterns = [
            r'during\s+(\d{4})',
            r'for\s+(\d{4})',
            r'for\s+each\s+month\s+of\s+(\d{4})',
            r'in\s+(\d{4})',
            r'of\s+(\d{4})'
        ]
        
        for pattern in year_patterns:
            year_match = re.search(pattern, command)
            if year_match:
                year = year_match.group(1)
                start_date = f"{year}-01-01"
                end_date = f"{year}-12-31"
                return {
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                    "plot_type": plot_type
                }
        
        raise HTTPException(status_code=400, detail="Không tìm thấy khoảng thời gian")
    else:
        # Chuyển đổi định dạng ngày
        start_date = datetime.strptime(date_match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        end_date = datetime.strptime(date_match.group(2), "%B %d, %Y").strftime("%Y-%m-%d")

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "plot_type": plot_type
    }

def get_stock_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Lấy dữ liệu chứng khoán từ database"""
    try:
        conn = psycopg2.connect(db_url.replace("postgresql+psycopg", "postgresql"))
        query = """
            SELECT "Date", "Close"
            FROM ai.prices
            WHERE "Ticker" = %s
            AND "Date" BETWEEN %s AND %s
            ORDER BY "Date"
        """
        df = pd.read_sql(query, conn, params=(ticker, start_date, end_date))
        conn.close()
        
        # Tính daily returns nếu cần
        if not df.empty:
            df['Daily_Return'] = df['Close'].pct_change() * 100
            # Thêm cột tháng cho boxplot
            df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%B')
            
        return df
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def create_plot(df: pd.DataFrame, ticker: str, start_date: str, end_date: str, plot_type: str = "time_series") -> str:
    """Tạo biểu đồ và trả về đường dẫn file"""
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    fig, ax = plt.subplots(figsize=(12, 6))
    
    if plot_type == "histogram":
        # Vẽ histogram của daily returns
        ax.hist(df['Daily_Return'].dropna(), bins=50, color='blue', alpha=0.7)
        ax.set_title(f'Daily Returns Distribution for {ticker} ({start_date} to {end_date})')
        ax.set_xlabel('Daily Return (%)')
        ax.set_ylabel('Frequency')
        ax.grid(True)
    elif plot_type == "boxplot":
        # Vẽ boxplot theo tháng
        df.boxplot(column='Close', by='Month', ax=ax)
        ax.set_title(f'Monthly Closing Price Distribution for {ticker} ({start_date[:4]})')
        ax.set_xlabel('Month')
        ax.set_ylabel('Price (USD)')
        plt.suptitle('')  # Xóa tiêu đề mặc định của boxplot
        ax.grid(True)
    else:
        # Vẽ biểu đồ thời gian
        ax.plot(df['Date'], df['Close'], label=f'{ticker} Closing Price', color='blue')
        ax.set_title(f'{ticker} Stock Closing Price from {start_date} to {end_date}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price (USD)')
        ax.grid(True)
        ax.legend()
    
    # Lưu biểu đồ
    output_file = output_dir / f"{ticker}_{plot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(output_file)
    plt.close()
    
    return str(output_file)

@app.post("/plot")
async def create_stock_plot(request: PlotRequest):
    """API endpoint để tạo biểu đồ chứng khoán"""
    try:
        # Lấy dữ liệu
        df = get_stock_data(
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # Tạo biểu đồ
        plot_path = create_plot(
            df=df,
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # Trả về kết quả
        return {
            "message": f"Plot created for {request.ticker} from {request.start_date} to {request.end_date}",
            "plot_url": f"http://localhost:8000/plots/{os.path.basename(plot_path)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plot/command")
async def process_plot_command(request: PlotCommand):
    """API endpoint để xử lý câu lệnh plot"""
    try:
        # Phân tích câu lệnh
        params = parse_plot_command(request.command)
        
        # Lấy dữ liệu
        df = get_stock_data(
            ticker=params["ticker"],
            start_date=params["start_date"],
            end_date=params["end_date"]
        )
        
        # Tạo biểu đồ
        plot_path = create_plot(
            df=df,
            ticker=params["ticker"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            plot_type=params["plot_type"]
        )
        
        # Trả về kết quả
        return {
            "message": f"Plot created for {params['ticker']} from {params['start_date']} to {params['end_date']}",
            "plot_url": f"http://localhost:8000/plots/{os.path.basename(plot_path)}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plots/{filename}")
async def get_plot(filename: str):
    """API endpoint để lấy file biểu đồ"""
    file_path = output_dir / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Plot not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 