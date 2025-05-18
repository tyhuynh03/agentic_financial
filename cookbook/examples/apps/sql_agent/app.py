import nest_asyncio
import streamlit as st
from agents import get_sql_agent, agent_storage, agent_knowledge
from agno.agent import Agent
from agno.utils.log import logger
from dotenv import load_dotenv
import os
import json
import pandas as pd

from utils import (
    CUSTOM_CSS,
    about_widget,
    add_message,
    display_tool_calls,
    rename_session_widget,
    session_selector_widget,
    sidebar_widget,
)

load_dotenv()

nest_asyncio.apply()
st.set_page_config(
    page_title="SQrL: DJIA Stock Analysis Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS with dark mode support
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Khởi tạo session state nếu chưa có
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "sql_agent" not in st.session_state:
    st.session_state["sql_agent"] = None
if "current_model" not in st.session_state:
    st.session_state["current_model"] = None
if "sql_agent_session_id" not in st.session_state:
    st.session_state["sql_agent_session_id"] = None

def main() -> None:
    ####################################################################
    # App header
    ####################################################################
    st.markdown(
        "<h1 class='main-title'>SQrL: DJIA Stock Analysis Agent</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='subtitle'>SQrL is an intelligent SQL Agent that can analyze stock market data, powered by Agno</p>",
        unsafe_allow_html=True,
    )

    ####################################################################
    # Model selector
    ####################################################################
    model_options = {
        "llama-4-scout": "groq:meta-llama/llama-4-scout-17b-16e-instruct",
        "gemini-2.5-pro-exp-03-25": "google:gemini-2.5-pro-exp-03-25",
    }
    selected_model = st.sidebar.selectbox(
        "Select a model",
        options=list(model_options.keys()),
        index=0,
        key="model_selector",
    )
    model_id = model_options[selected_model]

    ####################################################################
    # Reload Knowledge Button
    ####################################################################
    if st.sidebar.button("🔄 Reload Knowledge"):
        try:
            with st.spinner("Đang tải lại knowledge base..."):
                agent_knowledge.load(recreate=True)
                st.sidebar.success("Knowledge base đã được tải lại thành công!")
        except Exception as e:
            st.sidebar.error(f"Lỗi: {str(e)}")
            logger.exception("Error reloading knowledge base")

    ####################################################################
    # Initialize Agent
    ####################################################################
    try:
        if (
            "sql_agent" not in st.session_state
            or st.session_state["sql_agent"] is None
            or st.session_state.get("current_model") != model_id
        ):
            logger.info("---*--- Creating new SQL agent ---*---")
            sql_agent = get_sql_agent(
                name="SQrL",
                model_id=model_id,
                debug_mode=True,
                session_id=None  # Để agent tự tạo session mới
            )
            if sql_agent is None:
                st.error("Failed to initialize SQL agent")
                return
            st.session_state["sql_agent"] = sql_agent
            st.session_state["current_model"] = model_id
            st.session_state["sql_agent_session_id"] = sql_agent.session_id
        else:
            sql_agent = st.session_state["sql_agent"]

        ####################################################################
        # Load Agent Session from the database
        ####################################################################
        if "sql_agent_session_id" not in st.session_state or st.session_state["sql_agent_session_id"] is None:
            session_id = sql_agent.load_session()
            if session_id is None:
                st.warning("Could not create Agent session")
                return
            st.session_state["sql_agent_session_id"] = session_id

        ####################################################################
        # Load runs from memory
        ####################################################################
        if hasattr(sql_agent, 'memory') and sql_agent.memory is not None:
            agent_runs = sql_agent.memory.runs
            if agent_runs and len(agent_runs) > 0:
                logger.debug("Loading run history")
                if "messages" not in st.session_state or not st.session_state["messages"]:
                    st.session_state["messages"] = []
                    for _run in agent_runs:
                        if _run.message is not None:
                            add_message(_run.message.role, _run.message.content)
                        if _run.response is not None:
                            add_message("assistant", _run.response.content, _run.response.tools)
            else:
                logger.debug("No run history found")
                if "messages" not in st.session_state:
                    st.session_state["messages"] = []
        else:
            logger.warning("Agent memory not initialized")
            if "messages" not in st.session_state:
                st.session_state["messages"] = []
            # Khởi tạo lại memory nếu chưa có
            try:
                sql_agent.memory = agent_storage.create_memory(sql_agent.session_id)
            except Exception as e:
                logger.error(f"Error creating memory: {str(e)}")
                st.error("Could not initialize agent memory")

    except Exception as e:
        st.error(f"Error initializing agent: {str(e)}")
        return

    ####################################################################
    # Sidebar
    ####################################################################
    sidebar_widget()

    ####################################################################
    # Get user input
    ####################################################################
    if prompt := st.chat_input("👋 Ask me about DJIA stock market data!"):
        add_message("user", prompt)

    ####################################################################
    # Display chat history
    ####################################################################
    for message in st.session_state["messages"]:
        if message["role"] in ["user", "assistant"]:
            _content = message["content"]
            if _content is not None:
                with st.chat_message(message["role"]):
                    # Display tool calls if they exist in the message
                    if "tool_calls" in message and message["tool_calls"]:
                        display_tool_calls(st.empty(), message["tool_calls"])
                    st.markdown(_content)

    ####################################################################
    # Generate response for user message
    ####################################################################
    last_message = (
        st.session_state["messages"][-1] if st.session_state["messages"] else None
    )
    if last_message and last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            # Create container for tool calls
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner("🤔 Analyzing..."):
                response = ""
                try:
                    # Run the agent and stream the response
                    run_response = sql_agent.run(
                        question, stream=True, stream_intermediate_steps=True
                    )
                    for _resp_chunk in run_response:
                        # Display tool calls if available
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)

                        # Display response if available and event is RunResponse
                        if (
                            _resp_chunk.event == "RunResponse"
                            and _resp_chunk.content is not None
                        ):
                            # Format SQL query display
                            content = _resp_chunk.content
                            if "SQL query used:" in content:
                                parts = content.split("SQL query used:")
                                text_part = parts[0]
                                sql_part = parts[1]
                                # Format SQL query with proper indentation
                                sql_lines = sql_part.strip().split("\n")
                                formatted_sql = "\n".join(line.strip() for line in sql_lines)
                                content = f"{text_part}SQL query used:\n```sql\n{formatted_sql}\n```"
                            response += content
                            resp_container.markdown(response + "\n\n" + "---")

                        add_message("assistant", response, sql_agent.run_response.tools)
                except Exception as e:
                    logger.exception(e)
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    add_message("assistant", error_message)
                    st.error(error_message)

    ####################################################################
    # Session selector
    ####################################################################
    session_selector_widget(sql_agent, model_id)
    rename_session_widget(sql_agent)

    ####################################################################
    # About section
    ####################################################################
    about_widget()

if __name__ == "__main__":
    main()
