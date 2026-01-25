"""
Utility functions for Step 2: Flood Visualization.

This module provides helper functions for file discovery and data loading
based on event dates.
"""

from pathlib import Path
from typing import Optional


def find_event_input(event_date: str, input_folder: str) -> Optional[Path]:
    """
    Find Sentinel-2 input file for the given event date.
    
    Args:
        event_date: Event date (e.g., "2024-04-13")
        input_folder: Folder containing S2 files
    
    Returns:
        Path to input file, or None if not found
    
    Example:
        >>> find_event_input("2024-04-13", "/path/to/data/")
        Path("/path/to/data/S2_2024-04-13_LL_68.97_54.85_UR_69.17_55.02.tif")
    """
    folder = Path(input_folder)
    if not folder.exists():
        print(f"[STEP2] Input folder not found: {input_folder}")
        return None
    
    # Search for files matching the event date pattern
    matches = list(folder.glob(f"S2_{event_date}_*.tif"))
    
    if not matches:
        print(f"[STEP2] No input file found for event {event_date}")
        return None
    
    if len(matches) > 1:
        print(f"[STEP2] Multiple input files found for event {event_date}, using first: {matches[0].name}")
    
    print(f"[STEP2] Found input file: {matches[0].name}")
    return matches[0]


def find_event_output(event_date: str, output_folder: str) -> Optional[Path]:
    """
    Find EDL prediction output for the given event date.
    
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
    
    # Search for .tif output files (prediction results)
    matches = list(folder.glob(f"S2_{event_date}_*_EDL.tif"))
    
    if not matches:
        print(f"[STEP2] No output file found for event {event_date}")
        return None
    
    if len(matches) > 1:
        print(f"[STEP2] Multiple output files found for event {event_date}, using first: {matches[0].name}")
    
    print(f"[STEP2] Found output file: {matches[0].name}")
    return matches[0]
