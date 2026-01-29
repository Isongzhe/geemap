#!/usr/bin/env python
"""
Copy demo event files to local machine for fast rendering.

This script copies demo files from NAS to local /tmp directory
to avoid slow network I/O during demo presentations.
"""

from pathlib import Path
import shutil
import os

# Demo events on NAS
DEMO_EVENTS = {
    '2020-04-18': {
        'input': '/home/NAS/homes/isaac-10009/Data/Sinotech_Hackathon/data/S2_2020-04-18_LL_68.97_54.85_UR_69.17_55.02.tif',
        'output': '/home/NAS/homes/cjchen-10025/ML4FloodsUncertainty/result/hackathon_sinotech/EDL/S2_2020-04-18_LL_68.97_54.85_UR_69.17_55.02_output_EDL.tif',
    },
    '2024-04-20': {
        'input': '/home/NAS/homes/isaac-10009/Data/Sinotech_Hackathon/data/S2_2024-04-20_LL_68.97_54.85_UR_69.17_55.02.tif',
        'output': '/home/NAS/homes/cjchen-10025/ML4FloodsUncertainty/result/hackathon_sinotech/EDL/S2_2024-04-20_LL_68.97_54.85_UR_69.17_55.02_output_EDL.tif',
    }
}

# Permanent water (shared)
PERMANENT_WATER = '/home/NAS/homes/isaac-10009/Data/Sinotech_Hackathon/data/permanent_water_binary_LL_68.97_54.85_UR_69.17_55.02.tif'

# Local cache directory (fast local disk)
LOCAL_CACHE_DIR = Path('/tmp/geemap_demo_cache')

def copy_file_with_progress(src: Path, dst: Path):
    """Copy file and show progress."""
    size_mb = src.stat().st_size / 1024 / 1024
    print(f"  Copying {src.name} ({size_mb:.1f} MB)...")
    shutil.copy2(src, dst)
    print(f"  Done: {dst}")

def main():
    # Create local cache directory
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[DEMO SETUP] Local cache directory: {LOCAL_CACHE_DIR}")
    print(f"[DEMO SETUP] Copying demo files from NAS to local disk...\n")
    
    # Copy demo event files
    for event_date, files in DEMO_EVENTS.items():
        event_dir = LOCAL_CACHE_DIR / event_date
        event_dir.mkdir(exist_ok=True)
        
        print(f"[{event_date}]")
        
        # Input file
        input_src = Path(files['input'])
        input_dst = event_dir / 'input.tif'
        if input_src.exists():
            if not input_dst.exists() or input_dst.stat().st_size != input_src.stat().st_size:
                copy_file_with_progress(input_src, input_dst)
            else:
                print(f"  Skip (already cached): {input_dst.name}")
        else:
            raise FileNotFoundError(f"Input file not found: {input_src}")
        
        # Output file
        output_src = Path(files['output'])
        output_dst = event_dir / 'output.tif'
        if output_src.exists():
            if not output_dst.exists() or output_dst.stat().st_size != output_src.stat().st_size:
                copy_file_with_progress(output_src, output_dst)
            else:
                print(f"  Skip (already cached): {output_dst.name}")
        else:
            raise FileNotFoundError(f"Output file not found: {output_src}")
        
        print()
    
    # Copy permanent water
    print("[Permanent Water]")
    water_src = Path(PERMANENT_WATER)
    water_dst = LOCAL_CACHE_DIR / 'permanent_water.tif'
    if water_src.exists():
        if not water_dst.exists() or water_dst.stat().st_size != water_src.stat().st_size:
            copy_file_with_progress(water_src, water_dst)
        else:
            print(f"  Skip (already cached): {water_dst.name}")
    else:
        raise FileNotFoundError(f"Permanent water file not found: {water_src}")
    
    print(f"\n[DEMO SETUP] All files cached to: {LOCAL_CACHE_DIR}")
    print(f"[DEMO SETUP] Total cache size: {sum(f.stat().st_size for f in LOCAL_CACHE_DIR.rglob('*.tif')) / 1024 / 1024:.1f} MB")
    print(f"\n[DEMO SETUP] Next: Run the app with DEMO_MODE=True to use local cache")

if __name__ == '__main__':
    main()
