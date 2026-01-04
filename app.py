import streamlit as st
import sys
import os
import io
import threading
import traceback
from datetime import datetime
from openai import OpenAI

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
            pass # Ignore file write errors
        
        # 3. Update UI
        try:
            self.placeholder.code(self.output_buffer[-5000:], language="text")
        except Exception:
            pass
            
    def get_logs(self):
        return self.output_buffer

def generate_summary(logs, model_name):
    """Generate a structured summary using LLM based on the execution logs."""
    try:
        client = OpenAI()
        prompt = f"""
        You are an expert financial analyst editor. 
        Below are the execution logs from a multi-agent trading analysis system.
        
        Please summarize the findings into a structured report with the following sections:
        1. **📊 Fundamental Analysis**: Key financial metrics and growth outlook.
        2. **📈 Technical Analysis**: Chart trends, indicators (MACD, RSI, etc.).
        3. **📰 Sentiment & News**: Market sentiment and key news drivers.
        4. **🛡️ Risk Assessment**: Main risks and bearish arguments.
        5. **📝 Final Verdict**: The final decision (BUY/SELL/HOLD) and the core reason.
        
        Keep it concise, professional, and easy to read. Use bullet points.
        
        --- LOGS START ---
        {logs[-30000:]} 
        --- LOGS END ---
        """
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Failed to generate summary: {str(e)}"

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
        
        # Create logs directory if it doesn't exist
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
            st.subheader("📊 Final Decision & Summary")
            
            # 1. Display Simple Decision
            if isinstance(decision, dict) and "decision" in decision:
                 final_decision = decision["decision"]
            else:
                 # Clean up string decision (remove markdown bold if present)
                 final_decision = str(decision).replace("**", "").replace("FINAL TRANSACTION PROPOSAL:", "").strip()
            
            st.info(f"### Decision: {final_decision}")
            
            # 2. Generate and Display AI Summary
            with st.spinner("✍️ Writing final report based on agent debates..."):
                logs = capture.get_logs()
                summary = generate_summary(logs, model_name)
                st.markdown(summary)
                
                # 3. Save summary to a separate file
                try:
                    summary_path = log_path.replace(".log", "_summary.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(f"# Analysis Summary for {ticker} ({date_str})\n\n")
                        f.write(f"**Final Decision: {final_decision}**\n\n")
                        f.write(summary)
                    st.caption(f"Summary saved to: `{summary_path}`")
                except Exception as save_e:
                    st.warning(f"Could not save summary file: {str(save_e)}")
                
                # Save summary to file
                try:
                    summary_path = log_path.replace(".log", "_summary.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(summary)
                    st.caption(f"Summary saved to: `{summary_path}`")
                except Exception as e:
                    st.warning(f"Failed to save summary file: {str(e)}")
                
                # Save summary to file
                try:
                    summary_path = log_path.replace(".log", "_summary.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(f"# Analysis Summary for {ticker} ({date_str})\n\n")
                        f.write(f"**Final Decision:** {final_decision}\n\n")
                        f.write(summary)
                    st.caption(f"Summary report saved to: `{summary_path}`")
                except Exception as save_e:
                    st.warning(f"Could not save summary file: {str(save_e)}")
                
                # Save summary to file
                try:
                    summary_path = log_path.replace(".log", "_summary.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(summary)
                    st.caption(f"Summary report saved to: `{summary_path}`")
                except Exception as e:
                    st.warning(f"Could not save summary file: {str(e)}")

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
