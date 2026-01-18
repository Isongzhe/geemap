#!/bin/bash
SESSION="geemap"

echo "Cleaning up..."
PORTS="8765"
for port in $PORTS; do
    echo "   Stopping process on port $port..."
    fuser -k -n tcp $port 2>/dev/null
done
# Wait for ports to release
sleep 2

# Kill existing tmux session if it exists
tmux kill-session -t $SESSION 2>/dev/null

# Create new session and start Solara
echo "Starting new session..."
tmux new-session -d -s $SESSION -n "solara"

# Start Solara Application
tmux send-keys -t $SESSION:solara "export PYTHONUNBUFFERED=1" C-m
# Add project root to PYTHONPATH for absolute imports
tmux send-keys -t $SESSION:solara "export PYTHONPATH=\$(pwd):\$PYTHONPATH" C-m
# Using --host 0.0.0.0 to ensure remote access and container support
tmux send-keys -t $SESSION:solara "uv run solara run src/main.py --host=0.0.0.0 --port=8765" C-m

echo "tmux session '$SESSION' started."

echo "========================================================"
echo "APPLICATION STARTED SUCCESSFULLY"
echo "========================================================"
echo ""
echo "Solara UI is running on port 8765"
echo ""
echo "Using VSCode Dev Container:"
echo "  1. VSCode will auto-forward port 8765 to your local machine"
echo "  2. Check VSCode 'PORTS' tab (next to Terminal)"
echo "  3. Access: http://localhost:8765 in your browser"
echo ""
echo "If port forwarding doesn't appear automatically:"
echo "  - Reload VSCode window (Cmd/Ctrl + Shift + P > Reload Window)"
echo "  - Or manually forward in PORTS tab"
echo ""
echo "========================================================"
echo "Useful commands:"
echo "  View logs:   tmux attach -t $SESSION"
echo "  Stop app:    ./stop.sh"
echo "========================================================"
