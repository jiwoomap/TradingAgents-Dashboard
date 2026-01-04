import streamlit as st
import sys
import os
import io
import threading
import traceback
import re
from datetime import datetime
from openai import OpenAI

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

from tradingagents.agents.utils.memory import FinancialSituationMemory

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

    st.subheader("🧠 Knowledge Base (Obsidian)")
    
    # Get local path from env for display
    env_vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")
    
    # UI shows the local path (user friendly)
    user_input_path = st.text_input("Vault Path (Local Absolute Path)", value=env_vault_path)
    
    # Logic to determine the actual internal path to use
    # If running in Docker, we must use the mount point /app/obsidian_vault
    # mapping logic: if user_input == env_path and /app/obsidian_vault exists -> use /app/obsidian_vault
    
    obsidian_path = user_input_path
    is_docker = os.path.exists("/app/obsidian_vault")
    
    if is_docker and user_input_path == env_vault_path:
        obsidian_path = "/app/obsidian_vault"
        st.caption(f"ℹ️ Docker Mode: Local path `{user_input_path}` is mounted to `{obsidian_path}` inside the container.")
    elif is_docker:
        st.warning("⚠️ You are in Docker mode. Unless you mounted a different volume, custom paths might not work.")
        
    enable_obsidian_save = st.checkbox("Auto-save reports to Obsidian", value=True)
    
    run_btn = st.button("Analyze", type="primary")
    
    if st.button("Sync Memories from Obsidian"):
        if not os.path.exists(obsidian_path):
            st.error(f"Path not found: {obsidian_path}\n\nDid you mount your local vault to Docker? Add this to docker-compose.yml:\n`- /path/to/your/vault:/app/obsidian_vault`")
        else:
            with st.spinner("Syncing markdown notes..."):
                # Temporary init to access memory
                temp_config = DEFAULT_CONFIG.copy()
                temp_mem = FinancialSituationMemory("invest_judge_memory", temp_config)
                msg = temp_mem.load_from_obsidian(obsidian_path)
                st.success(msg)

