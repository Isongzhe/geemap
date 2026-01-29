#!/bin/bash
SESSION="geemap"

echo "Stopping geemap application..."

# Kill all Python processes (including TileServers)
echo "Killing all Python/Solara processes..."
pkill -f "solara run" 2>/dev/null
pkill -f "start_tileservers.py" 2>/dev/null
pkill -f "localtileserver" 2>/dev/null

# Kill tmux sessions
tmux has-session -t $SESSION 2>/dev/null
if [ $? == 0 ]; then
  tmux kill-session -t $SESSION
  echo "Session '$SESSION' killed."
fi

tmux has-session -t geemap_tiles 2>/dev/null
if [ $? == 0 ]; then
  tmux kill-session -t geemap_tiles
  echo "Session 'geemap_tiles' killed."
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

