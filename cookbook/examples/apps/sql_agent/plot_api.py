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
import numpy as np
from sqlalchemy import create_engine

# Khởi tạo FastAPI app
app = FastAPI()

# Cấu hình
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
engine = create_engine(db_url)
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
    # Tìm mã chứng khoán hoặc nhóm chứng khoán
    ticker_pattern = r'\(([A-Z]+)\)'
    ticker_match = re.search(ticker_pattern, command)
    
    # Xác định loại biểu đồ
    plot_type = "time_series"  # mặc định
    if "histogram" in command.lower():
        plot_type = "histogram"
    elif "boxplot" in command.lower():
        plot_type = "boxplot"
    elif "scatter" in command.lower():
        plot_type = "scatter"
    elif "bar" in command.lower() or "bar chart" in command.lower():
        plot_type = "bar"
    elif "pie" in command.lower() or "pie chart" in command.lower():
        plot_type = "pie"
        
    # Xác định loại dữ liệu cho scatter plot
    data_type = None
    if "market capitalization" in command.lower() and "p/e ratio" in command.lower():
        data_type = "market_cap_pe"
    elif "market capitalization" in command.lower() and "top" in command.lower():
        data_type = "top_market_cap"
    elif "distribution" in command.lower() and "sector" in command.lower():
        data_type = "sector_distribution"
        
    # Tìm ngày
    date_pattern = r'as of (\w+ \d+,\s+\d{4})'
    date_match = re.search(date_pattern, command)
    if date_match:
        date = datetime.strptime(date_match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        # Nếu không có mã cụ thể, mặc định là DJIA
        ticker = ticker_match.group(1) if ticker_match else "DJIA"
        return {
            "ticker": ticker,
            "date": date,
            "plot_type": plot_type,
            "data_type": data_type
        }
        
    # Tìm khoảng thời gian
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
                # Nếu không có mã cụ thể, mặc định là DJIA
                ticker = ticker_match.group(1) if ticker_match else "DJIA"
                return {
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                    "plot_type": plot_type,
                    "data_type": data_type
                }
        
        # Nếu không tìm thấy ngày cụ thể, lấy ngày gần nhất có dữ liệu
        try:
            query = """
                SELECT "Date" 
                FROM ai.prices 
                ORDER BY "Date" DESC 
                LIMIT 1
            """
            latest_date = pd.read_sql(query, engine)
            if not latest_date.empty:
                date = latest_date['Date'].iloc[0].strftime('%Y-%m-%d')
                # Nếu không có mã cụ thể, mặc định là DJIA
                ticker = ticker_match.group(1) if ticker_match else "DJIA"
                return {
                    "ticker": ticker,
                    "date": date,
                    "plot_type": plot_type,
                    "data_type": data_type
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
            
        raise HTTPException(status_code=400, detail="Không tìm thấy khoảng thời gian")
    else:
        # Chuyển đổi định dạng ngày
        start_date = datetime.strptime(date_match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
        end_date = datetime.strptime(date_match.group(2), "%B %d, %Y").strftime("%Y-%m-%d")
        # Nếu không có mã cụ thể, mặc định là DJIA
        ticker = ticker_match.group(1) if ticker_match else "DJIA"

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "plot_type": plot_type,
        "data_type": data_type
    }

def get_stock_data(ticker: str, start_date: str = None, end_date: str = None, date: str = None, plot_type: str = None, data_type: str = None) -> pd.DataFrame:
    """Lấy dữ liệu chứng khoán từ database"""
    try:
        # Nếu là biểu đồ top market cap hoặc scatter plot
        if plot_type in ["bar", "scatter"] and data_type in ["top_market_cap", "market_cap_pe"]:
            # Kiểm tra và lấy ngày gần nhất có dữ liệu
            if date:
                check_query = """
                    SELECT "Date" 
                    FROM ai.prices 
                    WHERE "Date" <= %s
                    ORDER BY "Date" DESC 
                    LIMIT 1
                """
                available_date = pd.read_sql(check_query, engine, params=(date,))
                if not available_date.empty:
                    date = available_date['Date'].iloc[0].strftime('%Y-%m-%d')
            
            # Lấy dữ liệu cho tất cả công ty trong DJIA
            query = """
                SELECT "Ticker", "Date", "Close", "Volume"
                FROM ai.prices
                WHERE "Date" = %s
            """
            df = pd.read_sql(query, engine, params=(date,))
            
            if df.empty:
                # Kiểm tra xem có dữ liệu cho ngày nào không
                check_query = """
                    SELECT DISTINCT "Date" 
                    FROM ai.prices 
                    ORDER BY "Date" DESC 
                    LIMIT 5
                """
                available_dates = pd.read_sql(check_query, engine)
                if not available_dates.empty:
                    dates_str = ", ".join(available_dates['Date'].dt.strftime('%Y-%m-%d').tolist())
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Không tìm thấy dữ liệu cho ngày {date}. Các ngày có sẵn: {dates_str}"
                    )
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="Không tìm thấy dữ liệu nào trong database"
                    )
            
            # Tính toán Market Cap từ Volume và Close price
            df['Market_Cap'] = df['Volume'] * df['Close']  # Ước tính đơn giản
            # Tính P/E ratio (giả định)
            df['PE_Ratio'] = df['Close'] / 10  # Giá trị giả định
        # Nếu là biểu đồ tròn phân bố ngành
        elif plot_type == "pie" and data_type == "sector_distribution":
            # Kiểm tra và lấy ngày gần nhất có dữ liệu
            if date:
                check_query = """
                    SELECT "Date" 
                    FROM ai.prices 
                    WHERE "Date" <= %s
                    ORDER BY "Date" DESC 
                    LIMIT 1
                """
                available_date = pd.read_sql(check_query, engine, params=(date,))
                if not available_date.empty:
                    date = available_date['Date'].iloc[0].strftime('%Y-%m-%d')
            
            # Lấy dữ liệu cho tất cả công ty trong DJIA
            query = """
                SELECT p."Ticker", p."Date", c.sector
                FROM ai.prices p
                JOIN ai.companies c ON p."Ticker" = c.symbol
                WHERE p."Date" = %s
            """
            df = pd.read_sql(query, engine, params=(date,))
            
            if df.empty:
                # Kiểm tra xem có dữ liệu cho ngày nào không
                check_query = """
                    SELECT DISTINCT "Date" 
                    FROM ai.prices 
                    ORDER BY "Date" DESC 
                    LIMIT 5
                """
                available_dates = pd.read_sql(check_query, engine)
                if not available_dates.empty:
                    dates_str = ", ".join(available_dates['Date'].dt.strftime('%Y-%m-%d').tolist())
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Không tìm thấy dữ liệu cho ngày {date}. Các ngày có sẵn: {dates_str}"
                    )
                else:
                    raise HTTPException(
                        status_code=404,
                        detail="Không tìm thấy dữ liệu nào trong database"
                    )
        else:
            # Lấy dữ liệu cho một mã cụ thể
            query = """
                SELECT "Date", "Close"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            
            if not df.empty:
                df['Daily_Return'] = df['Close'].pct_change() * 100
                df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%B')
            
        return df
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def create_plot(df: pd.DataFrame, ticker: str, start_date: str = None, end_date: str = None, 
                plot_type: str = "time_series", data_type: str = None) -> str:
    """Tạo biểu đồ và trả về đường dẫn file"""
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    fig, ax = plt.subplots(figsize=(12, 6))
    
    if plot_type == "pie" and data_type == "sector_distribution":
        # Tính toán số lượng công ty theo ngành
        sector_counts = df['sector'].value_counts()
        
        # Vẽ biểu đồ tròn
        wedges, texts, autotexts = ax.pie(
            sector_counts.values,
            labels=sector_counts.index,
            autopct='%1.1f%%',
            textprops={'fontsize': 8},
            colors=plt.cm.Pastel1(np.linspace(0, 1, len(sector_counts)))
        )
        
        # Thêm tiêu đề
        ax.set_title(f'Distribution of DJIA Companies by Sector - {df["Date"].iloc[0].strftime("%Y-%m-%d")}')
        
        # Thêm chú thích
        plt.legend(
            wedges,
            [f'{sector} ({count} companies)' for sector, count in sector_counts.items()],
            title="Sectors",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1)
        )
        
        # Điều chỉnh layout để tránh cắt chú thích
        plt.tight_layout()
    elif plot_type == "bar" and data_type == "top_market_cap":
        # Sắp xếp và lấy top 10
        df = df.sort_values('Market_Cap', ascending=False).head(10)
        
        # Vẽ biểu đồ cột
        bars = ax.bar(df['Ticker'], df['Market_Cap'], color='skyblue')
        
        # Thêm giá trị trên mỗi cột
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'${height:,.0f}',
                   ha='center', va='bottom')
        
        ax.set_title(f'Top 10 Companies by Market Capitalization - {df["Date"].iloc[0].strftime("%Y-%m-%d")}')
        ax.set_xlabel('Company')
        ax.set_ylabel('Market Capitalization (USD)')
        plt.xticks(rotation=45, ha='right')
        ax.grid(True, axis='y')
        
        # Thêm chú thích về dữ liệu ước tính
        plt.figtext(0.02, 0.02, 
                   "Note: Market Cap is estimated from Volume * Close Price",
                   fontsize=8, style='italic')
        
    elif plot_type == "scatter" and data_type == "market_cap_pe":
        # Vẽ scatter plot
        scatter = ax.scatter(df['Market_Cap'], df['PE_Ratio'], alpha=0.6)
        
        # Thêm nhãn cho các điểm
        for i, txt in enumerate(df['Ticker']):
            ax.annotate(txt, (df['Market_Cap'].iloc[i], df['PE_Ratio'].iloc[i]))
            
        ax.set_title(f'Market Cap vs P/E Ratio for DJIA Companies (Estimated) - {df["Date"].iloc[0].strftime("%Y-%m-%d")}')
        ax.set_xlabel('Market Capitalization (USD) - Estimated from Volume')
        ax.set_ylabel('P/E Ratio - Estimated')
        ax.grid(True)
        
        # Thêm đường hồi quy
        z = np.polyfit(df['Market_Cap'], df['PE_Ratio'], 1)
        p = np.poly1d(z)
        ax.plot(df['Market_Cap'], p(df['Market_Cap']), "r--", alpha=0.8)
        
        # Thêm chú thích về dữ liệu ước tính
        plt.figtext(0.02, 0.02, 
                   "Note: Market Cap and P/E Ratio are estimated values for demonstration purposes",
                   fontsize=8, style='italic')
        
    elif plot_type == "histogram":
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
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            date=params.get("date"),
            plot_type=params["plot_type"],
            data_type=params.get("data_type")
        )
        
        # Tạo biểu đồ
        plot_path = create_plot(
            df=df,
            ticker=params["ticker"],
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            plot_type=params["plot_type"],
            data_type=params.get("data_type")
        )
        
        # Trả về kết quả
        return {
            "message": f"Plot created for {params['ticker']}",
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