import rioxarray
import xarray as xr
import numpy as np
import os
import yaml
import rasterio
from rasterio.enums import Resampling

# Load Config
with open("dataset/config.yaml", "r") as f:
    config = yaml.safe_load(f)

INPUT_PATH = config["model"]["input_path"]
OUTPUT_PATH = config["model"]["output_path"]

CACHE_DIR = "dataset/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

OPT_INPUT = os.path.join(CACHE_DIR, "optimized_input.tif")
OPT_CLASS = os.path.join(CACHE_DIR, "optimized_class_rgb.tif")
OPT_UNCERTAINTY = os.path.join(CACHE_DIR, "optimized_uncertainty.tif")
OPT_UNC_MASK = os.path.join(CACHE_DIR, "optimized_uncertainty_mask.tif")
OPT_CLASS_RAW = os.path.join(CACHE_DIR, "optimized_class_raw.tif")

FACTOR = 4  # Downsample factor

def add_overviews(path, resampling_method=Resampling.nearest):
    """Adds overviews (pyramids) to the GeoTIFF for faster tile serving."""
    try:
        print(f"   Building overviews for {os.path.basename(path)}...")
        with rasterio.open(path, 'r+') as dst:
            dst.build_overviews([2, 4, 8, 16], resampling_method)
            dst.update_tags(ns='rio_overview', resampling=resampling_method.name)
    except Exception as e:
        print(f"   Warning: Failed to build overviews: {e}")

def optimize_input():
    if os.path.exists(OPT_INPUT):
        print(f"Cached Input found: {OPT_INPUT}")
        return

    print("Optimizing Input (Resampling)...")
    with rioxarray.open_rasterio(INPUT_PATH) as src:
        # Downsample
        new_width = src.rio.width // FACTOR
        new_height = src.rio.height // FACTOR
        
        downsampled = src.rio.reproject(
            src.rio.crs,
            shape=(new_height, new_width),
            resampling=1 # Bilinear
        )
        
        # Keep only RGB bands (Sentinel-2 usually B4, B3, B2 are indices 3, 2, 1)
        rgb = downsampled.isel(band=[3, 2, 1])
        
        # Clear attributes to prevent "long_name" mismatch error
        rgb.attrs = {}
        
        # Save
        rgb.rio.to_raster(OPT_INPUT, compress='LZW')
        print(f"Saved Optimized Input: {OPT_INPUT}")
        add_overviews(OPT_INPUT, Resampling.average)

def optimize_output():
    
    print("Optimizing Output (Colorizing & Splitting)...")
    with rioxarray.open_rasterio(OUTPUT_PATH) as src:
        # Clear attributes from source immediately to avoid propagation issues
        src.attrs = {} 
        
        new_width = src.rio.width // FACTOR
        new_height = src.rio.height // FACTOR
        
        # Resample Nearest for Classification (Discrete)
        downsampled_nearest = src.rio.reproject(
            src.rio.crs,
            shape=(new_height, new_width),
            resampling=0 # Nearest
        )
        
        # Band 1: Classification (0-4)
        print("   Processing Classification Band (Pastel Colors)...")
        class_band = downsampled_nearest.isel(band=0).values
        
        # Save Raw (0-4) for Dynamic Toggling
        # Ensure 3D shape (1, H, W) for DataArray
        raw_3d = np.expand_dims(class_band, axis=0)
        da_raw = xr.DataArray(
            raw_3d,
            coords={'band': [1], 'y': downsampled_nearest.y, 'x': downsampled_nearest.x},
            dims=('band', 'y', 'x')
        )
        da_raw.rio.write_crs(src.rio.crs, inplace=True)
        da_raw.rio.write_nodata(0, inplace=True) 
        da_raw.rio.to_raster(OPT_CLASS_RAW, compress='LZW')
        print(f"Saved Optimized Raw Class: {OPT_CLASS_RAW}")
        add_overviews(OPT_CLASS_RAW, Resampling.nearest)
        
        # Create RGB
        # 0: Black, 1: Gray, 2: Blue, 3: White, 4: Red
        # Detailed Palette (Softer/Pastel):
        # 0: Transparent/Black (0,0,0)
        # 1: Light Gray (220, 220, 220) - Land
        # 2: Soft Blue (100, 149, 237) - Water (CornflowerBlue)
        # 3: White (255, 255, 255) - Cloud
        # 4: Soft Red (255, 99, 71) - Flood (Tomato)
        h, w = class_band.shape
        rgb_out = np.zeros((3, h, w), dtype=np.uint8)
        
        colors = {
            0: (0, 0, 0),       
            1: (200, 200, 200), 
            2: (100, 149, 237), 
            3: (255, 255, 255), 
            4: (255, 99, 71)   
        }
        
        for val, (r, g, b) in colors.items():
            mask = (class_band == val)
            rgb_out[0][mask] = r
            rgb_out[1][mask] = g
            rgb_out[2][mask] = b

        da_rgb = xr.DataArray(
            rgb_out,
            coords={'band': [1, 2, 3], 'y': downsampled_nearest.y, 'x': downsampled_nearest.x},
            dims=('band', 'y', 'x')
        )
        da_rgb.rio.write_crs(src.rio.crs, inplace=True)
        da_rgb.rio.write_nodata(0, inplace=True) 
        
        da_rgb.rio.to_raster(OPT_CLASS, compress='LZW')
        print(f"Saved Optimized Classification: {OPT_CLASS}")
        
        # Band 2: Uncertainty Logic (Mask)
        print("   Processing Uncertainty Mask (RGBA)...")
        downsampled_bilinear = src.rio.reproject(
            src.rio.crs,
            shape=(new_height, new_width),
            resampling=1 # Bilinear
        )
        unc_val = downsampled_bilinear.isel(band=1).values
        
        # Create RGBA (4 bands)
        # We'll use a "Warning Pattern" (e.g. Yellow tint)
        mask_rgba = np.zeros((4, h, w), dtype=np.uint8)
        
        # RGB = Yellow (255, 255, 0) for visibility
        mask_rgba[0, :, :] = 255
        mask_rgba[1, :, :] = 255
        mask_rgba[2, :, :] = 0
        
        # Alpha based on Logic
        # < 0.2 : Transparent (Trusted)
        # 0.2 - 0.8 : Semi-transparent (Warning)
        # > 0.8 : More Opaque (Untrustworthy)
        alpha = np.zeros((h, w), dtype=np.uint8)
        alpha[unc_val >= 0.2] = 80  # Light warning
        alpha[unc_val >= 0.8] = 180 # Strong warning
        
        mask_rgba[3, :, :] = alpha
        
        da_mask = xr.DataArray(
            mask_rgba,
            coords={'band': [1, 2, 3, 4], 'y': downsampled_nearest.y, 'x': downsampled_nearest.x},
            dims=('band', 'y', 'x')
        )
        da_mask.rio.write_crs(src.rio.crs, inplace=True)
        da_mask.rio.to_raster(OPT_UNC_MASK, compress='LZW')
        print(f"Saved Uncertainty Mask: {OPT_UNC_MASK}")
        
        # Save Raw Uncertainty (Float) for standard visualization
        print("   Processing Uncertainty Band (Float)...")
        # Reuse bilinear downsampled data
        unc_band = downsampled_bilinear.isel(band=1)
        unc_band.rio.to_raster(OPT_UNCERTAINTY, compress='LZW')
        print(f"Saved Optimized Uncertainty: {OPT_UNCERTAINTY}")
        add_overviews(OPT_UNCERTAINTY, Resampling.average) # Average for float

if __name__ == "__main__":
    optimize_input()
    optimize_output()
