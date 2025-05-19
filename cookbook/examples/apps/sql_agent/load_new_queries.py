from agents import agent_knowledge
from agno.utils.log import logger
import os
from dotenv import load_dotenv

def load_sql_queries(file_path: str) -> list:
    """Load SQL queries from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Split content into individual queries
            queries = content.split('-- </query>')
            return [q.strip() for q in queries if q.strip()]
    except Exception as e:
        logger.error(f"Error loading SQL file {file_path}: {str(e)}")
        return []

def load_new_queries():
    """Load new SQL queries for SQL agent."""
    logger.info("Loading new SQL queries.")
    
    # Load base knowledge (không xóa dữ liệu cũ)
    agent_knowledge.load(recreate=False)
    
    # Load new SQL queries
    knowledge_dir = os.path.join(os.path.dirname(__file__), 'knowledge')
    new_queries_dir = os.path.join(knowledge_dir, 'new_queries')
    sql_file = os.path.join(new_queries_dir, 'djia_queries_new.sql')
    
    if os.path.exists(sql_file):
        queries = load_sql_queries(sql_file)
        logger.info(f"Loaded {len(queries)} new SQL queries from djia_queries_new.sql")
    else:
        logger.error(f"File {sql_file} not found")
    
    logger.info("New SQL queries loaded successfully.")

if __name__ == "__main__":
    load_dotenv()
    load_new_queries() 