"""Tool để format kết quả SQL cho plot_tool."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from agno.tools import Toolkit
from agno.utils.log import log_info, logger

class FormatSQLTool(Toolkit):
    """Tool để format kết quả SQL cho plot_tool."""
    
    def __init__(self, **kwargs):
        super().__init__(name="format_sql_tool", **kwargs)
        self.register(self.format_for_plot)
        # self.register(self.format_for_plot_from_json)
        self.register(self.validate_plot_data)

    def format_for_plot(
        self,
        sql_result: List[Dict[str, Any]],
        date_column: str = "Date",
        value_column: str = "Close"
    ) -> str:
        """Format kết quả SQL thành định dạng phù hợp cho plot_tool.
        
        Args:
            sql_result: Kết quả từ câu query SQL
            date_column: Tên cột chứa ngày tháng
            value_column: Tên cột chứa giá trị cần vẽ
            
        Returns:
            str: JSON string chứa danh sách các dictionary với key 'date' và 'close'
        """
        try:
            formatted_data = []
            
            for row in sql_result:
                # Chuyển đổi ngày tháng thành string
                date = row[date_column]
                if isinstance(date, datetime):
                    date = date.strftime("%Y-%m-%d %H:%M:%S")
                
                # Chuyển đổi giá trị thành float
                value = float(row[value_column])
                
                formatted_data.append({
                    "date": date,
                    "close": value
                })
            
            log_info(f"Formatted {len(formatted_data)} rows of data")
            return json.dumps(formatted_data)
        except Exception as e:
            logger.error(f"Error formatting data: {e}")
            return "[]"

    # def format_for_plot_from_json(
    #     self,
    #     json_result: str,
    #     date_column: str = "Date",
    #     value_column: str = "Close"
    # ) -> str:
    #     """Format kết quả JSON từ SQL thành định dạng phù hợp cho plot_tool.
        
    #     Args:
    #         json_result: Kết quả JSON từ câu query SQL
    #         date_column: Tên cột chứa ngày tháng
    #         value_column: Tên cột chứa giá trị cần vẽ
            
    #     Returns:
    #         str: JSON string chứa danh sách các dictionary với key 'date' và 'close'
    #     """
    #     try:
    #         # Parse JSON string thành list
    #         data = json.loads(json_result)
    #         if isinstance(data, list):
    #             return self.format_for_plot(data, date_column, value_column)
    #         return "[]"
    #     except json.JSONDecodeError as e:
    #         logger.error(f"Error parsing JSON: {e}")
    #         return "[]"

    def validate_plot_data(self, data: str) -> bool:
        """Kiểm tra xem dữ liệu có đúng định dạng cho plot_tool không.
        
        Args:
            data: JSON string chứa dữ liệu cần kiểm tra
            
        Returns:
            bool: True nếu dữ liệu hợp lệ, False nếu không
        """
        try:
            data_list = json.loads(data)
            if not isinstance(data_list, list):
                return False
                
            for item in data_list:
                if not isinstance(item, dict):
                    return False
                if "date" not in item or "close" not in item:
                    return False
                if not isinstance(item["close"], (int, float)):
                    return False
                    
            log_info("Data validation successful")
            return True
        except Exception as e:
            logger.error(f"Error validating data: {e}")
            return False 