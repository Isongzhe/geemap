import geopandas as gpd
import rioxarray
import yaml
import os

def inspect_watershed(path):
    print(f"\n--- Inspecting Watershed: {path} ---")
    try:
        gdf = gpd.read_file(path, rows=1)
        print(f"CRS: {gdf.crs}")
        print(f"Columns: {list(gdf.columns)}")
        print(f"First Row: {gdf.iloc[0].to_dict()}")
        
        # Get full count
        # gdf_full = gpd.read_file(path, ignore_geometry=True) 
        # print(f"Total Rows: {len(gdf_full)}")
    except Exception as e:
        print(f"Error inspecting shapefile: {e}")

def inspect_raster(path, name):
    print(f"\n--- Inspecting Raster: {name} ({path}) ---")
    try:
        with rioxarray.open_rasterio(path) as src:
            print(f"Shape: {src.rio.shape} (Count, Height, Width)")
            print(f"CRS: {src.rio.crs}")
            print(f"Resolution: {src.rio.resolution()}")
            print(f"Bounds: {src.rio.bounds()}")
            print(f"Dtypes: {src.dtype}")
            print(f"Attributes: {src.attrs}")
            if hasattr(src, "long_name"): 
                print(f"Long Name: {src.long_name}")
            # print(f"Band Descriptions: {src.descriptions}") 
            # some drivers don't populate descriptions well, check attrs
    except Exception as e:
        print(f"Error inspecting raster: {e}")

if __name__ == "__main__":
    with open("dataset/config.yaml", "r") as f:
        config = yaml.safe_load(f)
        
    inspect_watershed(config["watershed"]["path"])
    inspect_raster(config["model"]["input_path"], "Model Input")
    inspect_raster(config["model"]["output_path"], "Model Output")
