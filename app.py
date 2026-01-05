import streamlit as st
import sys
import os
import io
import threading
import traceback
import re
from datetime import datetime
from openai import OpenAI
import requests

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

from tradingagents.agents.utils.memory import FinancialSituationMemory

# Load environment variables
load_dotenv()

def search_ticker_suggestions(query):
    """Fetch ticker suggestions from Yahoo Finance API."""
    if not query or len(query) < 2:
        return []
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        # Return list of formatted strings: "SYMBOL | NAME (EXCHANGE)"
        return [f"{item['symbol']} | {item.get('shortname', '')} ({item.get('exchange', '')})" 
                for item in data.get('quotes', []) if 'symbol' in item]
    except Exception:
        return []

st.set_page_config(page_title="TradingAgents Dashboard", layout="wide")

st.title("🤖 TradingAgents: AI Financial Analyst")
st.markdown("LLM Agents collaborate to analyze stocks and provide trading recommendations.")

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    
    st.subheader("📊 Select Asset")
    
    # 2. Integrated Smart Ticker Input
    if 'ticker' not in st.session_state:
        st.session_state.ticker = "NVDA"

    # Main Input Box
    user_input = st.text_input("Asset (Ticker or Name)", 
                              value=st.session_state.ticker,
                              placeholder="Search (e.g. Samsung)",
                              help="Search by company name or enter ticker directly.")

    # Search suggestions based on input
    if user_input and user_input.upper() != st.session_state.ticker:
        suggestions = search_ticker_suggestions(user_input)
        if suggestions:
            st.caption("🔍 Suggested results (Click to select):")
            # Show top 3 suggestions as quick-action buttons
            cols = st.columns(1) # Vertical list for better readability in sidebar
            for s in suggestions[:3]:
                symbol = s.split(" | ")[0].strip()
                name = s.split(" | ")[1].strip()
                
                # Auto-convert Korean tickers to Alpha Vantage format (KRX:XXXXXX)
                if symbol.endswith(".KS") or symbol.endswith(".KQ"):
                    clean_code = symbol.split(".")[0]
                    final_ticker = f"KRX:{clean_code}"
                else:
                    final_ticker = symbol

                if st.button(f"🎯 {symbol} | {name[:20]}...", 
                             key=f"btn_{symbol}", 
                             use_container_width=True,
                             help=s): # Show full name on hover
                    st.session_state.ticker = final_ticker
                    st.rerun()
    
    # Final ticker value used for analysis
    ticker = st.session_state.ticker.upper().strip()
    
    # Success indicator for current selection
    st.success(f"Selected: **{ticker}**")
    target_date = st.date_input("Analysis Date", datetime.today())
    
    st.subheader("Model Settings")
    model_name = st.selectbox("LLM Model", ["gpt-4o", "gpt-4o-mini"], index=1)
    debate_rounds = st.slider("Debate Rounds", 1, 5, 2)

    st.subheader("🧠 Knowledge Base (Obsidian)")
    env_vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")
    user_input_path = st.text_input("Vault Path (Local Absolute Path)", value=env_vault_path)
    
    obsidian_path = user_input_path
    is_docker = os.path.exists("/app/obsidian_vault")
    
    if is_docker and user_input_path == env_vault_path:
        obsidian_path = "/app/obsidian_vault"
        st.caption(f"ℹ️ Docker Mode: Local path mounted to `{obsidian_path}`.")
    
    enable_obsidian_save = st.checkbox("Auto-save reports to Obsidian", value=True)
    
    run_btn = st.button("Analyze", type="primary")
    
    if st.button("Sync Memories from Obsidian"):
        if not os.path.exists(obsidian_path):
            st.error(f"Path not found: {obsidian_path}")
        else:
            with st.spinner("Syncing markdown notes..."):
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
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    def write(self, string):
        self._filter_debate_message(string)
        self.output_buffer += string
        if len(self.output_buffer) > 100000:
            self.output_buffer = self.output_buffer[-50000:]
        
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(string)
        except Exception:
            pass
        
        try:
            self.placeholder.code(self.output_buffer[-5000:], language="text")
        except Exception:
            pass
            
    def get_logs(self):
        return self.output_buffer

    def _filter_debate_message(self, text):
        keywords = ["Bull Analyst:", "Bear Analyst:", "[Research Manager Decision]", 
                    "Risky Analyst:", "Safe Analyst:", "Neutral Analyst:", "[Risk Manager Decision]"]
        for keyword in keywords:
            if keyword in text:
                clean_text = text.strip()
                if clean_text:
                    self.debate_buffer.append(clean_text)
                break
    
    def get_debate_transcript(self):
        if not self.debate_buffer:
            return "No debate transcript available."
        transcript = ""
        for msg in self.debate_buffer:
            if "Bull Analyst:" in msg: transcript += f"### 🐂 {msg}\n\n---\n\n"
            elif "Bear Analyst:" in msg: transcript += f"### 🐻 {msg}\n\n---\n\n"
            elif "[Research Manager Decision]" in msg: transcript += f"### 👨‍⚖️ {msg}\n\n---\n\n"
            elif "Risky Analyst:" in msg: transcript += f"### 🚀 {msg}\n\n---\n\n"
            elif "Safe Analyst:" in msg: transcript += f"### 🛡️ {msg}\n\n---\n\n"
            elif "Neutral Analyst:" in msg: transcript += f"### ⚖️ {msg}\n\n---\n\n"
            elif "[Risk Manager Decision]" in msg: transcript += f"### 👮 {msg}\n\n---\n\n"
            else: transcript += f"{msg}\n\n---\n\n"
        return transcript

    def save_debate_log(self):
        if not self.debate_buffer: return None
        debate_path = self.log_file_path.replace(".log", "_debate.md")
        try:
            with open(debate_path, "w", encoding="utf-8") as f:
                f.write(f"# 💬 Analyst Debate Log\n")
                f.write(f"**Ticker:** {ticker} | **Date:** {target_date}\n\n---\n\n")
                f.write(self.get_debate_transcript())     
            return debate_path
        except Exception: return None

