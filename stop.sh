#!/bin/bash
SESSION="geemap"

echo "Stopping geemap application..."

# Kill all Python processes (including TileServers managed by app.py)
echo "Killing all Python/Solara processes..."
pkill -f "solara run" 2>/dev/null
pkill -f "localtileserver" 2>/dev/null

# Kill tmux session
tmux has-session -t $SESSION 2>/dev/null
if [ $? == 0 ]; then
  tmux kill-session -t $SESSION
  echo "Session '$SESSION' killed."
fi

# Clean up all ports
echo "Cleaning up ports..."
PORTS="8765 9100 9101 9102 9103 9104"
for port in $PORTS; do
    fuser -k -n tcp $port 2>/dev/null
done

# Wait for cleanup
sleep 1

echo "Cleanup complete."

