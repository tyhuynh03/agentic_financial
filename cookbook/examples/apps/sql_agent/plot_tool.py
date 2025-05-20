import matplotlib.pyplot as plt
import pandas as pd
from typing import List, Dict
from agno.tools import Toolkit
from agno.utils.log import log_info, logger

class PlotTools:
    def plot_time_series(
        self,
        data: List[Dict],
        x: str = "date",
        y: str = "close",
        title: str = "Time Series Plot",
        xlabel: str = "Date",
        ylabel: str = "Close ($)",
        output_path: str = "output/plot.png"
    ) -> str:
        """
        Vẽ biểu đồ time series từ dữ liệu.
        Args:
            data: List các dict, mỗi dict là 1 dòng dữ liệu (ví dụ: {'date': ..., 'close': ...})
            x: tên cột trục X (ví dụ: 'date')
            y: tên cột trục Y (ví dụ: 'close')
            title, xlabel, ylabel: tiêu đề và nhãn trục
            output_path: đường dẫn lưu file ảnh
        Returns:
            Đường dẫn file ảnh đã lưu
        """
        if not data or x not in data[0] or y not in data[0]:
            raise ValueError("Dữ liệu đầu vào không hợp lệ hoặc thiếu cột cần thiết.")

        df = pd.DataFrame(data)
        plt.figure(figsize=(8, 6))
        plt.plot(df[x], df[y])
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        return output_path

class PlotTool(Toolkit):
    """Tool để vẽ biểu đồ time series từ dữ liệu."""
    
    def __init__(self, **kwargs):
        super().__init__(name="plot_tools", **kwargs)
        self.plot_tools = PlotTools()
        self.register(self.plot_time_series)
        
    def plot_time_series(
        self,
        data: List[Dict],
        x: str = "date",
        y: str = "close",
        title: str = "Time Series Plot",
        xlabel: str = "Date",
        ylabel: str = "Close ($)",
        output_path: str = "output/plot.png"
    ) -> str:
        """
        Vẽ biểu đồ time series từ dữ liệu.
        Args:
            data: List các dict, mỗi dict là 1 dòng dữ liệu (ví dụ: {'date': ..., 'close': ...})
            x: tên cột trục X (ví dụ: 'date')
            y: tên cột trục Y (ví dụ: 'close')
            title, xlabel, ylabel: tiêu đề và nhãn trục
            output_path: đường dẫn lưu file ảnh
        Returns:
            Đường dẫn file ảnh đã lưu
        """
        try:
            log_info(f"Creating time series plot: {title}")
            result = self.plot_tools.plot_time_series(
                data=data,
                x=x,
                y=y,
                title=title,
                xlabel=xlabel,
                ylabel=ylabel,
                output_path=output_path
            )
            log_info(f"Plot saved to: {result}")
            return result
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            return f"Error creating plot: {e}"