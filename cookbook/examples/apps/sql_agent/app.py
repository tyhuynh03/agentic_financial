import nest_asyncio
import streamlit as st
from agents import get_sql_agent
from agno.agent import Agent
from agno.utils.log import logger
from dotenv import load_dotenv
from PIL import Image
import os
import re
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
# Cấu hình đường dẫn thư mục chứa ảnh
IMAGE_DIR = "D:/agent_sql/agno"
nest_asyncio.apply()
st.set_page_config(
    page_title="SQrL: DJIA Stock Analysis Agent",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS with dark mode support
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

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
    # Initialize Agent
    ####################################################################
    sql_agent: Agent
    if (
        "sql_agent" not in st.session_state
        or st.session_state["sql_agent"] is None
        or st.session_state.get("current_model") != model_id
    ):
        logger.info("---*--- Creating new SQL agent ---*---")
        sql_agent = get_sql_agent(model_id=model_id)
        st.session_state["sql_agent"] = sql_agent
        st.session_state["current_model"] = model_id
    else:
        sql_agent = st.session_state["sql_agent"]

    ####################################################################
    # Load Agent Session from the database
    ####################################################################
    try:
        st.session_state["sql_agent_session_id"] = sql_agent.load_session()
    except Exception:
        st.warning("Could not create Agent session, is the database running?")
        return

    ####################################################################
    # Load runs from memory
    ####################################################################
    agent_runs = sql_agent.memory.runs
    if len(agent_runs) > 0:
        logger.debug("Loading run history")
        st.session_state["messages"] = []
        for _run in agent_runs:
            if _run.message is not None:
                add_message(_run.message.role, _run.message.content)
            if _run.response is not None:
                add_message("assistant", _run.response.content, _run.response.tools)
    else:
        logger.debug("No run history found")
        st.session_state["messages"] = []

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
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner("🤔 Thinking..."):
                response = ""
                try:
                    run_response = sql_agent.run(
                        question, stream=True, stream_intermediate_steps=True
                    )
                    for _resp_chunk in run_response:
                        if _resp_chunk.tools and len(_resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, _resp_chunk.tools)
                        if (
                            _resp_chunk.event == "RunResponse"
                            and _resp_chunk.content is not None
                        ):
                            response += _resp_chunk.content
                            # Kiểm tra nếu response là file ảnh .png và file tồn tại
                            image_match = re.search(r"([\w\-\.]+\.png)", response)
                            if image_match:
                                image_name = image_match.group(1)
                                image_path = os.path.join(IMAGE_DIR, image_name)
                                if os.path.exists(image_path):
                                    image = Image.open(image_path)
                                    resp_container.image(image, caption="Kết quả biểu đồ", use_container_width=True)
                                else:
                                    resp_container.error(f"Không tìm thấy ảnh: {image_path}")
                            else:
                                resp_container.markdown(response)
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
