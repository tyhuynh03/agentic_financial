from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from datetime import datetime, timedelta
import os
from pathlib import Path
from typing import Optional
import re
import numpy as np
from sqlalchemy import create_engine
import seaborn as sns

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
    elif "heatmap" in command.lower():
        plot_type = "heatmap"
    elif "volume" in command.lower() or "trading volume" in command.lower():
        plot_type = "volume"
    
    # Xác định loại dữ liệu cho bar chart trung bình tháng
    data_type = None
    rolling_window = None
    if "average monthly closing price" in command.lower():
        data_type = "monthly_avg_close"
    elif "market capitalization" in command.lower() and "p/e ratio" in command.lower():
        data_type = "market_cap_pe"
    elif "market capitalization" in command.lower() and "top" in command.lower():
        data_type = "top_market_cap"
    elif "distribution" in command.lower() and "sector" in command.lower():
        data_type = "sector_distribution"
    elif "correlation" in command.lower() and "daily returns" in command.lower():
        data_type = "correlation_matrix"
    elif "daily trading volume" in command.lower():
        data_type = "daily_volume"
    elif "rolling average" in command.lower() or "moving average" in command.lower():
        data_type = "rolling_avg"
        # Tìm số ngày cho rolling average
        rolling_pattern = r'(\d+)-day'
        rolling_match = re.search(rolling_pattern, command)
        rolling_window = int(rolling_match.group(1)) if rolling_match else 30  # Mặc định là 30 ngày
    elif "market capitalization" in command.lower() and "technology" in command.lower():
        data_type = "sector_market_cap"
        # Tìm sector
        sector_pattern = r'in the (\w+) sector'
        sector_match = re.search(sector_pattern, command.lower())
        sector = sector_match.group(1).capitalize() if sector_match else "Technology"
    elif "average daily volume" in command.lower() and "average closing price" in command.lower():
        data_type = "volume_price_scatter"
    elif "cumulative return" in command.lower():
        data_type = "cumulative_return"
    elif "high" in command.lower() and "low" in command.lower() and "range" in command.lower():
        data_type = "high_low_range"
    elif "daily returns" in command.lower():
        data_type = "daily_returns_boxplot"
    elif "dividends" in command.lower() and "per share" in command.lower():
        data_type = "dividends_per_share"
    elif ("market capitalization" in command.lower() and "proportion" in command.lower() and "sector" in command.lower()) or ("market capitalization" in command.lower() and "by sector" in command.lower() and ("pie" in command.lower() or "pie chart" in command.lower())):
        data_type = "sector_market_cap_pie"
    
    # Tìm danh sách mã chứng khoán cho heatmap
    tickers = []
    if plot_type == "heatmap":
        # Tìm phần sau "for" trong câu lệnh
        for_pattern = r'for\s+([A-Z]+(?:,\s*[A-Z]+)*)'
        for_match = re.search(for_pattern, command)
        if for_match:
            tickers = [t.strip() for t in for_match.group(1).split(',')]
            # Loại bỏ các từ khóa không phải mã chứng khoán
            tickers = [t for t in tickers if t not in ['PLOT', 'HEATMAP', 'CORRELATION', 'MATRIX']]
    
    # Tìm tháng và năm
    month_year_pattern = r'for\s+(\w+)\s+(\d{4})'
    month_year_match = re.search(month_year_pattern, command)
    if month_year_match:
        month = month_year_match.group(1)
        year = month_year_match.group(2)
        try:
            # Chuyển đổi tên tháng thành số
            month_num = datetime.strptime(month, "%B").month
            # Tạo ngày đầu và cuối tháng
            start_date = f"{year}-{month_num:02d}-01"
            # Tính ngày cuối tháng
            if month_num == 12:
                end_date = f"{year}-12-31"
            else:
                end_date = f"{year}-{month_num+1:02d}-01"
                end_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Nếu không có mã cụ thể, mặc định là DJIA
            ticker = ticker_match.group(1) if ticker_match else "DJIA"
            return {
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date,
                "plot_type": plot_type,
                "data_type": data_type,
                "tickers": tickers,
                "rolling_window": rolling_window
            }
        except ValueError:
            pass
    
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
            "data_type": data_type,
            "tickers": tickers,
            "rolling_window": rolling_window
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
                    "data_type": data_type,
                    "tickers": tickers,
                    "rolling_window": rolling_window
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
                    "data_type": data_type,
                    "tickers": tickers,
                    "rolling_window": rolling_window
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
        "data_type": data_type,
        "tickers": tickers,
        "rolling_window": rolling_window
    }

