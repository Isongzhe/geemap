import yaml
import rioxarray
import matplotlib.pyplot as plt
import numpy as np
import os

# Load Paths
config_path = "dataset/config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

input_path = config["model"]["input_path"]
output_path = config["model"]["output_path"]

print(f"Input: {input_path}")
print(f"Output: {output_path}")

# Setup Plot
fig, axs = plt.subplots(1, 3, figsize=(18, 6))

# 1. Plot Input RGB (Estimate)
try:
    print("Reading Input Raster...")
    with rioxarray.open_rasterio(input_path) as src:
        # Read center chunk to avoid reading entire large file if possible, 
        # but for simplicity/correctness of visualization, let's read the whole thing downsampled.
        # Downsample factor
        scale_factor = 10
        new_width = src.rio.width // scale_factor
        new_height = src.rio.height // scale_factor
        
        # Read bands 4, 3, 2 (Red, Green, Blue for S2 typically)
        # Note: rioxarray/rasterio is 1-indexed for 'bands' usually, but let's check.
        # data = src.read([4, 3, 2], out_shape=(3, new_height, new_width))
        # rioxarray .open_rasterio returns DataArray. .isel can be used.
        # Assuming standard S2: B4=Red, B3=Green, B2=Blue. 
        # In the file, do bands correspond to indices 0?? 1? 
        # Usually src.coords['band'] is 1,2,3...
        
        rgb = src.isel(band=[3, 2, 1]) # 0-based index for B4, B3, B2 (Index 3,2,1 -> Band 4,3,2) ?? 
        # Wait, if bands are 1,2,3...13. Then B4 is index 3.
        # Let's try reading 3 bands.
        
        # Safe read with resampling
        rgb_data = src.rio.reproject(
            src.rio.crs, 
            shape=(new_height, new_width), 
            resampling=0 # Nearest
        ).isel(band=[3, 2, 1]).values # Assuming Index 3=B4, 2=B3, 1=B2
        
        # Normalize for display (0-3000 -> 0-1)
        rgb_data = rgb_data.astype(float)
        rgb_data = np.clip(rgb_data / 3000.0, 0, 1)
        rgb_data = np.transpose(rgb_data, (1, 2, 0)) # CHW -> HWC
        
        axs[0].imshow(rgb_data)
        axs[0].set_title(f"Input RGB (Approx B4,3,2)\nMax Val: {np.max(src.isel(band=3).values)}")
        print("Input Plot Generated.")
        
except Exception as e:
    axs[0].text(0.5, 0.5, f"Error: {e}", ha='center')
    print(f"Input Error: {e}")

# 2. Plot Output Prediction (Band 1)
try:
    print("Reading Output Raster...")
    with rioxarray.open_rasterio(output_path) as src:
        # Band 1 is likely Flood Probability/Class
        # Band 2 is Uncertainty
        scale_factor = 10
        new_width = src.rio.width // scale_factor
        new_height = src.rio.height // scale_factor
        
        # Read Band 1 (Flood)
        flood = src.rio.reproject(
             src.rio.crs, 
            shape=(new_height, new_width), 
            resampling=0
        ).isel(band=0).values # Index 0 = Band 1
        
        im = axs[1].imshow(flood, cmap='Blues', vmin=0, vmax=1.0)
        axs[1].set_title(f"Flood Prediction (Band 1)\nRange: {np.min(flood):.2f} - {np.max(flood):.2f}")
        plt.colorbar(im, ax=axs[1])
        
        # 3. Plot Uncertainty (Band 2)
        unc = src.rio.reproject(
             src.rio.crs, 
            shape=(new_height, new_width), 
            resampling=0
        ).isel(band=1).values # Index 1 = Band 2
        
        im2 = axs[2].imshow(unc, cmap='RdYlGn_r', vmin=0, vmax=1.0)
        axs[2].set_title(f"Uncertainty (Band 2)\nRange: {np.min(unc):.2f} - {np.max(unc):.2f}")
        plt.colorbar(im2, ax=axs[2])
        
        print("Output Plots Generated.")
        
except Exception as e:
    axs[1].text(0.5, 0.5, f"Error: {e}", ha='center')
    print(f"Output Error: {e}")

plt.tight_layout()
plt.savefig("debug_raster_plot.png")
print("Saved debug_raster_plot.png")
