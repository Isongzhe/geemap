import sys
import time
import os
from localtileserver import TileClient

def main():
    if len(sys.argv) < 3:
        print("Usage: python server.py <path> <port>")
        sys.exit(1)
        
    path = sys.argv[1]
    port = int(sys.argv[2])
    
    if not os.path.exists(path):
        print(f"Error: File not found {path}")
        sys.exit(1)
        
    print(f"Starting Tile Server on port {port} for {path}")
    try:
        # Assign to variable to prevent GC
        client = TileClient(path, port=port, host="0.0.0.0", debug=True)
        print(f"Server started. Access at http://localhost:{port}")
        
        # Proper Keep-Alive
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("Stopping server...")
    except Exception as e:
        print(f"Server crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
