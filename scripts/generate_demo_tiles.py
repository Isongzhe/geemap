#!/usr/bin/env python
"""
Generate pre-tiled versions of demo events for fast rendering.

This script creates symbolic links to the original files and generates
TileClient instances that will be cached and reused during demo.
"""

from pathlib import Path
from localtileserver import TileClient
import json
import shutil

# Demo events
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

def main():
    base_dir = Path(__file__).parent.parent / 'data' / 'tiles'
    base_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔧 Generating demo tiles configuration...")
    
    # Create symlinks or copy files
    for event_date, files in DEMO_EVENTS.items():
        event_dir = base_dir / event_date
        event_dir.mkdir(exist_ok=True)
        
        print(f"\n📅 Processing event: {event_date}")
        
        # Input file
        input_src = Path(files['input'])
        input_dst = event_dir / 'input.tif'
        if input_src.exists():
            if input_dst.exists():
                input_dst.unlink()
            input_dst.symlink_to(input_src)
            print(f"  ✓ Input: {input_src.name} -> {input_dst}")
        else:
            print(f"  ✗ Input not found: {input_src}")
        
        # Output file
        output_src = Path(files['output'])
        output_dst = event_dir / 'output.tif'
        if output_src.exists():
            if output_dst.exists():
                output_dst.unlink()
            output_dst.symlink_to(output_src)
            print(f"  ✓ Output: {output_src.name} -> {output_dst}")
        else:
            print(f"  ✗ Output not found: {output_src}")
    
    # Permanent water (shared)
    water_src = Path(PERMANENT_WATER)
    water_dst = base_dir / 'permanent_water.tif'
    if water_src.exists():
        if water_dst.exists():
            water_dst.unlink()
        water_dst.symlink_to(water_src)
        print(f"\n💧 Permanent water: {water_src.name} -> {water_dst}")
    else:
        print(f"\n✗ Permanent water not found: {water_src}")
    
    print("\n✅ Demo tiles configuration complete!")
    print(f"📁 Files organized in: {base_dir}")
    print("\n⚡ Next: Update app.py to use these local paths for instant loading.")

if __name__ == '__main__':
    main()
