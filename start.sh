#!/bin/bash
SESSION="geemap"

echo "Cleaning up..."
PORTS="8765 7777 7778 7779"
for port in $PORTS; do
    echo "   Stopping process on port $port..."
    fuser -k -n tcp $port 2>/dev/null
done
# Wait for ports to release
sleep 2

# Kill existing tmux session if it exists
tmux kill-session -t $SESSION 2>/dev/null

# Create new session
echo "Starting new session..."
tmux new-session -d -s $SESSION -n "solara"

# Start Tile Servers
# Unified Data Server (7777)
tmux new-window -t $SESSION:1 -n "server"
tmux send-keys -t $SESSION:server "uv run python src/step2/unified_server.py" C-m

# Start Solara Step 2
tmux send-keys -t $SESSION:solara "export PYTHONUNBUFFERED=1" C-m
# Using --host 0.0.0.0 to ensure remote access
tmux send-keys -t $SESSION:solara "uv run solara run src/main.py --host=0.0.0.0 --port=8765" C-m

echo "tmux session '$SESSION' started."

echo "========================================================"
echo "PLEASE CONFIGURE PORT FORWARDING ON YOUR LOCAL MACHINE:"
echo "1. Port 8765 : Solara UI"
echo "2. Port 7777 : Data Server (Unified)"
echo "========================================================"
echo ""
echo "To view logs/attach:   tmux attach -t $SESSION"
echo "To stop everything:    ./stop.sh"
