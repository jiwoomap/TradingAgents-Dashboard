import os
import re
import sys
import threading
import time
import traceback
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from croniter import croniter

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from openai import OpenAI

# Job store to persist jobs across restarts (optional, but good for "real" servers)
# For now, we use MemoryJobStore or simple file-based if needed. 
# Streamlit reloads often, so a persistent store is better. 
# We'll use a local SQLite for persistence.

class AnalysisScheduler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AnalysisScheduler, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        import pytz
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        # Set default timezone to UTC
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.UTC
        )
        self.scheduler.start()
        print("Scheduler started with UTC timezone...")

    def add_job(self, ticker, cron_expr, model_name="gpt-4o", debate_rounds=3, obsidian_path=None, enable_obsidian=False):
        """
        Add a job with cron expression.
        cron_expr format: "minute hour day month day_of_week"
        Example: "0 9 * * MON-FRI" = Every weekday at 9 AM
        """
        # Validate cron expression
        if not croniter.is_valid(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        job_id = f"{ticker}_{cron_expr.replace(' ', '_')}"

        # Check if job exists
        if self.scheduler.get_job(job_id):
            raise ValueError("Job already exists")

        # Parse cron expression parts
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 parts: minute hour day month day_of_week")

        minute, hour, day, month, day_of_week = parts

        self.scheduler.add_job(
            func=run_analysis_task,
            trigger='cron',
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            id=job_id,
            name=f"Analyze {ticker}",
            replace_existing=True,
            args=[ticker, model_name, debate_rounds, obsidian_path, enable_obsidian]
        )
        return True, f"Job added: {ticker} @ {cron_expr}"

    def remove_job(self, job_id):
        try:
            self.scheduler.remove_job(job_id)
            return True, "Job removed"
        except Exception as e:
            return False, str(e)

    def get_jobs(self):
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            })
        return jobs

    def list_jobs(self):
        """
        List all jobs with ticker and schedule information for UI display.
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            # Extract ticker from job id (format: TICKER_cron_expr)
            ticker = job.id.split('_')[0]

            # Reconstruct cron expression from job id
            # Format: TICKER_minute_hour_day_month_day_of_week
            parts = job.id.split('_')[1:]
            schedule = ' '.join(parts) if len(parts) == 5 else "Custom"

            jobs.append({
                'id': job.id,
                'ticker': ticker,
                'schedule': schedule,
                'next_run': job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            })
        return jobs

# --- The actual task function running in background ---
def run_analysis_task(ticker, model_name, debate_rounds, obsidian_path, enable_obsidian):
    """
    Standalone function to run analysis and save files.
    Does NOT use streamlit calls.
    """
    print(f"[{datetime.now()}] Starting scheduled analysis for {ticker}")

    current_time = datetime.now()
    date_str = current_time.strftime('%Y-%m-%d')
    time_str = current_time.strftime('%H%M%S')
    log_dir = os.path.join("logs", date_str, ticker)
    log_path = os.path.join(log_dir, f"{time_str}_scheduled.log")
    os.makedirs(log_dir, exist_ok=True)

    # Create status file to indicate job is running
    status_file = os.path.join(log_dir, f"{time_str}_status.json")
    import json
    with open(status_file, "w") as f:
        json.dump({
            "status": "running",
            "ticker": ticker,
            "start_time": current_time.isoformat(),
            "progress": 0
        }, f)

    # Capture stdout to log file
    class FileLogger:
        def __init__(self, filepath):
            self.terminal = sys.stdout
            self.log = open(filepath, "a", encoding="utf-8")
            self.buffer = "" # To store logs for summary

        def write(self, message):
            # self.terminal.write(message) # Optional: print to server console
            self.log.write(message)
            self.buffer += message

        def flush(self):
            # self.terminal.flush()
            self.log.flush()
            
        def get_content(self):
            return self.buffer

        def close(self):
            self.log.close()

    logger = FileLogger(log_path)
    original_stdout = sys.stdout
    sys.stdout = logger

    try:
        # Update status: analyzing
        with open(status_file, "w") as f:
            json.dump({
                "status": "running",
                "ticker": ticker,
                "start_time": current_time.isoformat(),
                "progress": 30,
                "stage": "Analyzing market data..."
            }, f)

        config = DEFAULT_CONFIG.copy()
        config["deep_think_llm"] = model_name
        config["quick_think_llm"] = model_name
        config["max_debate_rounds"] = debate_rounds

        # Run Graph
        ta = TradingAgentsGraph(debug=True, config=config)

        # Check if RAG memory is available (ChromaDB has memories loaded)
        memory_count = ta.invest_judge_memory.situation_collection.count()
        rag_has_memories = memory_count > 0

        final_state, decision = ta.propagate(ticker, date_str)

        final_decision = decision["decision"] if isinstance(decision, dict) else str(decision).replace("**", "").strip()
        print(f"\nFinal Decision: {final_decision}")
        if rag_has_memories:
            print(f"RAG: Used {memory_count} memories from ChromaDB")

        # Update status: generating reports
        with open(status_file, "w") as f:
            json.dump({
                "status": "running",
                "ticker": ticker,
                "start_time": current_time.isoformat(),
                "progress": 70,
                "stage": "Generating reports..."
            }, f)

        # Extract Debate Transcript (Simple logic for background)
        # We re-read the captured log buffer to filter debate parts
        full_log = logger.get_content()
        debate_transcript = _extract_debate_from_log(full_log)

        # Save Debate Log
        debate_path = log_path.replace("_scheduled.log", "_debate.md")
        with open(debate_path, "w", encoding="utf-8") as f:
            f.write(f"# 💬 Scheduled Debate Log\n")
            f.write(f"**Ticker:** {ticker} | **Date:** {date_str}\n\n---\n\n")
            f.write(debate_transcript)

        # Generate Summary
        summary = _generate_summary_task(full_log, model_name)

        # Save Summary Report
        summary_path = log_path.replace("_scheduled.log", "_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"# Scheduled Analysis for {ticker} ({date_str})\n**Decision: {final_decision}**\n\n{summary}")

        # Save to Obsidian if enabled
        obsidian_saved_paths = []
        if enable_obsidian and obsidian_path and os.path.exists(obsidian_path):
            try:
                mem = ta.invest_judge_memory
                summary_content = f"# Scheduled Analysis for {ticker}\n**Decision: {final_decision}**\n\n{summary}"
                summary_filename = f"{ticker}_{date_str}_Summary.md"
                debate_filename = f"{ticker}_{date_str}_Debate.md"
                mem.save_to_obsidian(summary_content, summary_filename, obsidian_path)
                mem.save_to_obsidian(debate_transcript, debate_filename, obsidian_path)
                obsidian_saved_paths = [
                    os.path.join(obsidian_path, "TradingAgents", "Reports", summary_filename),
                    os.path.join(obsidian_path, "TradingAgents", "Reports", debate_filename)
                ]
            except Exception as e:
                print(f"Failed to save to Obsidian: {e}")

        # Update status: completed
        end_time = datetime.now()
        duration = (end_time - current_time).total_seconds()
        with open(status_file, "w") as f:
            json.dump({
                "status": "completed",
                "ticker": ticker,
                "start_time": current_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration": duration,
                "progress": 100,
                "decision": final_decision,
                "rag_enabled": rag_has_memories,
                "rag_memory_count": memory_count if rag_has_memories else 0,
                "obsidian_saved": enable_obsidian and len(obsidian_saved_paths) > 0,
                "obsidian_path": obsidian_path if enable_obsidian else None,
                "obsidian_files": obsidian_saved_paths if obsidian_saved_paths else None,
                "log_files": {
                    "summary": summary_path,
                    "debate": debate_path,
                    "full_log": log_path
                }
            }, f)

    except Exception as e:
        print(f"Error in scheduled task: {e}")
        traceback.print_exc()

        # Update status: failed
        end_time = datetime.now()
        with open(status_file, "w") as f:
            json.dump({
                "status": "failed",
                "ticker": ticker,
                "start_time": current_time.isoformat(),
                "end_time": end_time.isoformat(),
                "error": str(e)
            }, f)
    finally:
        sys.stdout = original_stdout
        logger.close()
        print(f"[{datetime.now()}] Completed scheduled analysis for {ticker}")


def _extract_debate_from_log(text):
    """Helper to clean up log into debate format - extracts full debate messages"""
    lines = text.split('\n')
    transcript = ""

    # Keywords that mark the start of a new speaker
    speaker_keywords = [
        "Bull Analyst:", "Bear Analyst:",
        "Risky Analyst:", "Safe Analyst:", "Neutral Analyst:",
        "[Research Manager Decision]", "[Risk Manager Decision]"
    ]

    current_speaker = None
    current_message = []

    for line in lines:
        # Check if this line starts a new speaker
        is_new_speaker = False
        for keyword in speaker_keywords:
            if keyword in line:
                # Save previous speaker's message if exists
                if current_speaker and current_message:
                    # Join lines and add paragraph spacing
                    message_text = '\n'.join(current_message).strip()
                    # Replace multiple consecutive newlines with double newlines for paragraph breaks
                    message_text = re.sub(r'\n\n+', '\n\n', message_text)
                    transcript += f"{current_speaker}\n\n{message_text}\n\n---\n\n"

                # Start new speaker
                is_new_speaker = True
                current_message = []

                # Format speaker header with emoji
                if "Bull Analyst:" in line:
                    current_speaker = "### 🐂 Bull Analyst"
                elif "Bear Analyst:" in line:
                    current_speaker = "### 🐻 Bear Analyst"
                elif "Risky Analyst:" in line:
                    current_speaker = "### 🚀 Risky Analyst"
                elif "Safe Analyst:" in line:
                    current_speaker = "### 🛡️ Safe Analyst"
                elif "Neutral Analyst:" in line:
                    current_speaker = "### ⚖️ Neutral Analyst"
                elif "[Research Manager Decision]" in line:
                    current_speaker = "### 👨‍⚖️ Research Manager Decision"
                elif "[Risk Manager Decision]" in line:
                    current_speaker = "### 👮 Risk Manager Decision"

                # Extract message after the keyword (same line)
                msg_start = line.find(keyword) + len(keyword)
                first_line_msg = line[msg_start:].strip()
                if first_line_msg:
                    current_message.append(first_line_msg)
                break

        # If not a new speaker and we're collecting a message, add this line
        if not is_new_speaker and current_speaker:
            stripped = line.strip()
            # Stop collecting if we hit certain markers or debug patterns
            skip_patterns = [
                '---',
                'DEBUG',
                '====',  # LangGraph debug markers like "==== Ai Message ===="
                'Tool Calls:',
                'Response:',
            ]
            should_skip = any(stripped.startswith(pattern) for pattern in skip_patterns)

            if stripped and not should_skip:
                current_message.append(stripped)
            elif not stripped and current_message:
                # Empty line - preserve it as paragraph break if previous line exists
                current_message.append('')

    # Don't forget the last speaker
    if current_speaker and current_message:
        # Join lines and add paragraph spacing
        message_text = '\n'.join(current_message).strip()
        # Replace multiple consecutive newlines with double newlines for paragraph breaks
        message_text = re.sub(r'\n\n+', '\n\n', message_text)
        transcript += f"{current_speaker}\n\n{message_text}\n\n---\n\n"

    return transcript if transcript else "No debate content found."

def _generate_summary_task(logs, model_name):
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
