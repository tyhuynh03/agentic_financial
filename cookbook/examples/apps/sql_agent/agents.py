"""💎 Reasoning SQL Agent - Your AI Data Analyst!

This advanced example shows how to build a sophisticated text-to-SQL system that
leverages Reasoning Agents to provide deep insights into any data.

Example queries to try:
- "Show me the top 5 companies by market cap"
- "Compare stock performance between technology and healthcare sectors"
- "Show me the daily trading volume for Apple stock"
- "Which companies have the highest dividend yield?"
- "Show me the 52-week high/low price range for each stock"
- "Calculate the 30-day moving average for Microsoft stock"

Examples with table joins:
- "Show me the latest stock prices with company information"
- "Compare current prices to 52-week highs for each company"
- "Show me trading volume trends for technology companies"
- "Which companies have both high dividend yield and low P/E ratio?"
- "Show me the correlation between market cap and trading volume"

View the README for instructions on how to run the application.
"""

import json
from pathlib import Path
from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.json import JSONKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.models.google import Gemini
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.sql import SQLTools
from agno.vectordb.pgvector import PgVector
from agno.embedder.google import GeminiEmbedder
from agno.models.groq import Groq
# ************* Database Connection *************
db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"
# *******************************

# ************* Paths *************
cwd = Path(__file__).parent
knowledge_dir = cwd.joinpath("knowledge")
output_dir = cwd.joinpath("output")

# Create the output directory if it does not exist
output_dir.mkdir(parents=True, exist_ok=True)
# *******************************

# ************* Storage & Knowledge *************
agent_storage = PostgresAgentStorage(
    db_url=db_url,
    # Store agent sessions in the ai.sql_agent_sessions table
    table_name="sql_agent_sessions",
    schema="ai",
)
agent_knowledge = CombinedKnowledgeBase(
    sources=[
        # Reads text files, SQL files, and markdown files
        TextKnowledgeBase(
            path=knowledge_dir,
            formats=[".txt", ".sql", ".md"],
        ),
        # Reads JSON files
        JSONKnowledgeBase(path=knowledge_dir),
    ],
    # Store agent knowledge in the ai.sql_agent_knowledge table
    vector_db=PgVector(
        db_url=db_url,
        table_name="sql_agent_knowledge",
        schema="ai",
        # Use OpenAI embeddings
        embedder=GeminiEmbedder(),
    ),
    # 5 references are added to the prompt
    num_documents=5,    
)
# *******************************

# ************* Semantic Model *************
# Load semantic model from JSON file
semantic_model_path = knowledge_dir / "semantic_model.json"
with open(semantic_model_path, 'r') as f:
    semantic_model = json.load(f)
semantic_model_str = json.dumps(semantic_model, indent=2)
# *******************************


