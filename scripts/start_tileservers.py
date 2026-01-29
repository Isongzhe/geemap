#!/usr/bin/env python
"""
Pre-start TileServers for demo events.

This script starts all TileServers (5 servers total) before the main app:
- 2020-04-18 input (port 9100)
- 2020-04-18 output (port 9101)
- 2024-04-20 input (port 9103)
- 2024-04-20 output (port 9104)
- Permanent water (port 9102)

These servers will stay alive and be reused by the app.
"""

from pathlib import Path
from localtileserver import TileClient
import time

# Demo events from local cache
LOCAL_CACHE_DIR = Path('/tmp/geemap_demo_cache')

SERVERS = {
    '2020-04-18_input': {
        'path': LOCAL_CACHE_DIR / '2020-04-18' / 'input.tif',
        'port': 9100,
    },
    '2020-04-18_output': {
        'path': LOCAL_CACHE_DIR / '2020-04-18' / 'output.tif',
        'port': 9101,
    },
    '2024-04-20_input': {
        'path': LOCAL_CACHE_DIR / '2024-04-20' / 'input.tif',
        'port': 9103,
    },
    '2024-04-20_output': {
        'path': LOCAL_CACHE_DIR / '2024-04-20' / 'output.tif',
        'port': 9104,
    },
    'permanent_water': {
        'path': LOCAL_CACHE_DIR / 'permanent_water.tif',
        'port': 9102,
    },
}

def main():
    print("[TILESERVERS] Starting all TileServers...")
    
    clients = {}
    
    for name, config in SERVERS.items():
        path = config['path']
        port = config['port']
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}\nRun: uv run scripts/generate_demo_tiles.py")
        
        print(f"[TILESERVERS] Starting {name} on port {port}...")
        client = TileClient(
            str(path),
            port=port,
            host='0.0.0.0',
            client_port=port,
            client_host='localhost'
        )
        clients[name] = client
        print(f"[TILESERVERS]   Server URL: {client.server_base_url}")
    
    print(f"\n[TILESERVERS] All {len(clients)} TileServers started successfully!")
    print("[TILESERVERS] Press Ctrl+C to stop all servers...\n")
    
    # Keep servers alive
    try:
        while True:
            time.sleep(60)
            print(f"[TILESERVERS] {len(clients)} servers still running...")
    except KeyboardInterrupt:
        print("\n[TILESERVERS] Shutting down all servers...")
        for name, client in clients.items():
            if hasattr(client, 'shutdown'):
                client.shutdown()
                print(f"[TILESERVERS] Stopped {name}")

if __name__ == '__main__':
    main()
