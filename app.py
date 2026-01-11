import streamlit as st
import sys
import os
import io
import threading
import traceback
import re
import time
from datetime import datetime
from openai import OpenAI
import requests

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv

from tradingagents.agents.utils.memory import FinancialSituationMemory
from scheduler_service import AnalysisScheduler

# Load environment variables
load_dotenv()

# Initialize Scheduler (Singleton)
@st.cache_resource
def get_scheduler():
    return AnalysisScheduler()

scheduler = get_scheduler()

# Helper Classes and Functions
class StreamlitOutputCapture(io.StringIO):
    def __init__(self, placeholder, log_file_path):
        super().__init__()
        self.placeholder = placeholder
        self.output_buffer = ""
        self.log_file_path = log_file_path
        self.debate_buffer = []
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

    def save_debate_log(self, ticker, target_date):
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

# --- Sidebar: User Inputs ---
with st.sidebar:
    st.header("Configuration")

    st.subheader("📊 Select Asset")

    # Initialize session state for ticker
    if 'ticker' not in st.session_state:
        st.session_state.ticker = "NVDA"

    # Show current selection prominently
    st.markdown(f"### 📌 Selected: `{st.session_state.ticker}`")

    # Main Input Box - no key binding to avoid modification restrictions
    user_input = st.text_input("Search Asset (Ticker or Name)",
                               placeholder="Search (e.g. Samsung)",
                               help="Search by company name or enter ticker directly.")

    # Search suggestions based on input
    if user_input:
        suggestions = search_ticker_suggestions(user_input)
        if suggestions:
            st.caption("🔍 Suggested results (Click to select):")
            # Show top 3 suggestions as quick-action buttons
            for s in suggestions[:3]:
                symbol = s.split(" | ")[0].strip()
                name = s.split(" | ")[1].strip() if " | " in s else ""

                # Auto-convert Korean tickers to Alpha Vantage format (KRX:XXXXXX)
                if symbol.endswith(".KS") or symbol.endswith(".KQ"):
                    clean_code = symbol.split(".")[0]
                    final_ticker = f"KRX:{clean_code}"
                else:
                    final_ticker = symbol

                if st.button(f"**{symbol}** {name}", key=f"btn_{symbol}", use_container_width=True):
                    st.session_state.ticker = final_ticker
                    st.rerun()
        else:
            # If user typed but no suggestions, assume it's a direct ticker input
            if user_input.upper() != st.session_state.ticker:
                st.session_state.ticker = user_input.upper()

    # Ticker variable from session state
    ticker = st.session_state.ticker

    target_date = st.date_input("Target Analysis Date", value=datetime.now())
    model_name = st.selectbox("LLM Model", ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview"], index=0)
    debate_rounds = st.slider("Max Debate Rounds", min_value=1, max_value=5, value=2)

    run_btn = st.button("Analyze", type="primary", use_container_width=True)

    st.divider()
    st.subheader("⏰ Schedule Analyzer")
    st.markdown("Schedule recurring analysis jobs")

    # Initialize session state for timezone
    if 'timezone' not in st.session_state:
        st.session_state.timezone = "UTC"

    # Timezone selector
    timezones = [
        "UTC",
        "Asia/Seoul (KST, UTC+9)",
        "America/New_York (EST, UTC-5)",
        "America/Los_Angeles (PST, UTC-8)",
        "Europe/London (GMT, UTC+0)",
        "Asia/Tokyo (JST, UTC+9)",
        "Asia/Shanghai (CST, UTC+8)",
        "Asia/Hong_Kong (HKT, UTC+8)"
    ]

    selected_tz = st.selectbox(
        "🌍 Timezone",
        timezones,
        index=timezones.index(st.session_state.timezone) if st.session_state.timezone in timezones else 0,
        help="Select timezone for scheduled jobs. All times will be converted to this timezone."
    )

    # Update session state if changed
    if selected_tz != st.session_state.timezone:
        st.session_state.timezone = selected_tz

    # Display current server time in selected timezone
    from datetime import datetime
    import pytz

    # Extract timezone name from display string
    tz_name = selected_tz.split(" ")[0]
    try:
        tz = pytz.timezone(tz_name)
        current_time = datetime.now(tz)
        st.info(f"🕐 Current Time ({tz_name}): **{current_time.strftime('%Y-%m-%d %H:%M:%S')}**")
    except:
        # Fallback to system time if timezone parsing fails
        current_time = datetime.now()
        st.info(f"🕐 Current Server Time: **{current_time.strftime('%Y-%m-%d %H:%M:%S')}**")

    # Initialize session state for schedule ticker
    if 'sched_ticker' not in st.session_state:
        st.session_state.sched_ticker = "NVDA"

    # Show current selection prominently
    st.markdown(f"### 📌 Selected: `{st.session_state.sched_ticker}`")

    # Schedule Ticker Input with Smart Search - no key binding to avoid modification restrictions
    sched_user_input = st.text_input("Search Asset (Ticker or Name)",
                                     placeholder="Search (e.g. Tesla)",
                                     help="Search by company name or enter ticker directly.")

    # Show suggestions if user is typing
    if sched_user_input:
        sched_suggestions = search_ticker_suggestions(sched_user_input)
        if sched_suggestions:
            st.caption("🔍 Suggested results (Click to select):")
            for s in sched_suggestions[:3]:
                symbol = s.split(" | ")[0].strip()
                name = s.split(" | ")[1].strip() if " | " in s else ""

                # Auto-convert Korean tickers to Alpha Vantage format (KRX:XXXXXX)
                if symbol.endswith(".KS") or symbol.endswith(".KQ"):
                    clean_code = symbol.split(".")[0]
                    final_ticker = f"KRX:{clean_code}"
                else:
                    final_ticker = symbol

                if st.button(f"**{symbol}** {name}", key=f"sched_btn_{symbol}", use_container_width=True):
                    st.session_state.sched_ticker = final_ticker
                    st.rerun()
        else:
            # If user typed but no suggestions, assume it's a direct ticker input
            if sched_user_input.upper() != st.session_state.sched_ticker:
                st.session_state.sched_ticker = sched_user_input.upper()

    # Use selected ticker from session state
    sched_ticker = st.session_state.sched_ticker

    with st.form("add_schedule_job"):
        sched_freq = st.selectbox("Frequency", ["Every Day", "Every Week"], index=0)

        # Simple time input with keyboard support (HH:MM format)
        time_input = st.text_input("Time (HH:MM)", value="09:00", placeholder="09:00",
                                   help="Enter time in 24-hour format (e.g., 09:00, 14:30)")

        # Always show day selector, but with help text
        sched_days = st.multiselect("Select Days (for Weekly only)",
                                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                    default=["Monday"],
                                    help="Only used when 'Every Week' is selected")

        # LLM Model selection for scheduled jobs
        sched_model = st.selectbox("LLM Model", ["gpt-4o", "gpt-4o-mini", "o1-mini", "o1-preview"], index=0, key="sched_model")

        # Max Debate Rounds for scheduled jobs
        sched_debate_rounds = st.slider("Max Debate Rounds", min_value=1, max_value=5, value=2, key="sched_debate_rounds")

        sched_submit = st.form_submit_button("➕ Add Schedule")

        if sched_submit:
            try:
                # Parse time input
                try:
                    time_parts = time_input.split(":")
                    if len(time_parts) != 2:
                        st.error("❌ Invalid time format. Use HH:MM (e.g., 09:00)")
                        st.stop()

                    hour = int(time_parts[0])
                    minute = int(time_parts[1])

                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        st.error("❌ Invalid time. Hour must be 0-23, minute must be 0-59")
                        st.stop()
                except ValueError:
                    st.error("❌ Invalid time format. Use HH:MM (e.g., 09:00)")
                    st.stop()

                # Convert selected timezone time to UTC
                import pytz
                from datetime import datetime, time as dt_time

                tz_name = st.session_state.timezone.split(" ")[0]
                try:
                    user_tz = pytz.timezone(tz_name)
                except:
                    user_tz = pytz.UTC

                # Create a datetime in user's timezone
                now = datetime.now(user_tz)
                user_time = user_tz.localize(datetime.combine(now.date(), dt_time(hour, minute)))

                # Convert to UTC
                utc_time = user_time.astimezone(pytz.UTC)
                utc_hour = utc_time.hour
                utc_minute = utc_time.minute

                # Convert to cron expression (in UTC)
                if sched_freq == "Every Day":
                    cron_expr = f"{utc_minute} {utc_hour} * * *"
                    freq_display = f"Every Day at {hour:02d}:{minute:02d} ({tz_name})"
                else:  # Every Week
                    if not sched_days:
                        st.error("❌ Please select at least one day")
                        st.stop()
                    day_map = {"Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED",
                              "Thursday": "THU", "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN"}
                    days_str = ",".join([day_map[d] for d in sched_days])
                    cron_expr = f"{utc_minute} {utc_hour} * * {days_str}"
                    freq_display = f"Every {', '.join(sched_days)} at {hour:02d}:{minute:02d} ({tz_name})"

                # Get Obsidian vault path from environment (always enabled for scheduled jobs)
                env_vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")

                scheduler.add_job(
                    st.session_state.sched_ticker.upper(),
                    cron_expr,
                    model_name=sched_model,
                    debate_rounds=sched_debate_rounds,
                    obsidian_path=env_vault_path if env_vault_path else None,
                    enable_obsidian=True
                )

                st.success(f"✅ Added: {st.session_state.sched_ticker} - {freq_display}")
                st.caption(f"ℹ️ Model: {sched_model} | Debate Rounds: {sched_debate_rounds} | Scheduled to run at {utc_hour:02d}:{utc_minute:02d} UTC")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    st.divider()
    st.subheader("📋 Active Schedules")
    jobs = scheduler.list_jobs()

    if not jobs:
        st.info("No active schedules")
    else:
        for job in jobs:
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    # Parse schedule to human-readable format
                    schedule_parts = job['schedule'].split()
                    if len(schedule_parts) >= 5:
                        utc_minute = schedule_parts[0]
                        utc_hour = schedule_parts[1]
                        days = schedule_parts[4] if len(schedule_parts) > 4 else "*"

                        # Convert UTC time to user's selected timezone
                        import pytz
                        from datetime import datetime, time as dt_time

                        tz_name = st.session_state.timezone.split(" ")[0]
                        try:
                            user_tz = pytz.timezone(tz_name)
                            # Create UTC datetime
                            utc_now = datetime.now(pytz.UTC)
                            utc_time_obj = pytz.UTC.localize(datetime.combine(utc_now.date(), dt_time(int(utc_hour), int(utc_minute))))
                            # Convert to user timezone
                            user_time_obj = utc_time_obj.astimezone(user_tz)
                            display_hour = user_time_obj.hour
                            display_minute = user_time_obj.minute
                            tz_abbr = tz_name.split('/')[-1] if '/' in tz_name else tz_name
                        except:
                            # Fallback to UTC
                            display_hour = int(utc_hour)
                            display_minute = int(utc_minute)
                            tz_abbr = "UTC"

                        # Time-based schedules
                        if days == "*":
                            freq_text = "Every Day"
                        else:
                            # Weekly schedule - convert day codes to readable format
                            day_names = {"MON": "Mon", "TUE": "Tue", "WED": "Wed", "THU": "Thu",
                                       "FRI": "Fri", "SAT": "Sat", "SUN": "Sun"}
                            day_codes = days.split(",")
                            readable_days = ", ".join([day_names.get(d, d) for d in day_codes])
                            freq_text = f"Every {readable_days}"

                        st.markdown(f"**{job['ticker']}** · 🕐 {display_hour:02d}:{display_minute:02d} {tz_abbr} · {freq_text}")
                    else:
                        st.markdown(f"**{job['ticker']}** · {job['schedule']}")

                    # Convert next_run time to user's timezone
                    try:
                        if job['next_run'] != "N/A":
                            # Parse next_run string (format: "YYYY-MM-DD HH:MM:SS")
                            next_run_utc = datetime.strptime(job['next_run'], "%Y-%m-%d %H:%M:%S")
                            next_run_utc = pytz.UTC.localize(next_run_utc)
                            next_run_user_tz = next_run_utc.astimezone(user_tz)
                            next_run_display = next_run_user_tz.strftime(f"%Y-%m-%d %H:%M:%S {tz_abbr}")
                        else:
                            next_run_display = "N/A"
                    except:
                        next_run_display = job['next_run']

                    st.caption(f"Next run: {next_run_display}")
                with col2:
                    if st.button("🗑️", key=f"delete_{job['id']}", use_container_width=True):
                        scheduler.remove_job(job['id'])
                        st.rerun()
                st.divider()

    st.divider()
    st.subheader("🧠 Knowledge Base (Obsidian)")

    # Get local path from env for display
    env_vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "")

    # UI shows the local path (user friendly)
    user_input_path = st.text_input("Vault Path (Local Absolute Path)", value=env_vault_path)

    # Logic to determine the actual internal path to use
    # If running in Docker, we must use the mount point /app/obsidian_vault
    obsidian_path = user_input_path
    is_docker = os.path.exists("/app/obsidian_vault")

    if is_docker and user_input_path == env_vault_path:
        obsidian_path = "/app/obsidian_vault"
        st.caption(f"ℹ️ Docker Mode: Local path `{user_input_path}` is mounted to `{obsidian_path}` inside the container.")
    elif is_docker:
        st.warning("⚠️ You are in Docker mode. Unless you mounted a different volume, custom paths might not work.")

    enable_obsidian_save = st.checkbox("Auto-save reports to Obsidian", value=True)

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

