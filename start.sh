#!/bin/bash
SESSION="geemap"

echo "==========================="
echo "STARTING GEEMAP APPLICATION"
echo "==========================="

# 1. Clean up any existing processes
echo ""
echo "Step 1: Cleaning up existing processes..."
./stop.sh

# Wait for cleanup
sleep 2

# 2. Ensure demo cache exists
echo ""
echo "Step 2: Checking demo cache..."
if [ ! -d "/tmp/geemap_demo_cache" ]; then
    echo "Demo cache not found. Generating..."
    uv run scripts/generate_demo_tiles.py
fi

# 3. Start Solara Application (TileClients will be created on first Step 2 access)
echo ""
echo "Step 3: Starting Solara application..."
tmux new-session -d -s $SESSION -n "solara"
tmux send-keys -t $SESSION:solara "export PYTHONUNBUFFERED=1" C-m
tmux send-keys -t $SESSION:solara "export PYTHONPATH=\$(pwd):\$PYTHONPATH" C-m
tmux send-keys -t $SESSION:solara "export SOLARA_AUTORELOAD=false" C-m
tmux send-keys -t $SESSION:solara "uv run solara run src/main.py --host=0.0.0.0 --port=8765 --no-open" C-m

echo ""
echo "========================================================"
echo "APPLICATION STARTED SUCCESSFULLY"
echo "========================================================"
echo ""
echo "Services:"
echo "  - Solara UI:    http://localhost:8765"
echo "  - TileServers:  ports 9100-9104 (5 servers)"
echo ""
echo "Tmux sessions:"
echo "  - geemap:       Main Solara application"
echo "  - geemap_tiles: TileServers (background)"
echo ""
echo "Useful commands:"
echo "  View Solara logs:      tmux attach -t geemap"
echo "  View TileServer logs:  tmux attach -t geemap_tiles"
echo "  Stop all:              ./stop.sh"
echo "========================================================"

echo "========================================================"
