import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import streamlit as st
from agents import get_sql_agent
from agno.agent.agent import Agent
from agno.utils.log import logger
import pandas as pd


def is_json(myjson):
    """Check if a string is valid JSON"""
    try:
        json.loads(myjson)
    except (ValueError, TypeError):
        return False
    return True


def load_data_and_knowledge():
    """Load F1 data and knowledge base if not already done"""
    from load_f1_data import load_f1_data
    from load_knowledge import load_knowledge

    if "data_loaded" not in st.session_state:
        with st.spinner("🔄 Loading data into database..."):
            load_f1_data()
        with st.spinner("📚 Loading knowledge base..."):
            load_knowledge()
        st.session_state["data_loaded"] = True
        st.success("✅ Data and knowledge loaded successfully!")


def add_message(
    role: str, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None
) -> None:
    """Safely add a message to the session state"""
    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = []
    st.session_state["messages"].append(
        {"role": role, "content": content, "tool_calls": tool_calls}
    )


def restart_agent():
    """Reset the agent and clear chat history"""
    logger.debug("---*--- Restarting agent ---*---")
    st.session_state["sql_agent"] = None
    st.session_state["sql_agent_session_id"] = None
    st.session_state["messages"] = []
    st.rerun()


def export_chat_history():
    """Export chat history as markdown"""
    if "messages" in st.session_state:
        chat_text = "# Reasoning SQL Agent - Chat History\n\n"
        for msg in st.session_state["messages"]:
            role = "🤖 Assistant" if msg["role"] == "agent" else "👤 User"
            chat_text += f"### {role}\n{msg['content']}\n\n"
        return chat_text
    return ""


def display_tool_calls(tool_calls_container, tools):
    """Display tool calls in a streamlit container with expandable sections.

    Args:
        tool_calls_container: Streamlit container to display the tool calls
        tools: List of tool call dictionaries containing name, args, content, and metrics
    """
    try:
        with tool_calls_container.container():
            for tool_call in tools:
                tool_name = tool_call.get("tool_name", "Unknown Tool")
                tool_args = tool_call.get("tool_args", {})
                content = tool_call.get("content", None)
                metrics = tool_call.get("metrics", None)

                # Add timing information
                execution_time_str = "N/A"
                try:
                    if metrics is not None and hasattr(metrics, "time"):
                        execution_time = metrics.time
                        if execution_time is not None:
                            execution_time_str = f"{execution_time:.4f}s"
                except Exception as e:
                    logger.error(f"Error displaying tool calls: {str(e)}")
                    pass

                with st.expander(
                    f"🛠️ {tool_name.replace('_', ' ').title()} ({execution_time_str})",
                    expanded=False,
                ):
                    # Show query with syntax highlighting
                    if isinstance(tool_args, dict) and "query" in tool_args:
                        st.code(tool_args["query"], language="sql")

                    # Display arguments in a more readable format
                    if tool_args and tool_args != {"query": None}:
                        st.markdown("**Arguments:**")
                        st.json(tool_args)

                    if content is not None:
                        try:
                            if is_json(content):
                                st.markdown("**Results:**")
                                # Chuyển đổi JSON thành DataFrame để hiển thị
                                if isinstance(content, str):
                                    content = json.loads(content)
                                df = pd.DataFrame.from_records(content)
                                # Hiển thị DataFrame với đầy đủ dữ liệu
                                st.dataframe(df, use_container_width=True, height=400)
                                # Hiển thị thông tin về số lượng dòng
                                st.write(f"Tổng số dòng: {len(df)}")
                        except Exception as e:
                            logger.debug(f"Skipped tool call content: {e}")
    except Exception as e:
        logger.error(f"Error displaying tool calls: {str(e)}")
        tool_calls_container.error("Failed to display tool results")


def sidebar_widget() -> None:
    """Display the sidebar widget with sample queries."""
    st.sidebar.markdown("## 🏆 Sample Queries")
    
    if st.sidebar.button("📋 Show Tables"):
        add_message("user", "Which tables do you have access to?")
        
    if st.sidebar.button("💰 Top Market Cap"):
        add_message("user", "Show me the top 5 companies by market cap")
        
    if st.sidebar.button("📊 Sector Performance"):
        add_message("user", "Compare stock performance between technology and healthcare sectors")
        
    if st.sidebar.button("📈 Trading Volume"):
        add_message("user", "Show me the daily trading volume for Apple stock")
        
    if st.sidebar.button("💵 Dividend Yield"):
        add_message("user", "Which companies have the highest dividend yield?")
        
    if st.sidebar.button("📉 Price Range"):
        add_message("user", "Show me the 52-week high/low price range for each stock")
        
    if st.sidebar.button("📈 Moving Average"):
        add_message("user", "Calculate the 30-day moving average for Microsoft stock")

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🛠️ Utilities")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 New Chat"):
            restart_agent()
    with col2:
        fn = "sql_agent_chat_history.md"
        if "sql_agent_session_id" in st.session_state:
            fn = f"sql_agent_{st.session_state.sql_agent_session_id}.md"
        if st.download_button(
            "💾 Export Chat",
            export_chat_history(),
            file_name=fn,
            mime="text/markdown",
        ):
            st.sidebar.success("Chat history exported!")


def session_selector_widget(agent: Agent, model_id: str) -> None:
    """Display the session selector widget."""
    st.sidebar.markdown("## 💾 Sessions")
    if agent.storage:
        agent_sessions = agent.storage.get_all_sessions()
        # Get session names if available, otherwise use IDs
        session_options = []
        for session in agent_sessions:
            session_id = session.session_id
            session_name = (
                session.session_data.get("session_name", None)
                if session.session_data
                else None
            )
            display_name = session_name if session_name else session_id
            session_options.append({"id": session_id, "display": display_name})

        # Display session selector
        if session_options:
            selected_session = st.sidebar.selectbox(
                "Session",
                options=[s["display"] for s in session_options],
                key="session_selector",
            )
            # Find the selected session ID
            selected_session_id = next(
                s["id"] for s in session_options if s["display"] == selected_session
            )

            if st.session_state["sql_agent_session_id"] != selected_session_id:
                logger.info(
                    f"---*--- Loading {model_id} run: {selected_session_id} ---*---"
                )
                st.session_state["sql_agent"] = get_sql_agent(
                    model_id=model_id,
                    session_id=selected_session_id,
                )
                st.rerun()


def rename_session_widget(agent: Agent) -> None:
    """Display the rename session widget."""
    if st.sidebar.button("Rename Current Session"):
        new_name = st.sidebar.text_input("New Session Name")
        if new_name:
            agent.rename_session(new_name)
            st.rerun()


def about_widget() -> None:
    """Display the about widget."""
    st.sidebar.markdown("## 📊 About")
    st.sidebar.markdown(
        """
        This app uses Agno to analyze DJIA stock market data. It can:
        - Analyze company performance
        - Compare sector trends
        - Track stock prices
        - Calculate financial metrics
        - Generate market insights
        """
    )


CUSTOM_CSS = """
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .stChatMessage[data-testid="stChatMessage"] {
        background-color: #f0f2f6;
    }
    .stChatMessage[data-testid="stChatMessage"] .stMarkdown {
        color: #333;
    }
    .stChatMessage[data-testid="stChatMessage"] .stCodeBlock {
        background-color: #fff;
        border-radius: 0.25rem;
        padding: 0.5rem;
    }
</style>
"""
