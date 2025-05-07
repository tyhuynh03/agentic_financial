import pandas as pd
import os
from agents import db_url
from agno.utils.log import logger
from sqlalchemy import create_engine

def load_data():
    """Load DJIA data into the database"""
    
    logger.info("Loading database.")
    engine = create_engine(db_url)
    
    # Đường dẫn đến thư mục data
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    
    # Dictionary mapping file paths to table names
    files_to_tables = {
        os.path.join(data_dir, 'djia_companies_20250426.csv'): 'companies',
        os.path.join(data_dir, 'djia_prices_20250426.csv'): 'prices'
    }
    
    # Load each CSV file into the corresponding PostgreSQL table
    for file_path, table_name in files_to_tables.items():
        logger.info(f"Loading {file_path} into {table_name} table.")
        
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Convert Date column to datetime for prices table
        if table_name == 'prices':
            df['Date'] = pd.to_datetime(df['Date'])
        
        # Load data into database
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        logger.info(f"{file_path} loaded into {table_name} table.")
    
    logger.info("Database loaded.")

if __name__ == "__main__":
    load_data() 