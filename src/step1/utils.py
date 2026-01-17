import geopandas as gpd
import rioxarray
import yaml
import os
from shapely.geometry import box

def load_config():
    with open("dataset/config.yaml", "r") as f:
        return yaml.safe_load(f)

def get_candidate_watersheds():
    """
    Finds watersheds that intersect with the input Sentinel-2 image.
    Returns:
        gdf (GeoDataFrame): Filtered watersheds.
        bounds (tuple): Image bounds (minx, miny, maxx, maxy) in EPSG:4326.
    """
    config = load_config()
    input_path = config["model"]["input_path"]
    shp_path = config["watershed"]["path"]
    
    # 1. Get Image Bounds
    print(f"Reading bounds from {os.path.basename(input_path)}...")
    with rioxarray.open_rasterio(input_path) as src:
        # Reproject bounds to EPSG:4326 if needed
        # rioxarray bounds are in native CRS
        # We need to transform them to 4326 to match shapefile (usually 4326)
        # OR transform shapefile to match raster.
        # Ideally, we work in 4326 for Leaflet compatibility.
        
        # Get bounds in 4326
        # Reprojecting the whole raster is slow, just reproject bounds.
        from pyproj import Transformer
        
        src_crs = src.rio.crs
        dst_crs = "EPSG:4326"
        
        bounds_native = src.rio.bounds() # (left, bottom, right, top)
        
        # Transform bounds
        transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
        minx, miny = transformer.transform(bounds_native[0], bounds_native[1])
        maxx, maxy = transformer.transform(bounds_native[2], bounds_native[3])
        
        # Handle flipped coordinates if any (e.g. south up)
        minx, maxx = sorted((minx, maxx))
        miny, maxy = sorted((miny, maxy))
        
        bounds_4326 = (minx, miny, maxx, maxy)
        print(f"Image Bounds (4326): {bounds_4326}")

    # 2. visual bbox for map
    image_bbox = box(minx, miny, maxx, maxy)
    
    # 3. Load & Filter Shapefile
    print(f"Filtering watersheds from {os.path.basename(shp_path)}...")
    # Use cx for spatial indexing (fast)
    # Note: cx takes [minx:maxx, miny:maxy]
    # We read mainly the relevant chunk.
    # However, cx works on an ALREADY loaded GDF usually? 
    # geopandas.read_file with bbox is supported! This is fastest.
    
    gdf = gpd.read_file(shp_path, bbox=bounds_4326)
    
    print(f"Found {len(gdf)} intersecting watersheds.")
    return gdf, bounds_4326

def save_selected_watershed(hybas_id):
    """Updates config.yaml with the selected ID."""
    config = load_config()
    config["watershed"]["default_id"] = int(hybas_id)
    
    with open("dataset/config.yaml", "w") as f:
        yaml.safe_dump(config, f)
    print(f"Updated config with Watershed ID: {hybas_id}")
