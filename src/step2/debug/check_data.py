import os

config_path = 'dataset/config.yaml'

print(f"Reading {config_path} manually...")

paths_to_check = {}

with open(config_path, 'r') as f:
    lines = f.readlines()
    
# Simple heuristic: Look for lines starting with '/' (absolute paths)
for i, line in enumerate(lines):
    line = line.strip()
    if line.startswith('/'):
        # Try to guess what this path is based on previous comment or context
        label = f"Path found at line {i+1}"
        if i > 0 and lines[i-1].strip().startswith('#'):
            label = lines[i-1].strip().lstrip('#').strip()
        elif "imerg" in line:
            label = "IMERG Catalog"
        
        paths_to_check[label] = line

print(f"Found {len(paths_to_check)} paths to check.")

all_valid = True
for label, path in paths_to_check.items():
    exists = os.path.exists(path)
    status = "EXISTS" if exists else "MISSING"
    print(f"[{status}] {label}: {path}")
    if not exists:
        all_valid = False

if all_valid and len(paths_to_check) > 0:
    print("\nAll found paths are valid.")
else:
    print("\nSome paths are missing or no paths found.")
