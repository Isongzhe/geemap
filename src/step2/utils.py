"""
Utility functions for Step 2: Flood Visualization.

This module provides helper functions for file discovery and data loading
based on event dates, including analog event catalog loading.
"""

from pathlib import Path
from typing import Optional, Dict, List
import pandas as pd


def find_event_input(event_date: str, input_folder: str) -> Optional[Path]:
    """
    Find Sentinel-2 input file for the given event date.

    **Strict S2 Requirement**: Only searches for Sentinel-2 files (S2_ prefix).
    No fallback to other sensors like Landsat.

    Args:
        event_date: Event date (e.g., "2024-04-13")
        input_folder: Folder containing S2 files

    Returns:
        Path to S2 input file, or None if not found

    Example:
        >>> find_event_input("2024-04-13", "/path/to/data/")
        Path("/path/to/data/S2_2024-04-13_LL_68.97_54.85_UR_69.17_55.02.tif")
    """
    folder = Path(input_folder)
    if not folder.exists():
        print(f"[STEP2] Input folder not found: {input_folder}")
        return None

    # DEBUG: Show all files matching the date pattern (both S2 and LS)
    all_matches_with_date = list(folder.glob(f"*{event_date}*.tif"))
    print(f"[STEP2 DEBUG] All files matching date {event_date}: {[f.name for f in all_matches_with_date]}")

    # Search for S2 files only (strict requirement)
    matches = list(folder.glob(f"S2_{event_date}_*.tif"))
    print(f"[STEP2 DEBUG] S2 files matching pattern 'S2_{event_date}_*.tif': {[f.name for f in matches]}")

    if not matches:
        print(f"[STEP2] ❌ No S2 input file found for event {event_date} (strict S2 requirement)")
        return None

    if len(matches) > 1:
        print(f"[STEP2] Multiple S2 input files found for event {event_date}, using first: {matches[0].name}")

    print(f"[STEP2] ✅ Found S2 input file: {matches[0].name}")
    return matches[0]


def find_event_output(event_date: str, output_folder: str) -> Optional[Path]:
    """
    Find EDL prediction output for the given event date.

    **Strict S2 Requirement**: Only searches for Sentinel-2 output files (S2_ prefix).
    No fallback to other sensors like Landsat.

    Args:
        event_date: Event date
        output_folder: Folder containing prediction results

    Returns:
        Path to output file (.tif), or None if not found

    Example:
        >>> find_event_output("2024-04-13", "/path/to/result/")
        Path("/path/to/result/S2_2024-04-13_LL_68.97_54.85_UR_69.17_55.02_output_EDL.tif")
    """
    folder = Path(output_folder)
    if not folder.exists():
        print(f"[STEP2] Output folder not found: {output_folder}")
        return None

    # Search for S2 output files only (strict requirement)
    matches = list(folder.glob(f"S2_{event_date}_*_EDL.tif"))

    if not matches:
        print(f"[STEP2] No S2 output file found for event {event_date} (strict S2 requirement)")
        return None

    if len(matches) > 1:
        print(f"[STEP2] Multiple S2 output files found for event {event_date}, using first: {matches[0].name}")

    print(f"[STEP2] Found S2 output file: {matches[0].name}")
    return matches[0]


def find_event_preview(event_date: str, output_folder: str) -> Optional[Path]:
    """
    Find preview image (PNG) for the given event date.

    **Strict S2 Requirement**: Only searches for Sentinel-2 preview images (S2_ prefix).

    Args:
        event_date: Event date
        output_folder: Folder containing prediction results

    Returns:
        Path to preview PNG file, or None if not found

    Example:
        >>> find_event_preview("2024-04-13", "/path/to/result/")
        Path("/path/to/result/S2_2024-04-13_LL_68.97_54.85_UR_69.17_55.02_output_EDL_prediction.png")
    """
    folder = Path(output_folder)
    if not folder.exists():
        print(f"[STEP2] Output folder not found: {output_folder}")
        return None

    # Search for S2 PNG preview files only (strict requirement)
    matches = list(folder.glob(f"S2_{event_date}_*_EDL_prediction.png"))

    if not matches:
        print(f"[STEP2] No S2 preview image found for event {event_date} (strict S2 requirement)")
        return None

    if len(matches) > 1:
        print(f"[STEP2] Multiple S2 preview images found for event {event_date}, using first: {matches[0].name}")

    print(f"[STEP2] Found S2 preview image: {matches[0].name}")
    return matches[0]


def load_analog_catalog(csv_path: str, top_n: int = 10) -> Optional[pd.DataFrame]:
    """
    Load analog event catalog from CSV file.

    Expected CSV columns: rank, method, datetime, score

    Args:
        csv_path: Path to CSV file containing analog events
        top_n: Number of top-ranked events to return (default: 10)

    Returns:
        DataFrame with analog events, sorted by rank, limited to top_n,
        or None if file not found or loading fails

    Example:
        >>> df = load_analog_catalog("/path/to/analogs.csv", top_n=10)
        >>> df.columns
        Index(['rank', 'method', 'datetime', 'score'], dtype='object')
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"[STEP2] Analog catalog CSV not found: {csv_path}")
        return None

    try:
        df = pd.read_csv(csv_path)

        # Validate required columns
        required_columns = {'rank', 'datetime', 'score'}
        if not required_columns.issubset(df.columns):
            print(f"[STEP2] CSV missing required columns. Expected: {required_columns}, Found: {set(df.columns)}")
            return None

        # Sort by rank and limit to top_n
        df = df.sort_values('rank').head(top_n)

        print(f"[STEP2] Loaded {len(df)} analog events from CSV")
        return df

    except Exception as e:
        print(f"[STEP2] Error loading analog catalog: {e}")
        return None
