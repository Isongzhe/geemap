import rioxarray
import xarray as xr
import numpy as np
import rasterio
from pathlib import Path

def validate_inputs(input_path: str, output_path: str) -> tuple[xr.DataArray, xr.DataArray]:
    """
    Validates and aligns input and output rasters.
    
    Checks:
    1. Existence
    2. CRS Consistency (matches Output to Input if different)
    3. Resolution/Bounds alignment (Resamples Input to match Output grid)
    
    Args:
        input_path: Path to the model input raster (e.g., Satellite Image)
        output_path: Path to the model output raster (e.g., Flood Map + Uncertainty)
        
    Returns:
        tuple: (aligned_input, aligned_output) as xarray DataArrays
    """
    
    print(f"Loading Input: {input_path}")
    rxr_in = rioxarray.open_rasterio(input_path, masked=True)
    
    print(f"Loading Output: {output_path}")
    rxr_out = rioxarray.open_rasterio(output_path, masked=True)
    
    # 1. CRS Check
    if rxr_in.rio.crs != rxr_out.rio.crs:
        print(f"CRS Mismatch detected. Input: {rxr_in.rio.crs}, Output: {rxr_out.rio.crs}")
        print("Reprojecting Input to match Output CRS...")
        rxr_in = rxr_in.rio.reproject_match(rxr_out)
    else:
        print("CRS Validation Passed.")

    # 2. Alignment Check (Bounds & Resolution)
    # We use reproject_match which handles both CRS and Grid alignment
    if not rxr_in.rio.shape == rxr_out.rio.shape or \
       not np.allclose(rxr_in.rio.transform(), rxr_out.rio.transform()):
        print("Grid Alignment Mismatch (Shape or Transform).")
        print("Resampling Input to match Output grid...")
        rxr_in = rxr_in.rio.reproject_match(rxr_out)
    else:
        print("Grid Alignment Validation Passed.")

    return rxr_in, rxr_out

def check_uncertainty_range(da: xr.DataArray) -> xr.DataArray:
    """
    Checks if the DataArray is in the [0, 1] range.
    If max > 1, assumes it might be 0-255 or similar and normalizes.
    This is a heuristic.
    """
    min_val = float(da.min())
    max_val = float(da.max())
    print(f"Value Range Check: min={min_val}, max={max_val}")
    
    if max_val > 1.0:
        print("Data exceeds [0, 1] range. Attempting normalization...")
        # Simple min-max normalization if needed, or just warn?
        # For now, let's normalize by max if it looks like integer data (e.g., 255)
        if max_val <= 255:
             print(f"Normalizing by 255 (assuming 8-bit)...")
             da = da / 255.0
        else:
             print("Warning: Max value > 1.0 and > 255. Normalization strategy unclear. Returning as is.")
    
    return da

if __name__ == "__main__":
    import yaml
    
    # Load config to test
    with open("dataset/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    input_p = config["model"]["input_path"]
    output_p = config["model"]["output_path"]
    
    try:
        data_in, data_out = validate_inputs(input_p, output_p)
        print("\n--- Validation Successful ---")
        print(f"Input Shape: {data_in.shape}")
        print(f"Output Shape: {data_out.shape}")
        
        # Check uncertainty assumption
        # Assuming output file contains uncertainty or probability map
        # Let's inspect bands
        print(f"Output Bands: {data_out.attrs.get('long_name', data_out.coords.get('band', 'Unknown'))}")
        
        # Run range check on output (assuming it's the probability/uncertainty map)
        check_uncertainty_range(data_out)
        
    except Exception as e:
        print(f"\n! Validation Failed: {e}")