class StreamlitOutputCapture(io.StringIO):
    def __init__(self, placeholder, log_file_path):
        super().__init__()
        self.placeholder = placeholder
        self.output_buffer = ""
        self.log_file_path = log_file_path
        self.debate_buffer = [] # Store filtered debate messages
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    def write(self, string):
        # 1. Filter and store debate messages
        self._filter_debate_message(string)

        # 2. Write to memory buffer for UI
        self.output_buffer += string
        if len(self.output_buffer) > 100000:
            self.output_buffer = self.output_buffer[-50000:]
        
        # 3. Write to file
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(string)
        except Exception:
            pass # Ignore file write errors
        
        # 4. Update UI
        try:
            self.placeholder.code(self.output_buffer[-5000:], language="text")
        except Exception:
            pass
            
    def get_logs(self):
        return self.output_buffer

    def _filter_debate_message(self, text):
        """Filter specific agent messages for the debate log."""
        # Simple keywords to identify agent speech
        keywords = [
            "Bull Analyst:", "Bear Analyst:", 
            "[Research Manager Decision]", 
            "Risky Analyst:", "Safe Analyst:", "Neutral Analyst:", 
            "[Risk Manager Decision]"
        ]
        
        # Check if the text block contains any of the keywords
        for keyword in keywords:
            if keyword in text:
                # Clean up and format
                clean_text = text.strip()
                if clean_text:
                    self.debate_buffer.append(clean_text)
                break
    
    def get_debate_transcript(self):
        """Return the formatted debate transcript."""
        if not self.debate_buffer:
            return "No debate transcript available."
            
        transcript = ""
        for msg in self.debate_buffer:
            if "Bull Analyst:" in msg:
                transcript += f"### 🐂 {msg}\n\n---\n\n"
            elif "Bear Analyst:" in msg:
                transcript += f"### 🐻 {msg}\n\n---\n\n"
            elif "[Research Manager Decision]" in msg:
                transcript += f"### 👨‍⚖️ {msg}\n\n---\n\n"
            elif "Risky Analyst:" in msg:
                transcript += f"### 🚀 {msg}\n\n---\n\n"
            elif "Safe Analyst:" in msg:
                transcript += f"### 🛡️ {msg}\n\n---\n\n"
            elif "Neutral Analyst:" in msg:
                transcript += f"### ⚖️ {msg}\n\n---\n\n"
            elif "[Risk Manager Decision]" in msg:
                transcript += f"### 👮 {msg}\n\n---\n\n"
            else:
                transcript += f"{msg}\n\n---\n\n"
        return transcript

    def save_debate_log(self):
        """Save the filtered debate log to a markdown file."""
        if not self.debate_buffer:
            return None
            
        debate_path = self.log_file_path.replace(".log", "_debate.md")
        try:
            with open(debate_path, "w", encoding="utf-8") as f:
                f.write(f"# 💬 Analyst Debate Log\n")
                f.write(f"**Ticker:** {ticker} | **Date:** {target_date}\n\n---\n\n")
                f.write(self.get_debate_transcript())     
            return debate_path
        except Exception as e:
            return None

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
            final_state, decision = ta.propagate(ticker, target_date.strftime("%Y-%m-%d"))
            
            status_placeholder.success("✅ Analysis Complete!")
            
            # Restore stdout immediately after success
            sys.stdout = original_stdout
            
            # Save Debate Log
            debate_log_path = capture.save_debate_log()

            # Display Results
            st.divider()
            
            # 1. Final Decision
            st.subheader("📊 Final Decision")
            if isinstance(decision, dict) and "decision" in decision:
                 final_decision = decision["decision"]
            else:
                 # Clean up string decision (remove markdown bold if present)
                 final_decision = str(decision).replace("**", "").replace("FINAL TRANSACTION PROPOSAL:", "").strip()
            
            st.info(f"### Decision: {final_decision}")
            
            # 2. Debate Transcript
            st.subheader("💬 Analyst Debate Transcript")
            with st.container(height=500):
                st.markdown(capture.get_debate_transcript())

            # 3. Verified Sources (Fact Checker Results)
            if final_state and "investment_debate_state" in final_state:
                state_data = final_state["investment_debate_state"]
                
                # 3-A. Recalled Memories (Obsidian)
                if "recalled_memories" in state_data:
                    st.subheader("🧠 Recalled Memories (RAG)")
                    memories = state_data["recalled_memories"]
                    
                    if memories:
                        st.caption("Past insights retrieved from your Obsidian Vault that influenced this decision.")
                        for i, mem in enumerate(memories):
                            similarity = mem.get('similarity_score', 0)
                            # Extract title from 'matched_situation' if format is 'Note Title: ...'
                            situation_text = mem['matched_situation']
                            title = "Past Situation"
                            if "Note Title:" in situation_text:
                                try:
                                    title = situation_text.split("Note Title:")[1].split("\n")[0].strip()
                                except:
                                    pass
                            
                            with st.expander(f"📄 {title} (Similarity: {similarity:.1%})"):
                                st.markdown(f"**Context:**\n{situation_text[:200]}...")
                                st.markdown(f"**Insight/Advice:**\n{mem['recommendation']}")
                    else:
                        st.info("No similar past memories found in Obsidian for this situation.")
                else:
                    # Fallback for debugging (Should not happen if code is updated)
                    st.warning("⚠️ Agent did not return memory data. (Check Research Manager)")

                # 3-B. Verified Sources
                if "verified_urls" in state_data and state_data["verified_urls"]:
                    st.subheader("✅ Verified Sources & Fact Check")
                    st.caption("URLs verified by Fact Checker via direct connection test.")
                    
                    verified_urls = state_data["verified_urls"]
                    st.dataframe(
                        verified_urls, 
                        column_config={
                            "url": st.column_config.LinkColumn("Source URL"),
                            "status": "Verification Status",
                            "source": "Source Agent"
                        },
                        use_container_width=True,
                        hide_index=True
                    )

            # 4. Generate and Display AI Summary
            st.subheader("📝 AI Analysis Summary")
            with st.spinner("✍️ Writing final report based on agent debates..."):
                logs = capture.get_logs()
                summary = generate_summary(logs, model_name)
                st.markdown(summary)
                
                # Save summary to a separate file
                try:
                    summary_path = log_path.replace(".log", "_summary.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(f"# Analysis Summary for {ticker} ({date_str})\n\n")
                        f.write(f"**Final Decision: {final_decision}**\n\n")
                        f.write(summary)
                    
                    st.success("Analysis artifacts saved successfully:")
                    st.write(f"- 📄 **Raw Logs:** `{log_path}`")
                    if debate_log_path:
                        st.write(f"- 💬 **Debate Log:** `{debate_log_path}`")
                    st.write(f"- 📝 **Summary Report:** `{summary_path}`")
                    
                except Exception as save_e:
                    st.warning(f"Could not save summary file: {str(save_e)}")

                # Save to Obsidian if enabled
                if enable_obsidian_save and obsidian_path and os.path.exists(obsidian_path):
                    try:
                        # Initialize memory to use save function
                        mem = ta.invest_judge_memory
                        
                        # Save Summary
                        summary_filename = f"{ticker}_{date_str}_Summary.md"
                        summary_content = f"# Analysis Summary for {ticker} ({date_str})\n\n**Final Decision: {final_decision}**\n\n{summary}"
                        success, msg = mem.save_to_obsidian(summary_content, summary_filename, obsidian_path)
                        
                        # Save Debate Log
                        debate_filename = f"{ticker}_{date_str}_Debate.md"
                        debate_content = f"# 💬 Analyst Debate Log\n**Ticker:** {ticker} | **Date:** {target_date}\n\n---\n\n{capture.get_debate_transcript()}"
                        mem.save_to_obsidian(debate_content, debate_filename, obsidian_path)
                        
                        if success:
                            st.info(f"💎 Saved reports to Obsidian Vault: `{obsidian_path}/TradingAgents/Reports`")
                        else:
                            st.warning(f"Obsidian save failed: {msg}")
                            
                    except Exception as e:
                        st.warning(f"Failed to save to Obsidian: {str(e)}")

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