def generate_summary(logs, model_name):
    try:
        client = OpenAI()
        prompt = f"You are an expert financial analyst editor. Summarize these execution logs into a structured report with sections for Fundamental, Technical, Sentiment, Risk, and Final Verdict (BUY/SELL/HOLD). Use bullet points. --- LOGS --- {logs[-30000:]}"
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": "You are a helpful financial assistant."}, {"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Failed to generate summary: {str(e)}"

# Main Area
if run_btn:
    if not os.getenv("OPENAI_API_KEY"):
        st.error("⚠️ OPENAI_API_KEY is missing.")
    else:
        current_time = datetime.now()
        date_str = current_time.strftime('%Y-%m-%d')
        time_str = current_time.strftime('%H%M%S')
        log_dir = os.path.join("logs", date_str, ticker)
        log_path = os.path.join(log_dir, f"{time_str}.log")
        os.makedirs(log_dir, exist_ok=True)
        
        st.subheader("📡 Agent Activities & Logs")
        log_container = st.container(height=400)
        log_placeholder = log_container.empty()
        status_placeholder = st.empty()
        status_placeholder.info("🚀 Agents are gathering data and debating...")

        capture = StreamlitOutputCapture(log_placeholder, log_path)
        original_stdout = sys.stdout
        sys.stdout = capture

        try:
            config = DEFAULT_CONFIG.copy()
            config["deep_think_llm"] = model_name
            config["quick_think_llm"] = model_name
            config["max_debate_rounds"] = debate_rounds
            
            ta = TradingAgentsGraph(debug=True, config=config)
            final_state, decision = ta.propagate(ticker, target_date.strftime("%Y-%m-%d"))
            
            status_placeholder.success("✅ Analysis Complete!")
            sys.stdout = original_stdout
            debate_log_path = capture.save_debate_log()

            st.divider()
            st.subheader("📊 Final Decision")
            final_decision = decision["decision"] if isinstance(decision, dict) else str(decision).replace("**", "").strip()
            st.info(f"### Decision: {final_decision}")
            
            st.subheader("💬 Analyst Debate Transcript")
            with st.container(height=500):
                st.markdown(capture.get_debate_transcript())

            if final_state and "investment_debate_state" in final_state:
                state_data = final_state["investment_debate_state"]
                if "recalled_memories" in state_data:
                    st.subheader("🧠 Recalled Memories (RAG)")
                    for i, mem in enumerate(state_data["recalled_memories"]):
                        title = mem['matched_situation'].split("Note Title:")[1].split("\n")[0].strip() if "Note Title:" in mem['matched_situation'] else "Past Situation"
                        with st.expander(f"📄 {title} (Similarity: {mem.get('similarity_score', 0):.1%})"):
                            st.markdown(f"**Insight/Advice:**\n{mem['recommendation']}")

                if "verified_urls" in state_data and state_data["verified_urls"]:
                    st.subheader("✅ Verified Sources & Fact Check")
                    st.dataframe(state_data["verified_urls"], use_container_width=True, hide_index=True)

            st.subheader("📝 AI Analysis Summary")
            with st.spinner("✍️ Writing final report..."):
                logs = capture.get_logs()
                summary = generate_summary(logs, model_name)
                st.markdown(summary)
                
                try:
                    summary_path = log_path.replace(".log", "_summary.md")
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write(f"# Analysis for {ticker} ({date_str})\n**Decision: {final_decision}**\n\n{summary}")
                    st.success(f"Artifacts saved to `{log_dir}`")
                except: pass

                if enable_obsidian_save and obsidian_path and os.path.exists(obsidian_path):
                    try:
                        mem = ta.invest_judge_memory
                        summary_content = f"# Analysis for {ticker}\n**Decision: {final_decision}**\n\n{summary}"
                        mem.save_to_obsidian(summary_content, f"{ticker}_{date_str}_Summary.md", obsidian_path)
                        mem.save_to_obsidian(capture.get_debate_transcript(), f"{ticker}_{date_str}_Debate.md", obsidian_path)
                        st.info(f"💎 Reports saved to Obsidian: `{obsidian_path}/TradingAgents/Reports`")
                    except: pass

        except Exception as e:
            sys.stdout = original_stdout
            st.error(f"Error: {str(e)}")
            st.code(traceback.format_exc())
        finally:
            if sys.stdout != original_stdout: sys.stdout = original_stdout
