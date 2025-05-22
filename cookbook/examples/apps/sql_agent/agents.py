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
from agno.document.chunking.fixed import FixedSizeChunking
from agno.tools.knowledge import KnowledgeTools
from plot_tool import PlotTools
from tools.format_sql_result import FormatSQLTool
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
            chunking_strategy=FixedSizeChunking(chunk_size=2000, overlap=100),
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
    num_documents=4,    
)
# *******************************

# ************* Semantic Model *************
# Load semantic model from JSON file
semantic_model_path = knowledge_dir / "semantic_model.json"
with open(semantic_model_path, 'r') as f:
    semantic_model = json.load(f)
semantic_model_str = json.dumps(semantic_model, indent=2)
# *******************************

class UnlimitedSQLTools(SQLTools):
    def run_sql_query(self, query: str) -> str:
        """Override run_sql_query to return all results"""
        return super().run_sql_query(query, limit=None)

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
        # Add references from knowledge base to user prompt
        # add_references=True,
        # Add tools to the agent
        tools=[
            UnlimitedSQLTools(db_url=db_url, list_tables=False),
            FileTools(base_dir=output_dir),
            ReasoningTools(add_instructions=True, add_few_shot=True, think=True),
            PlotTools(),
            # FormatSQLTool(),
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
             * Price query (e.g., closing price, opening price)
             * Volume query
             * Comparison query (e.g., which is higher/lower)
             * Analysis query (e.g., average, percentage)
             * Plot query (e.g., show trend, visualize data)
                            
           - Identify key information:
             * Company names and symbols
             * Dates
             * Price types (open, close, high, low)
             * Metrics to compare
             * Plot type (line, bar, scatter)
             * Time range for plot
           
           - Plan the approach:
             * Search keywords for matching template in knowledge base
             * If found, use template and replace parameters
             * If not found, use basic SQL query structure
             * For plots: 
               - query data first
               - Convert query results to list of dicts format
               - Use PlotTool to visualize with proper parameters

        2. SEARCH FOR EXAMPLE QUERIES:
           - Use search_knowledge_base to find similar queries in the knowledge base 
             # example:Plot the histogram of daily returns of Boeing (BA) during 2024
               search_knowledge_base("Get daily returns data")
             # example:How many dividends did Apple pay in 2024?  
               search_knowledge_base("Count number of dividends paid by a company in a specific year")
             # example:What dividend per share did Microsoft pay on May 17, 2023?
               search_knowledge_base("Get dividend amount for a specific stock on a specific date")
             # example:By what percentage did Apple’s stock price increase in 2024?
               search_knowledge_base("percentage price change ")
             # example:What was Boeing’s beta (relative to the DJIA index) for 2024?
               search_knowledge_base("Calculate stock's beta relative")
           - Look for queries with similar purpose or structure               
           - If found, use the example query as a template
           - If not found, create a new query


        4. CREATE QUERY:
           - If example query found:
             * Use the query as a template
             * Replace parameters with actual values:
               - :ticker -> stock symbol (e.g. 'MSFT')
               - :date -> date in YYYY-MM-DD format
               - :company_name -> company name
               - :year -> year number
             * Adjust the query if needed
           - If no example found:
             * Create a new query following SQL best practices
             * Use proper table and column names
             * Include necessary JOINs and conditions

        5. EXECUTE QUERY:
           - Use run_sql_query to execute
           - Check returned results carefully:
             * Verify all fields are present
             * Double check numbers and dates
             * Ensure data matches query parameters
           - If no data found:
             * First try to find nearest past date
             * If still no data, try future dates
             * Store both the price and nearest date
           - For plotting, query the data and use PlotTools to visualize

        6. FORMAT RESPONSE:
           - Provide the answer in a natural way
           - ALWAYS show the SQL query that was executed in a code block:
             ```sql
             SELECT ... FROM ... WHERE ...
             ```  
            
        7. VERIFY:
           - Check if answer matches expected format
           - Verify numbers are properly formatted
           - Ensure SQL query is correct and displayed
           - Ask user if result is satisfactory

        <rules>
        - ALWAYS follow the processing sequence
        - ALWAYS verify data before responding
        - ALWAYS show the EXACT SQL query that was executed in a code block
        - ALWAYS format numbers and dates properly
        - ALWAYS use double quotes for column names and single quotes for string values
        - ALWAYS handle NULL values appropriately
        - ALWAYS search for example queries before creating new ones
        - ALWAYS use example queries as templates when available
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

