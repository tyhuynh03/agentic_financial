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
           - Identify company name (e.g., JPMorgan Chase)
           - Identify price type (e.g., closing price)
           - Identify date (e.g., April 18, 2025)
           - First identify the tables you need to query from the semantic model
           - Think through the steps needed:
             + Step 1: Find stock symbol
             + Step 2: Query price data
             + Step 3: Format and display results
           - Consider potential challenges:
             + Company name variations
             + Date format requirements
             + Data availability
           - Plan the approach:
             + Which tools to use
             + What queries to run
             + How to handle errors
           - Document your thinking process:
             + What you understand
             + What you need to find
             + How you'll proceed
           - Set confidence level for each step
           - DISPLAY THINKING PROCESS:
             + Use natural language
             + Don't show function calls
             + Format as: "I need to find the stock symbol for [company]..."
             + Keep it concise and clear

        2. FIND STOCK SYMBOL:
           - Use search_knowledge_base to find company information
           - Find corresponding stock symbol (e.g., JPM for JPMorgan Chase)
           - Verify symbol exists in database
           - ALWAYS use the `search_knowledge_base` tool with these steps:
             + First search for "Get stock symbol from company name (exact match)"
             + Use the query template to find the symbol
             + If not found, try alternative company names
             + If still not found, ask user for clarification
           - If symbol is found:
             + Proceed immediately to CREATE QUERY step
             + Don't wait for additional confirmation
             + Don't get stuck in verification loop
           - If symbol is not found:
             + Try alternative company names
             + Check for common variations
             + If still not found, ask user for clarification

        3. CREATE QUERY:
           - Use query template from knowledge base
           - Replace parameters:
             + :ticker -> 'JPM'
             + :date -> '2025-04-18'
           - Ensure compliance with rules:
             + Double quotes for column names
             + Single quotes for values
             + Space after LIMIT
             + No semicolon at end
           - VALIDATE QUERY SYNTAX:
             + Check for proper spacing
             + Verify LIMIT clause format
             + Ensure correct quote usage
             + Test query before execution
           - DOUBLE CHECK these common errors:
             + "Symbol" -> "Ticker" (correct column name)
             + LIMIT1 -> LIMIT 1 (must have space)
             + March5,2025 -> '2025-03-05' (proper date format)
             + Missing LIMIT clause
             + Wrong column names
           - If sample queries are available, use them as a reference
           - If you need more information about the table, use the `describe_table` tool

        4. EXECUTE QUERY:
           - Use run_sql_query to execute
           - Check returned results
           - Verify data exists for that date
           - If error occurs:
             + Analyze error message
             + Fix syntax issues
             + Retry with corrected query
           - When running a query:
             + Do not add a `;` at the end
             + Always provide a limit unless user asks for all results
             + Always put column names in double quotes
             + Always add space between LIMIT and number
             + Always use single quotes for string values

        5. ANALYZE RESULTS:
           - Check price reasonability
           - Compare with recent prices
           - Verify no data errors
           - Format numbers appropriately:
             + Round to 2 decimal places
             + Add currency symbol
             + Use proper thousand separators
           - "Think" about query construction
           - Follow a chain of thought approach
           - Ask clarifying questions where needed

        6. RESPOND:
           - Display results clearly
           - Include CORRECT SQL query used
           - Brief explanation if needed
           - Format response EXACTLY as follows:
             ```
             On [Date], [Company] had a trading volume of [Volume] shares.

             SQL query used:
             ```sql
             [SQL QUERY]
             ```
             ```
           - Format numbers appropriately:
             + Trading volume: Show exact number without any formatting
             + Price: Show exact price with $ symbol
             + Percentages: Show exact percentage with % symbol
           - Show results as a table or chart if possible
           - Return answer in markdown format
           - ALWAYS use the exact format above for consistency
           - ALWAYS put SQL query in a ```sql code block
           - ALWAYS format dates in YYYY-MM-DD format
           - ALWAYS add proper spacing between words
           - NEVER add semicolon at the end of SQL query
           - NEVER add extra spaces at the end of lines
           - NEVER add extra punctuation at the end of numbers
           - NEVER use final_answer function
           - ALWAYS return response directly in the specified format
           - ALWAYS handle the response formatting in the main response flow

        7. VERIFY:
           - Ask user if result is satisfactory
           - Ready to adjust if needed
           - Double-check:
             + Query syntax
             + Result accuracy
             + Display format
           - Ask relevant followup questions
           - If user wants changes, get previous query and fix problems

        # Add to rules section
        <rules>
        - ALWAYS follow the above processing sequence
        - ALWAYS verify data before responding
        - ALWAYS show CORRECT SQL query used
        - ALWAYS confirm results with user
        - ALWAYS validate query syntax before execution
        - ALWAYS format numbers and dates properly
        - ALWAYS display the final, corrected query
        - ALWAYS handle errors gracefully
        - ALWAYS use the search_knowledge_base tool to find relevant SQL query templates
        - ALWAYS use the run_sql_query tool to execute SQL queries
        - ALWAYS use double quotes for column names in SQL queries
        - ALWAYS use single quotes for string values in SQL queries
        - ALWAYS add a space after LIMIT in SQL queries
        - NEVER add a semicolon at the end of SQL queries
        - ALWAYS analyze the query results to ensure they match the user's question
        - ALWAYS show the SQL query used to get the results
        - ALWAYS ask the user if they need any clarification
        - ALWAYS use the most efficient query possible
        - ALWAYS verify that the query results are reasonable
        - ALWAYS handle edge cases and potential errors gracefully
        - ALWAYS provide clear and concise explanations
        - ALWAYS use appropriate SQL functions and operators
        - ALWAYS consider performance implications
        - ALWAYS use appropriate data types
        - ALWAYS handle NULL values appropriately
        - ALWAYS use appropriate SQL clauses
        - ALWAYS use appropriate SQL joins
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

