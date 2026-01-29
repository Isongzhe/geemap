#!/usr/bin/env python3
"""
Merge Level 1 watersheds from all 9 regions into a single Parquet file.

This script creates a global Level 1 background layer for fast loading:
- Combines all 9 HydroBASINS regions (af, ar, as, au, eu, gr, na, sa, si)
- Keeps only HYBAS_ID and geometry columns
- Saves to data/global_lev01.parquet (~9 features, <100KB)

Usage:
    uv run python scripts/merge_level1.py
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import sys
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.step1.utils import load_watersheds, REGION_BBOXES


def merge_level1_watersheds(output_path: str = "data/global_lev01.parquet"):
    """
    Merge all Level 1 watersheds into a single Parquet file.

    Args:
        output_path: Path to save the merged parquet file

    Returns:
        GeoDataFrame with merged Level 1 data
    """
    print("=" * 60)
    print("Merging Level 1 Watersheds from All Regions")
    print("=" * 60)

    regions = list(REGION_BBOXES.keys())
    print(f"Regions to process: {regions}\n")

    gdfs = []
    start_time = time.time()

    for region in regions:
        try:
            print(f"Loading {region}...", end=" ")
            gdf = load_watersheds(region, level=1)

            # Keep only essential columns
            gdf = gdf[['HYBAS_ID', 'geometry']]

            # Add region column for reference
            gdf['region'] = region

            gdfs.append(gdf)
            print(f"✓ {len(gdf)} features")

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    if not gdfs:
        print("\n❌ No data loaded. Exiting.")
        return None

    # Combine all regions
    print(f"\nCombining {len(gdfs)} regions...", end=" ")
    combined = pd.concat(gdfs, ignore_index=True)
    print(f"✓ {len(combined)} total features")

    # Ensure output directory exists
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to Parquet (requires pyarrow)
    print(f"Saving to {output_path}...", end=" ")
    try:
        combined.to_parquet(output_path)
        print("✓")
    except ImportError:
        # Fallback to GeoJSON if pyarrow not available
        geojson_path = output_path.with_suffix('.geojson')
        print(f"\n⚠️  pyarrow not available, using GeoJSON instead: {geojson_path}")
        combined.to_file(geojson_path, driver='GeoJSON')
        output_path = geojson_path
        print("✓")

    # Report statistics
    elapsed = time.time() - start_time
    file_size = output_path.stat().st_size / 1024  # KB

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total features:  {len(combined)}")
    print(f"File size:       {file_size:.1f} KB")
    print(f"Processing time: {elapsed:.2f} seconds")
    print(f"Output file:     {output_path.absolute()}")
    print("=" * 60)

    # Validation
    if file_size > 1024:
        print(f"⚠️  WARNING: File size ({file_size:.1f} KB) exceeds 1MB target")
    else:
        print("✓ File size is within target (<1MB)")

    return combined


def test_load_speed(file_path: str):
    """
    Test loading speed of the generated file (parquet or geojson).

    Args:
        file_path: Path to the file
    """
    print("\n" + "=" * 60)
    print("Testing Load Speed")
    print("=" * 60)

    file_path = Path(file_path)

    # Test 1: Cold load
    start_time = time.time()
    if file_path.suffix == '.parquet':
        gdf = gpd.read_parquet(file_path)
    else:
        gdf = gpd.read_file(file_path)
    load_time_ms = (time.time() - start_time) * 1000

    print(f"Load time:  {load_time_ms:.1f} ms")
    print(f"Features:   {len(gdf)}")
    print(f"Columns:    {list(gdf.columns)}")
    print(f"CRS:        {gdf.crs}")

    if load_time_ms > 100:
        print(f"⚠️  WARNING: Load time ({load_time_ms:.1f} ms) exceeds 100ms target")
    else:
        print("✓ Load time is within target (<100ms)")

    print("=" * 60)


if __name__ == "__main__":
    # Create the merged parquet file
    output_file = "data/global_lev01.parquet"

    gdf = merge_level1_watersheds(output_file)

    if gdf is not None:
        # Test loading speed
        test_load_speed(output_file)

        print("\n✅ Success! You can now use this file in Step 1.")
        print(f"   File location: {Path(output_file).absolute()}")
