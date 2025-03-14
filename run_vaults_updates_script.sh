#!/bin/bash

# Redirect all output (stdout and stderr) to a log file
exec > >(tee -a /root/hyperliquid-analysis/script_vaults_updates_output.log) 2>&1

echo "Starting script at $(date)" # Log the start time
cd /root/hyperliquid-analysis || { echo "Failed to change directory"; exit 1; }
echo "Changed to directory: $(pwd)"

source venv/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }
echo "Activated virtual environment"

echo "Running Python script"
python get_vaults_updates.py || { echo "Python script failed"; exit 1; }

echo "Script finished at $(date)"
