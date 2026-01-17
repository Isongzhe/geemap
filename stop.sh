#!/bin/bash
SESSION="geemap"

tmux has-session -t $SESSION 2>/dev/null

if [ $? == 0 ]; then
  tmux kill-session -t $SESSION
  echo "red🛑 Session '$SESSION' killed."
else
  echo "⚠️  Session '$SESSION' not found. Is it running?"
fi