# --- Tab Layout ---
tab1, tab2 = st.tabs(["🚀 Manual Analysis", "⏰ Scheduled Results"])

with tab2:
    st.header("Recent Scheduled Reports")

    # Add a small manual refresh button
    col1, col2, col3 = st.columns([0.5, 3, 6])
    with col1:
        if st.button("🔄", help="Refresh now"):
            st.rerun()
    with col2:
        st.caption("Click to refresh or press F5 to see latest results")
    with col3:
        pass  # Empty space

    # Scan logs directory for scheduled reports
    log_root = "logs"
    if not os.path.exists(log_root):
        st.info("No logs found yet.")
    else:
        # Find all status files and summary files
        report_files = []
        for root, dirs, files in os.walk(log_root):
            for file in files:
                if file.endswith("_status.json"):
                    # Path structure: logs/YYYY-MM-DD/TICKER/HHMMSS_status.json
                    full_path = os.path.join(root, file)
                    try:
                        # Extract info from path
                        parts = full_path.split(os.sep)
                        ticker_str = parts[2]

                        # Read status
                        import json
                        with open(full_path, "r") as f:
                            status_data = json.load(f)

                        # Convert UTC start_time to local timezone for display
                        from datetime import datetime, timezone
                        start_time_str = status_data.get("start_time", "")

                        # Get file time string for file paths (HHMMSS format from filename)
                        file_time_str = file.split("_")[0]  # HHMMSS from filename

                        if start_time_str:
                            # Parse datetime and convert to local timezone for display
                            utc_time = datetime.fromisoformat(start_time_str)
                            # If no timezone info, assume UTC
                            if utc_time.tzinfo is None:
                                utc_time = utc_time.replace(tzinfo=timezone.utc)
                            local_time = utc_time.astimezone()
                            date_str = local_time.strftime("%Y-%m-%d")
                            time_str = local_time.strftime("%H:%M:%S")
                        else:
                            # Fallback to path-based extraction
                            date_str = parts[1]
                            time_str = f"{file_time_str[:2]}:{file_time_str[2:4]}:{file_time_str[4:]}"

                        report_files.append({
                            "date": date_str,
                            "time": time_str,
                            "ticker": ticker_str,
                            "status": status_data.get("status", "unknown"),
                            "progress": status_data.get("progress", 0),
                            "stage": status_data.get("stage", ""),
                            "decision": status_data.get("decision", ""),
                            "duration": status_data.get("duration", 0),
                            "error": status_data.get("error", ""),
                            "summary_path": os.path.join(root, f"{file_time_str}_summary.md"),
                            "debate_path": os.path.join(root, f"{file_time_str}_debate.md"),
                            "rag_enabled": status_data.get("rag_enabled", False),
                            "rag_memory_count": status_data.get("rag_memory_count", 0),
                            "obsidian_saved": status_data.get("obsidian_saved", False),
                            "obsidian_path": status_data.get("obsidian_path"),
                            "obsidian_files": status_data.get("obsidian_files"),
                            "log_files": status_data.get("log_files", {})
                        })
                    except: continue

        # Sort by date/time desc
        report_files.sort(key=lambda x: (x['date'], x['time']), reverse=True)

        if not report_files:
            st.info("No scheduled analysis reports found yet. Add a job from the sidebar!")
        else:
            for report in report_files:
                # Status indicator
                if report['status'] == 'running':
                    status_icon = "🔄"
                    status_text = f"{report['stage']} ({report['progress']}%)"
                    status_color = "🟡"
                elif report['status'] == 'completed':
                    status_icon = "✅"
                    duration_min = int(report['duration'] // 60)
                    duration_sec = int(report['duration'] % 60)
                    status_text = f"Completed in {duration_min}m {duration_sec}s"
                    status_color = "🟢"
                elif report['status'] == 'failed':
                    status_icon = "❌"
                    status_text = f"Failed: {report['error'][:50]}"
                    status_color = "🔴"
                else:
                    status_icon = "❓"
                    status_text = "Unknown"
                    status_color = "⚪"

                with st.expander(f"{status_color} {report['date']} {report['time']} | {report['ticker']} | {status_icon} {status_text}"):
                    # Show progress bar if running
                    if report['status'] == 'running':
                        st.progress(report['progress'] / 100)
                        st.caption(f"Stage: {report['stage']}")

                    # Show decision if completed
                    if report['status'] == 'completed' and report['decision']:
                        st.info(f"**Decision: {report['decision']}**")

                    # Show RAG and file path info
                    if report['status'] == 'completed':
                        info_col1, info_col2 = st.columns(2)
                        with info_col1:
                            if report.get('rag_enabled'):
                                memory_count = report.get('rag_memory_count', 0)
                                rag_status = f"🧠 Enabled ({memory_count} memories)"
                            else:
                                rag_status = "❌ No memories loaded"
                            st.caption(f"**RAG:** {rag_status}")
                        with info_col2:
                            if report.get('log_files'):
                                log_dir = os.path.dirname(report['log_files'].get('summary', ''))
                                st.caption(f"**Log Directory:** `{log_dir}`")

                        # Show Obsidian save status and paths if available
                        if report.get('obsidian_saved') and report.get('obsidian_files'):
                            with st.expander("📁 Saved to Obsidian"):
                                for file_path in report['obsidian_files']:
                                    st.code(file_path, language=None)

                    # Tabs for Summary vs Debate (only if completed)
                    if report['status'] == 'completed':
                        sub_tab1, sub_tab2 = st.tabs(["📝 Summary Report", "💬 Debate Transcript"])

                        with sub_tab1:
                            try:
                                if os.path.exists(report['summary_path']):
                                    with open(report['summary_path'], "r", encoding="utf-8") as f:
                                        st.markdown(f.read())
                                else:
                                    st.warning("Summary not found.")
                            except:
                                st.error("Could not read report file.")

                        with sub_tab2:
                            try:
                                if os.path.exists(report['debate_path']):
                                    with open(report['debate_path'], "r", encoding="utf-8") as f:
                                        st.markdown(f.read())
                                else:
                                    st.warning("Debate transcript not found.")
                            except:
                                st.error("Could not read debate file.")

with tab1:
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
                debate_log_path = capture.save_debate_log(ticker, target_date)

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
