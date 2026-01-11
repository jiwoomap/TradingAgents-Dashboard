#!/usr/bin/env python3
"""
Standalone scheduler daemon that runs independently of Streamlit app.
Usage:
    python run_scheduler.py          # Run in foreground
    python run_scheduler.py &        # Run in background
    python run_scheduler.py stop     # Stop the daemon
"""
import os
import sys
import signal
import time
from datetime import datetime
from scheduler_service import AnalysisScheduler

# PID file to track running process
PID_FILE = "scheduler.pid"

def save_pid():
    """Save current process ID to file."""
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def load_pid():
    """Load process ID from file."""
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return None

def remove_pid():
    """Remove PID file."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def is_running():
    """Check if scheduler is already running."""
    pid = load_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # Check if process exists
        return True
    except OSError:
        return False

def stop_scheduler():
    """Stop the running scheduler daemon."""
    pid = load_pid()
    if pid is None:
        print("No PID file found. Scheduler may not be running.")
        return False

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to process {pid}")

        # Wait for process to stop
        for i in range(10):
            try:
                os.kill(pid, 0)
                time.sleep(0.5)
            except OSError:
                print("Scheduler stopped successfully")
                remove_pid()
                return True

        # Force kill if still running
        print("Process did not stop gracefully, forcing...")
        os.kill(pid, signal.SIGKILL)
        remove_pid()
        return True
    except OSError as e:
        print(f"Error stopping scheduler: {e}")
        remove_pid()
        return False

def signal_handler(signum, frame):
    """Handle termination signals."""
    print(f"\n[{datetime.now()}] Received signal {signum}, shutting down...")
    remove_pid()
    sys.exit(0)

def run_scheduler():
    """Run the scheduler daemon."""
    # Check if already running
    if is_running():
        print("Scheduler is already running!")
        print(f"PID: {load_pid()}")
        print("Use 'python run_scheduler.py stop' to stop it first.")
        sys.exit(1)

    # Save PID
    save_pid()
    print(f"[{datetime.now()}] Scheduler daemon started (PID: {os.getpid()})")
    print(f"PID saved to {PID_FILE}")

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize scheduler
    scheduler = AnalysisScheduler()

    # List current jobs
    jobs = scheduler.list_jobs()
    print(f"[{datetime.now()}] Found {len(jobs)} scheduled job(s)")
    for job in jobs:
        print(f"  - {job['ticker']}: {job['schedule']} (Next run: {job['next_run']})")

    print(f"[{datetime.now()}] Scheduler is running. Press Ctrl+C to stop.")
    print(f"[{datetime.now()}] Logs will be saved to logs/ directory")

    try:
        # Keep running forever
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Keyboard interrupt received, shutting down...")
    finally:
        remove_pid()

def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        stop_scheduler()
    else:
        run_scheduler()

if __name__ == "__main__":
    main()
