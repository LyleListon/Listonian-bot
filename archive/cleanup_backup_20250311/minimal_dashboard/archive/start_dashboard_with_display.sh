#!/bin/bash

# Start Xvfb
Xvfb :99 -screen 0 1280x800x24 &
export DISPLAY=:99

# Wait for Xvfb to start
sleep 2

# Start the dashboard
python start_dashboard.py