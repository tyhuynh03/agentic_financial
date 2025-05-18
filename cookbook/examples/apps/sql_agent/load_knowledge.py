from agents import agent_knowledge
from agno.utils.log import logger
import os
from dotenv import load_dotenv
import json

def load_json_knowledge(file_path: str) -> dict:
    """Load JSON knowledge file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {str(e)}")
        return {}

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

def load_markdown(file_path: str) -> str:
    """Load markdown file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading markdown file {file_path}: {str(e)}")
        return ""

def load_knowledge(recreate: bool = True):
    """Load all knowledge files for SQL agent."""
    logger.info("Loading SQL agent knowledge.")
    
    # Load base knowledge
    agent_knowledge.load(recreate=recreate)
    
    # Load DJIA specific knowledge
    knowledge_dir = os.path.join(os.path.dirname(__file__), 'knowledge')
    
    # Load JSON files
    json_files = ['companies.json', 'prices.json']
    for json_file in json_files:
        file_path = os.path.join(knowledge_dir, json_file)
        if os.path.exists(file_path):
            knowledge = load_json_knowledge(file_path)
            logger.info(f"Loaded knowledge from {json_file}")
    
    # Load SQL queries
    sql_file = os.path.join(knowledge_dir, 'djia_queries.sql')
    if os.path.exists(sql_file):
        queries = load_sql_queries(sql_file)
        logger.info(f"Loaded {len(queries)} SQL queries from djia_queries.sql")
    
    # Load markdown files
    md_files = ['stock_symbols.md']
    for md_file in md_files:
        file_path = os.path.join(knowledge_dir, md_file)
        if os.path.exists(file_path):
            content = load_markdown(file_path)
            logger.info(f"Loaded knowledge from {md_file}")
    
    logger.info("SQL agent knowledge loaded successfully.")

load_dotenv()
if __name__ == "__main__":
    load_knowledge()
