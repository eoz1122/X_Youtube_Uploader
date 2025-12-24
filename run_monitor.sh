#!/bin/bash

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

while true; do
    echo "----------------------------------------------------------------" >> monitor.log
    echo "[$(date)] Starting Twitter Upload Bot..." >> monitor.log
    
    # Run the Python script
    python3 yt_to_twitter.py >> output.log 2>&1
    
    EXIT_CODE=$?
    echo "[$(date)] Bot stopped/crashed with exit code $EXIT_CODE. Restarting in 10 seconds..." >> monitor.log
    
    # Wait before restarting to prevent rapid looping if there's a startup error
    sleep 10
done
