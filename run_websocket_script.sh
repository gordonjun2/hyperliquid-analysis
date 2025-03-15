#!/bin/bash

# Redirect all output (stdout and stderr) to a log file
exec > >(tee -a /root/hyperliquid-analysis/script_websocket_output.log) 2>&1

# Activate the virtual environment
source venv/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }
echo "Activated virtual environment"

# Run Python script in the background and log the output
echo "Running Python script"
nohup python run_websocket.py >> /root/hyperliquid-analysis/script_websocket_output.log 2>&1 &

# Ensure the background process is running properly
disown

echo "Python script is running in the background. Logs will be available in script_output.log"

