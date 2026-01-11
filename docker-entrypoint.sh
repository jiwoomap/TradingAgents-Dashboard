#!/bin/bash
set -e

# Start the background scheduler daemon
echo "Starting scheduler daemon..."
python run_scheduler.py &

# Start Streamlit app in foreground
echo "Starting Streamlit app..."
exec streamlit run app.py --server.address=0.0.0.0
