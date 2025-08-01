#!/bin/bash
# Railway startup script

echo "Starting Sleep Agent API Server..."
echo "Port: $PORT"

# Try different methods to start the ADK server
# Method 1: Direct module path
python -m google.adk.servers.api_server sleep_agent.agent:root_agent --host 0.0.0.0 --port $PORT || \
# Method 2: Using adk command with current directory
adk api_server . --host 0.0.0.0 --port $PORT || \
# Method 3: Using module specification
python -c "from sleep_agent.agent import root_agent; from google.adk.servers import api_server; api_server.run(root_agent, host='0.0.0.0', port=$PORT)"