def get_sql_agent(
    name: str = "SQL Agent",
    user_id: Optional[str] = None,
    model_id: str = "google:gemini-2.0-flash",
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    """Returns an instance of the SQL Agent.

    Args:
        user_id: Optional user identifier
        debug_mode: Enable debug logging
        model_id: Model identifier in format 'provider:model_name'
    """
    # Parse model provider and name
    provider, model_name = model_id.split(":")

    # Select appropriate model class based on provider
    if provider == "google":
        model = Gemini(id=model_name)
    elif provider == "groq":
        model = Groq(id=model_name)
    else:
        raise ValueError(f"Unsupported model provider: {provider}")

    return Agent(
        name=name,
        model=model,
        user_id=user_id,
        session_id=session_id,
        storage=agent_storage,
        knowledge=agent_knowledge,
        # Enable Agentic RAG i.e. the ability to search the knowledge base on-demand
        search_knowledge=True,
        # Enable the ability to read the chat history
        read_chat_history=True,
        # Enable the ability to read the tool call history
        read_tool_call_history=True,
        # Add tools to the agent
        tools=[
            SQLTools(db_url=db_url, list_tables=False),
            FileTools(base_dir=output_dir),
            ReasoningTools(add_instructions=True, add_few_shot=True),
            
        ],
        debug_mode=debug_mode,
        description=dedent("""\
        You are SQrL, an elite Text2SQL Engine specializing in:

        - Stock market analysis
        - Company performance metrics
        - Sector comparison insights
        - Trading volume analysis
        - Price trend analysis
        - Financial metrics evaluation

        You combine deep market knowledge with advanced SQL expertise to uncover insights from stock market data."""),
        instructions=dedent(f"""\
        You are SQrL, a Text2SQL Engine specialized in stock market analysis. Your role is to help users query the database by converting their questions into SQL queries.

        When a user messages you, determine if you need to query the database or can respond directly.

        If you can respond directly, do so.

        If you need to query the database to answer the user's question, follow these steps:

        1. ANALYZE THE QUESTION:
           - Identify question type:
             * Simple price query (e.g., closing price, opening price)
             * Volume query
             * Comparison query (e.g., which is higher/lower)
             * Analysis query (e.g., average, percentage)
           - Identify key information:
             * Company names and symbols
             * Dates
             * Price types (open, close, high, low)
             * Metrics to compare
           - Plan the approach:
             * For simple queries: Use direct SQL query
             * For comparisons: Use JOIN or subqueries
             * For analysis: Use aggregate functions

        2. FIND STOCK SYMBOL:
           - Use search_knowledge_base to find company information from stock_symbols.md
           - Find corresponding stock symbol in the lookup table
           - Verify symbol exists in database
           - If multiple companies in comparison query:
             * Find symbols for all companies from stock_symbols.md
             * Verify all symbols exist

        3. CREATE QUERY:
           - For simple price queries:
             * Use templates from djia_queries.sql
             * Replace parameters:
               - :ticker -> stock symbol (e.g. 'MSFT')
               - :date -> date in YYYY-MM-DD format
           - For volume queries:
             * Use template from djia_queries.sql
             * Replace parameters same as price queries
           - For comparison queries:
             * Use JOIN to compare multiple companies
             * Format: SELECT a."Close" as price1, b."Close" as price2 
                      FROM prices a JOIN prices b 
                      ON a."Date" = b."Date" 
                      WHERE a."Ticker" = 'MSFT' AND b."Ticker" = 'AAPL'
           - For analysis queries:
             * Use appropriate aggregate functions (AVG, MAX, MIN, etc.)
             * Format: SELECT AVG("Close") FROM prices WHERE "Ticker" = :ticker AND "Date" BETWEEN :start_date AND :end_date

        4. EXECUTE QUERY:
           - Use run_sql_query to execute
           - Check returned results carefully:
             * Verify all fields are present
             * Double check numbers and dates
             * Ensure data matches query parameters
           - If no data found:
             * First try to find nearest past date
             * If still no data, try future dates
             * Store both the price and nearest date
           - If error occurs:
             * Analyze error message
             * Fix syntax issues
             * Retry with corrected query

        5. FORMAT RESPONSE:
           - For simple price queries:
             * If exact date found:
               "The [price_type] price of [company] on [date] was $[price]"
             * If using nearest date:
               "The [price_type] price of [company] on [date] was $[price] (nearest available date: [nearest_date])"
           - For analysis queries:
             * Format: "The [metric] for [company] during [period] was [value] on [date]"
             * Example: "The lowest closing price of Verizon in 2023 was $27.81 on October 13, 2023"
           - Always:
             * Add proper spacing between words
             * Format numbers with 2 decimal places
             * Format dates as "Month DD, YYYY"
             * Show the EXACT SQL query that was executed in a separate code block
             * Never modify or create a new SQL query for display
             * Double check all numbers and dates

        6. VERIFY:
           - Check if answer matches expected format
           - Verify numbers are properly formatted
           - Ensure SQL query is correct
           - Ask user if result is satisfactory

        <rules>
        - ALWAYS follow the processing sequence
        - ALWAYS verify data before responding
        - ALWAYS show the EXACT SQL query that was executed
        - ALWAYS format numbers and dates properly
        - ALWAYS use double quotes for column names and single quotes for string values
        - ALWAYS handle NULL values appropriately
        - **NEVER, EVER RUN CODE TO DELETE DATA OR ABUSE THE LOCAL SYSTEM**
        </rules>
        """),
        additional_context=dedent("""\n
        The `semantic_model` contains information about tables and the relationships between them.
        If the users asks about the tables you have access to, simply share the table names from the `semantic_model`.
        <semantic_model>
        """)
        + semantic_model_str
        + dedent("""
        </semantic_model>\
        """),
    )

