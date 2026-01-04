import streamlit as st
import sys
import os
import io
import threading
import traceback
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="TradingAgents Dashboard", layout="wide")

st.title("🤖 TradingAgents: AI Financial Analyst")
st.markdown("LLM Agents collaborate to analyze stocks and provide trading recommendations.")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    ticker = st.text_input("Ticker Symbol", value="NVDA").upper()
    target_date = st.date_input("Analysis Date", datetime.today())
    
    st.subheader("Model Settings")
    model_name = st.selectbox("LLM Model", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"], index=1)
    debate_rounds = st.slider("Debate Rounds", 1, 5, 2)

    run_btn = st.button("Analyze", type="primary")

class StreamlitOutputCapture(io.StringIO):
    def __init__(self, placeholder, log_file_path):
        super().__init__()
        self.placeholder = placeholder
        self.output_buffer = ""
        self.log_file_path = log_file_path
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    def write(self, string):
        # 1. Write to memory buffer for UI
        self.output_buffer += string
        if len(self.output_buffer) > 100000:
            self.output_buffer = self.output_buffer[-50000:]
        
        # 2. Write to file
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(string)
        except Exception:
            pass # Ignore file write errors to keep app running
        
        # 3. Update UI
        try:
            self.placeholder.code(self.output_buffer[-5000:], language="text")
        except Exception:
            pass

# Main Area
if run_btn:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OPENAI_API_KEY is missing. Please check your .env file.")
    else:
        # Define log file path with structure: logs/YYYY-MM-DD/TICKER/HHMMSS.log
        current_time = datetime.now()
        date_str = current_time.strftime('%Y-%m-%d')
        time_str = current_time.strftime('%H%M%S')
        
        log_dir = os.path.join("logs", date_str, ticker)
        log_filename = f"{time_str}.log"
        log_path = os.path.join(log_dir, log_filename)
        
        # Create logs directory if it doesn't exist (handled in StreamlitOutputCapture, but good to be explicit)
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a container with fixed height for logs
        st.subheader("📡 Agent Activities & Logs")
        st.caption(f"Logs are being saved to: `{log_path}`")
        
        # Use a container with fixed height for scrolling (Streamlit 1.30+)
        log_container = st.container(height=400)
        log_placeholder = log_container.empty()
        
        status_placeholder = st.empty()
        status_placeholder.info("🚀 Agents are gathering data and debating...")

        # Capture stdout
        capture = StreamlitOutputCapture(log_placeholder, log_path)
        original_stdout = sys.stdout
        sys.stdout = capture

        try:
            # Override Config
            config = DEFAULT_CONFIG.copy()
            config["deep_think_llm"] = model_name
            config["quick_think_llm"] = model_name
            config["max_debate_rounds"] = debate_rounds
            
            # Initialize Graph
            ta = TradingAgentsGraph(debug=True, config=config)
            
            # Run Propagation
            _, decision = ta.propagate(ticker, target_date.strftime("%Y-%m-%d"))
            
            status_placeholder.success("✅ Analysis Complete!")
            
            # Restore stdout immediately after success
            sys.stdout = original_stdout

            # Display Results
            st.divider()
            st.subheader("📊 Final Decision")
            
            if isinstance(decision, dict):
                st.json(decision)
                st.subheader("💡 Detailed Reasoning")
                if "reasoning" in decision:
                    st.write(decision["reasoning"])
                else:
                    st.write("No detailed reasoning provided.")
            else:
                st.info(f"**Decision:** {str(decision)}")
                st.write("Detailed reasoning was not provided in JSON format.")

        except Exception as e:
            # Restore stdout in case of error
            sys.stdout = original_stdout
            st.error("An error occurred during analysis.")
            st.error(f"Error Message: {str(e)}")
            # Print traceback for debugging
            st.code(traceback.format_exc())

        finally:
            # Ensure stdout is always restored
            if sys.stdout != original_stdout:
                sys.stdout = original_stdout