def get_stock_data(ticker: str, start_date: str = None, end_date: str = None, date: str = None, 
                  plot_type: str = None, data_type: str = None, tickers: list = None,
                  rolling_window: int = None) -> pd.DataFrame:
    """Lấy dữ liệu chứng khoán từ database"""
    try:
        # Nếu là bar chart dividends per share
        if plot_type == "bar" and data_type == "dividends_per_share":
            # Lấy dữ liệu cổ tức cho tất cả công ty trong DJIA
            query = """
                SELECT p."Ticker", 
                       SUM(p."Dividends") as total_dividends,
                       c.sector
                FROM ai.prices p
                JOIN ai.companies c ON p."Ticker" = c.symbol
                WHERE p."Date" BETWEEN %s AND %s
                GROUP BY p."Ticker", c.sector
                ORDER BY total_dividends DESC
            """
            df = pd.read_sql(query, engine, params=(start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cổ tức trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            return df
            
        # Nếu là boxplot daily returns
        if plot_type == "boxplot" and data_type == "daily_returns_boxplot":
            query = """
                SELECT "Date", "Close"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cho {ticker} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            # Tính daily returns
            df['Daily_Return'] = df['Close'].pct_change() * 100  # Chuyển sang phần trăm
            
            # Thêm cột tháng để phân nhóm
            df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%B')
            
            return df
            
        # Nếu là histogram high-low range
        if plot_type == "histogram" and data_type == "high_low_range":
            query = """
                SELECT "Date", "High", "Low"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cho {ticker} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            # Tính high-low range
            df['High_Low_Range'] = df['High'] - df['Low']
            
            # Tính phần trăm range so với giá thấp nhất
            df['Range_Percent'] = (df['High_Low_Range'] / df['Low']) * 100
            
            return df
            
        # Nếu là biểu đồ cumulative return
        if plot_type == "time_series" and data_type == "cumulative_return":
            query = """
                SELECT "Date", "Close"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cho {ticker} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            # Tính daily returns
            df['Daily_Return'] = df['Close'].pct_change()
            
            # Tính cumulative returns
            df['Cumulative_Return'] = (1 + df['Daily_Return']).cumprod() - 1
            
            # Chuyển đổi sang phần trăm
            df['Cumulative_Return'] = df['Cumulative_Return'] * 100
            
            return df
            
        # Nếu là scatter plot volume vs price
        if plot_type == "scatter" and data_type == "volume_price_scatter":
            # Lấy dữ liệu cho tất cả công ty trong DJIA
            query = """
                SELECT p."Ticker", 
                       AVG(p."Volume") as avg_volume,
                       AVG(p."Close") as avg_price,
                       c.sector
                FROM ai.prices p
                JOIN ai.companies c ON p."Ticker" = c.symbol
                WHERE p."Date" BETWEEN %s AND %s
                GROUP BY p."Ticker", c.sector
                ORDER BY avg_volume DESC
            """
            df = pd.read_sql(query, engine, params=(start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            return df
            
        # Nếu là histogram market cap theo sector
        if plot_type == "histogram" and data_type == "sector_market_cap":
            # Lấy ngày gần nhất có dữ liệu
            query = """
                SELECT "Date" 
                FROM ai.prices 
                ORDER BY "Date" DESC 
                LIMIT 1
            """
            latest_date = pd.read_sql(query, engine)
            if not latest_date.empty:
                date = latest_date['Date'].iloc[0].strftime('%Y-%m-%d')
            
            # Lấy dữ liệu market cap cho các công ty trong sector
            query = """
                SELECT p."Ticker", p."Date", p."Close", p."Volume", c.sector
                FROM ai.prices p
                JOIN ai.companies c ON p."Ticker" = c.symbol
                WHERE p."Date" = %s
                AND c.sector = %s
            """
            df = pd.read_sql(query, engine, params=(date, "Technology"))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cho sector Technology vào ngày {date}"
                )
            
            # Tính market cap
            df['Market_Cap'] = df['Volume'] * df['Close']  # Ước tính đơn giản
            return df
            
        # Nếu là biểu đồ rolling average
        if plot_type == "time_series" and data_type == "rolling_avg":
            query = """
                SELECT "Date", "Close"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cho {ticker} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            # Tính rolling average
            df['Rolling_Avg'] = df['Close'].rolling(window=rolling_window).mean()
            return df
            
        # Nếu là bar chart trung bình giá đóng cửa theo tháng
        if plot_type == "bar" and data_type == "monthly_avg_close":
            query = """
                SELECT "Date", "Close"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu giá đóng cửa cho {ticker} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            df['Month'] = pd.to_datetime(df['Date']).dt.strftime('%b')
            monthly_avg = df.groupby('Month')['Close'].mean().reindex([
                'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])
            return monthly_avg.reset_index(name='AvgClose')
        
        # Nếu là biểu đồ khối lượng giao dịch
        if plot_type == "volume" and data_type == "daily_volume":
            query = """
                SELECT "Date", "Volume"
                FROM ai.prices
                WHERE "Ticker" = %s
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date"
            """
            df = pd.read_sql(query, engine, params=(ticker, start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu khối lượng giao dịch cho {ticker} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            return df
            
        # Nếu là biểu đồ heatmap
        if plot_type == "heatmap" and data_type == "correlation_matrix" and tickers:
            # Kiểm tra xem có dữ liệu cho các mã được chỉ định không
            check_query = """
                SELECT DISTINCT "Ticker"
                FROM ai.prices
                WHERE "Ticker" = ANY(%s)
                AND "Date" BETWEEN %s AND %s
            """
            available_tickers = pd.read_sql(check_query, engine, params=(tickers, start_date, end_date))
            
            if available_tickers.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu cho các mã: {', '.join(tickers)} trong khoảng thời gian từ {start_date} đến {end_date}"
                )
            
            # Lấy dữ liệu cho các mã có sẵn
            query = """
                SELECT "Ticker", "Date", "Close"
                FROM ai.prices
                WHERE "Ticker" = ANY(%s)
                AND "Date" BETWEEN %s AND %s
                ORDER BY "Date", "Ticker"
            """
            df = pd.read_sql(query, engine, params=(available_tickers['Ticker'].tolist(), start_date, end_date))
            
            if df.empty:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Không tìm thấy dữ liệu giá cho các mã: {', '.join(tickers)}"
                )
            
            # Tính toán daily returns
            df = df.pivot(index='Date', columns='Ticker', values='Close')
            # Tính daily returns và điền giá trị 0 cho ngày đầu tiên
            returns = df.pct_change() * 100
            returns = returns.fillna(0)  # Điền 0 cho ngày đầu tiên
            
            # Kiểm tra xem có đủ dữ liệu không
            if returns.isnull().sum().sum() > 0:
                missing_data = returns.isnull().sum()
                missing_tickers = missing_data[missing_data > 0].index.tolist()
                raise HTTPException(
                    status_code=404,
                    detail=f"Thiếu dữ liệu daily returns cho các mã: {', '.join(missing_tickers)}"
                )
            
            return returns
            
        # Nếu là biểu đồ top market cap hoặc scatter plot
        elif plot_type in ["bar", "scatter"] and data_type in ["top_market_cap", "market_cap_pe"]:
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
        # Pie chart market cap proportions by sector
        elif plot_type == "pie" and data_type == "sector_market_cap_pie":
            # Lấy ngày gần nhất có dữ liệu nếu ngày truyền vào không có
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
            else:
                # Nếu không truyền ngày, lấy ngày mới nhất
                query = "SELECT MAX(\"Date\") as max_date FROM ai.prices"
                date_df = pd.read_sql(query, engine)
                date = date_df['max_date'].iloc[0].strftime('%Y-%m-%d')
            # Lấy market cap từng công ty tại ngày đó
            query = """
                SELECT p."Ticker", c.sector, p."Close", p."Volume"
                FROM ai.prices p
                JOIN ai.companies c ON p."Ticker" = c.symbol
                WHERE p."Date" = %s
            """
            df = pd.read_sql(query, engine, params=(date,))
            if df.empty:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu market cap cho ngày {date}")
            # Tính market cap từng công ty
            df['Market_Cap'] = df['Close'] * df['Volume']
            # Tổng market cap theo sector
            sector_df = df.groupby('sector')['Market_Cap'].sum().reset_index()
            sector_df['Date'] = date
            return sector_df
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
                plot_type: str = "time_series", data_type: str = None, tickers: list = None,
                rolling_window: int = None) -> str:
    """Tạo biểu đồ và trả về đường dẫn file"""
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")

    fig, ax = plt.subplots(figsize=(12, 8))
    
    if plot_type == "bar" and data_type == "dividends_per_share":
        # Tạo màu sắc theo sector
        sectors = df['sector'].unique()
        colors = plt.cm.Set3(np.linspace(0, 1, len(sectors)))
        sector_colors = dict(zip(sectors, colors))
        
        # Vẽ bar chart
        bars = ax.bar(df['Ticker'], df['total_dividends'], 
                     color=[sector_colors[sector] for sector in df['sector']],
                     alpha=0.7)
        
        # Thêm giá trị trên mỗi cột
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'${height:.2f}',
                   ha='center', va='bottom', fontsize=8)
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'Total Dividends per Share by DJIA Companies\n{start_date} to {end_date}')
        ax.set_xlabel('Company')
        ax.set_ylabel('Total Dividends per Share (USD)')
        
        # Xoay nhãn công ty
        plt.xticks(rotation=45, ha='right')
        
        # Thêm lưới
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Thêm chú thích cho các sector
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=sector_colors[sector], label=sector)
                         for sector in sectors]
        ax.legend(handles=legend_elements, title='Sectors',
                 bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Thêm thống kê
        mean_div = df['total_dividends'].mean()
        median_div = df['total_dividends'].median()
        max_div = df['total_dividends'].max()
        
        stats_text = f'Mean: ${mean_div:.2f}\nMedian: ${median_div:.2f}\nMax: ${max_div:.2f}'
        ax.text(0.95, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
    elif plot_type == "boxplot" and data_type == "daily_returns_boxplot":
        # Vẽ boxplot theo tháng
        df.boxplot(column='Daily_Return', by='Month', ax=ax)
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'Distribution of Daily Returns for {ticker}\n{start_date} to {end_date}')
        ax.set_xlabel('Month')
        ax.set_ylabel('Daily Return (%)')
        
        # Xóa tiêu đề mặc định của boxplot
        plt.suptitle('')
        
        # Thêm lưới
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Thêm thống kê tổng quan
        mean_return = df['Daily_Return'].mean()
        median_return = df['Daily_Return'].median()
        std_return = df['Daily_Return'].std()
        
        stats_text = f'Mean: {mean_return:.2f}%\nMedian: {median_return:.2f}%\nStd Dev: {std_return:.2f}%'
        ax.text(0.95, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        # Xoay nhãn tháng
        plt.xticks(rotation=45)
        
        plt.tight_layout()
    elif plot_type == "histogram" and data_type == "high_low_range":
        # Vẽ histogram của high-low range
        ax.hist(df['Range_Percent'], bins=30, color='purple', edgecolor='black', alpha=0.7)
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'Distribution of Daily High-Low Range for {ticker}\n{start_date} to {end_date}')
        ax.set_xlabel('Daily Range (% of Low Price)')
        ax.set_ylabel('Frequency')
        
        # Thêm lưới
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Thêm thống kê
        mean_range = df['Range_Percent'].mean()
        median_range = df['Range_Percent'].median()
        max_range = df['Range_Percent'].max()
        
        stats_text = f'Mean: {mean_range:.1f}%\nMedian: {median_range:.1f}%\nMax: {max_range:.1f}%'
        ax.text(0.95, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
    elif plot_type == "time_series" and data_type == "cumulative_return":
        # Vẽ biểu đồ cumulative return
        ax.plot(df['Date'], df['Cumulative_Return'], color='green', linewidth=2)
        
        # Thêm đường zero
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'{ticker} Cumulative Return\n{start_date} to {end_date}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Return (%)')
        
        # Thêm lưới
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Định dạng trục y để hiển thị phần trăm
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1f}%'.format(y)))
        
        # Xoay nhãn ngày
        plt.xticks(rotation=45)
        
        # Thêm giá trị cuối cùng
        final_return = df['Cumulative_Return'].iloc[-1]
        ax.annotate(f'Final Return: {final_return:.1f}%',
                   xy=(df['Date'].iloc[-1], final_return),
                   xytext=(10, 10),
                   textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5))
        
        plt.tight_layout()
    elif plot_type == "scatter" and data_type == "volume_price_scatter":
        # Tạo scatter plot với màu sắc theo sector
        sectors = df['sector'].unique()
        colors = plt.cm.Set3(np.linspace(0, 1, len(sectors)))
        sector_colors = dict(zip(sectors, colors))
        
        # Vẽ scatter plot cho từng sector
        for sector in sectors:
            sector_data = df[df['sector'] == sector]
            ax.scatter(sector_data['avg_volume'], 
                      sector_data['avg_price'],
                      label=sector,
                      color=sector_colors[sector],
                      alpha=0.7,
                      s=100)
            
            # Thêm nhãn cho các điểm
            for _, row in sector_data.iterrows():
                ax.annotate(row['Ticker'], 
                          (row['avg_volume'], row['avg_price']),
                          xytext=(5, 5),
                          textcoords='offset points',
                          fontsize=8)
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'Average Daily Volume vs Average Closing Price\n{start_date} to {end_date}')
        ax.set_xlabel('Average Daily Volume')
        ax.set_ylabel('Average Closing Price (USD)')
        
        # Thêm lưới
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Thêm chú thích
        ax.legend(title='Sectors', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Điều chỉnh layout để tránh cắt chú thích
        plt.tight_layout()
    elif plot_type == "histogram" and data_type == "sector_market_cap":
        # Vẽ histogram market cap
        ax.hist(df['Market_Cap'], bins=20, color='skyblue', edgecolor='black')
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'Distribution of Market Capitalizations in Technology Sector\n{df["Date"].iloc[0].strftime("%Y-%m-%d")}')
        ax.set_xlabel('Market Capitalization (USD)')
        ax.set_ylabel('Number of Companies')
        
        # Thêm lưới
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Thêm chú thích về dữ liệu ước tính
        plt.figtext(0.02, 0.02, 
                   "Note: Market Cap is estimated from Volume * Close Price",
                   fontsize=8, style='italic')
        
        plt.tight_layout()
    elif plot_type == "time_series" and data_type == "rolling_avg":
        # Vẽ biểu đồ giá đóng cửa và rolling average
        ax.plot(df['Date'], df['Close'], label=f'{ticker} Closing Price', color='blue', alpha=0.7)
        ax.plot(df['Date'], df['Rolling_Avg'], label=f'{rolling_window}-day Moving Average', 
                color='red', linewidth=2)
        
        ax.set_title(f'{ticker} Stock Price and {rolling_window}-day Moving Average\n{start_date} to {end_date}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Price (USD)')
        ax.grid(True)
        ax.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
    elif plot_type == "heatmap" and data_type == "correlation_matrix":
        # Tính toán ma trận tương quan
        corr_matrix = df.corr()
        
        # Vẽ heatmap
        sns.heatmap(corr_matrix, 
                   annot=True,  # Hiển thị giá trị
                   cmap='coolwarm',  # Màu sắc
                   center=0,  # Giá trị trung tâm
                   fmt='.2f',  # Định dạng số
                   square=True,  # Hình vuông
                   ax=ax)
        
        # Thêm tiêu đề
        ax.set_title(f'Correlation Matrix of Daily Returns\n{start_date} to {end_date}')
        
        # Điều chỉnh layout
        plt.tight_layout()
    elif plot_type == "pie" and data_type == "sector_distribution":
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
    elif plot_type == "volume" and data_type == "daily_volume":
        # Vẽ line chart cho khối lượng giao dịch
        ax.plot(df['Date'], df['Volume'], marker='o', linestyle='-', color='tab:blue')
        
        # Thêm tiêu đề và nhãn
        ax.set_title(f'{ticker} Trading Volume (Mar 2025)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Volume')
        
        # Xoay nhãn ngày để dễ đọc
        plt.xticks(rotation=45, ha='right')
        
        # Thêm lưới
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # Điều chỉnh layout
        plt.tight_layout()
    elif plot_type == "bar" and data_type == "monthly_avg_close":
        # Vẽ bar chart trung bình giá đóng cửa theo tháng
        bars = ax.bar(df['Month'], df['AvgClose'], color='orange', alpha=0.8)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}',
                   ha='center', va='bottom', fontsize=9)
        ax.set_title(f'{ticker} Average Monthly Closing Price in 2024')
        ax.set_xlabel('Month')
        ax.set_ylabel('Average Closing Price (USD)')
        plt.tight_layout()
    elif plot_type == "pie" and data_type == "sector_market_cap_pie":
        # Vẽ pie chart tỷ trọng vốn hóa theo sector
        wedges, texts, autotexts = ax.pie(
            df['Market_Cap'],
            labels=df['sector'],
            autopct='%1.1f%%',
            textprops={'fontsize': 8},
            colors=plt.cm.Pastel2(np.linspace(0, 1, len(df)))
        )
        ax.set_title(f'Market Capitalization Proportions by Sector\n{df["Date"].iloc[0]}')
        # Thêm chú thích
        plt.legend(
            wedges,
            [f'{sector}: ${cap/1e9:.1f}B' for sector, cap in zip(df['sector'], df['Market_Cap'])],
            title="Sectors (Total Market Cap)",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1)
        )
        plt.tight_layout()
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
            data_type=params.get("data_type"),
            tickers=params.get("tickers"),
            rolling_window=params.get("rolling_window")
        )
        
        # Tạo biểu đồ
        plot_path = create_plot(
            df=df,
            ticker=params["ticker"],
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            plot_type=params["plot_type"],
            data_type=params.get("data_type"),
            tickers=params.get("tickers"),
            rolling_window=params.get("rolling_window")
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