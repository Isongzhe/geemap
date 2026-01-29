"""
Compute bounding boxes for all HydroBASINS level 1 regions.

This script scans all level 1 shapefiles and computes their actual
bounding boxes to be used for efficient viewport-based loading.
"""

import geopandas as gpd
from pathlib import Path
import json

# HydroBASINS root directory
HYDRO_ROOT = Path("/home/sungche/NAS/dataset/hydro_basins")

# Region codes (directory names)
REGIONS = ["af", "ar", "as", "au", "eu", "gr", "na", "sa", "si"]

def compute_region_bboxes():
    """
    Compute bounding boxes for all level 1 regions.

    Returns:
        dict: {region_code: (minx, miny, maxx, maxy)}
    """
    bboxes = {}

    for region in REGIONS:
        shp_path = HYDRO_ROOT / region / "shp" / f"hybas_{region}_lev01_v1c.shp"

        if not shp_path.exists():
            print(f"⚠️  {region}: File not found - {shp_path}")
            continue

        try:
            gdf = gpd.read_file(shp_path)
            bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
            bboxes[region] = tuple(map(float, bounds))

            print(f"✓ {region}: {bounds}")
            print(f"   Features: {len(gdf)}")

        except Exception as e:
            print(f"❌ {region}: Error - {e}")

    return bboxes


def format_as_python_dict(bboxes: dict) -> str:
    """
    Format bboxes as Python dictionary code for copy-paste.

    Args:
        bboxes: Dictionary of region bounding boxes

    Returns:
        str: Formatted Python code
    """
    lines = ["region_bboxes = {"]
    for region, (minx, miny, maxx, maxy) in sorted(bboxes.items()):
        lines.append(f"    '{region}': ({minx:.2f}, {miny:.2f}, {maxx:.2f}, {maxy:.2f}),")
    lines.append("}")
    return "\n".join(lines)


if __name__ == "__main__":
    print("Computing HydroBASINS Level 1 Region Bounding Boxes...")
    print("=" * 70)

    bboxes = compute_region_bboxes()

    print("\n" + "=" * 70)
    print(f"✓ Computed {len(bboxes)} region bounding boxes\n")

    # Print Python code for copy-paste
    print("Copy this to src/step1/utils.py:")
    print("-" * 70)
    print(format_as_python_dict(bboxes))
    print("-" * 70)

    # Save as JSON for reference
    output_path = HYDRO_ROOT.parent / "region_bboxes_level1.json"
    with open(output_path, "w") as f:
        json.dump(bboxes, f, indent=2)

    print(f"\n✓ Saved to: {output_path}")
