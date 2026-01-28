import geopandas as gpd
import os
from src.config import load_yaml_config, save_yaml_config, get_watershed_config


def load_config():
    """Wrapper for backward compatibility."""
    return load_yaml_config()

def get_shapefile_path(region: str, level: int) -> str:
    """
    Constructs the shapefile path for a given region and level.

    Args:
        region: Region code (af, ar, as, au, eu, gr, na, sa)
        level: HydroBASINS level (1-12)

    Returns:
        Full path to the shapefile
    """
    config = load_config()
    root_path = config["watershed"]["root_path"]
    level_str = f"{level:02d}"
    filename = f"hybas_{region}_lev{level_str}_v1c.shp"
    return os.path.join(root_path, region, "shp", filename)

def load_watersheds(region: str, level: int) -> gpd.GeoDataFrame:
    """
    Loads watershed shapefile for the given region and level.

    Args:
        region: Region code
        level: HydroBASINS level (1-12)

    Returns:
        GeoDataFrame with watershed polygons
    """
    shp_path = get_shapefile_path(region, level)
    print(f"Loading watersheds from {os.path.basename(shp_path)}...")
    gdf = gpd.read_file(shp_path)
    print(f"Loaded {len(gdf)} watersheds.")
    return gdf

def load_watershed_by_id(hybas_id: int) -> tuple:
    """
    Searches for a watershed by HYBAS_ID across all regions.
    The first digit of HYBAS_ID indicates the region:
    1=Africa, 2=Europe, 3=Siberia, 4=Asia, 5=Australia,
    6=South America, 7=North America, 8=Arctic, 9=Greenland

    Args:
        hybas_id: The HYBAS_ID to search for

    Returns:
        Tuple of (GeoDataFrame with single row, region, level) or (None, None, None) if not found
    """
    # Map first digit to region code
    region_map = {
        '1': 'af',  # Africa
        '2': 'eu',  # Europe
        '3': 'si',  # Siberia
        '4': 'as',  # Asia
        '5': 'au',  # Australia
        '6': 'sa',  # South America
        '7': 'na',  # North America
        '8': 'ar',  # Arctic
        '9': 'gr',  # Greenland
    }

    hybas_str = str(hybas_id)
    if len(hybas_str) != 10:
        print(f"Invalid HYBAS_ID format: {hybas_id}")
        return None, None, None

    first_digit = hybas_str[0]
    level_digits = hybas_str[1:3]

    region = region_map.get(first_digit)
    if not region:
        print(f"Unknown region code: {first_digit}")
        return None, None, None

    try:
        level = int(level_digits)
    except ValueError:
        print(f"Invalid level in HYBAS_ID: {level_digits}")
        return None, None, None

    # Load the shapefile and search
    try:
        gdf = load_watersheds(region, level)
        result = gdf[gdf['HYBAS_ID'] == hybas_id]
        if not result.empty:
            return result, region, level
    except Exception as e:
        print(f"Error loading watershed: {e}")

    return None, None, None

def get_watershed_bounds(gdf: gpd.GeoDataFrame) -> tuple:
    """
    Gets the bounds of a GeoDataFrame in (minx, miny, maxx, maxy) format.

    Args:
        gdf: GeoDataFrame with geometry

    Returns:
        Tuple (minx, miny, maxx, maxy) in EPSG:4326
    """
    bounds = gdf.total_bounds  # returns (minx, miny, maxx, maxy)
    return tuple(bounds)

def calculate_zoom_level(bounds: tuple) -> int:
    """
    Estimates appropriate zoom level based on bounds extent.

    Args:
        bounds: (minx, miny, maxx, maxy)

    Returns:
        Zoom level (1-18)
    """
    minx, miny, maxx, maxy = bounds
    lat_diff = maxy - miny
    lon_diff = maxx - minx
    max_diff = max(lat_diff, lon_diff)

    # Rough zoom estimation based on extent
    if max_diff > 100:
        return 2
    elif max_diff > 50:
        return 3
    elif max_diff > 20:
        return 4
    elif max_diff > 10:
        return 5
    elif max_diff > 5:
        return 6
    elif max_diff > 2:
        return 7
    elif max_diff > 1:
        return 8
    elif max_diff > 0.5:
        return 9
    elif max_diff > 0.2:
        return 10
    elif max_diff > 0.1:
        return 11
    else:
        return 12

def save_selected_watershed(hybas_id: int, region: str = None, level: int = None):
    """
    Updates config.yaml with the selected watershed info.

    Args:
        hybas_id: Selected HYBAS_ID
        region: Region code (optional, will update if provided)
        level: Level (optional, will update if provided)
    """
    config = load_config()
    config["watershed"]["default_id"] = int(hybas_id)

    if region:
        config["watershed"]["region"] = region
    if level:
        config["watershed"]["level"] = int(level)

    save_yaml_config(config)
    print(f"Updated config with Watershed ID: {hybas_id}")

def get_available_regions() -> list:
    """Returns list of available region codes."""
    return ['all', 'af', 'ar', 'as', 'au', 'eu', 'gr', 'na', 'sa', 'si']

def get_region_display_name(region: str) -> str:
    """Returns human-readable name for region code."""
    names = {
        'all': 'All Regions',
        'af': 'Africa',
        'ar': 'Arctic',
        'as': 'Asia',
        'au': 'Australia',
        'eu': 'Europe',
        'gr': 'Greenland',
        'na': 'North America',
        'sa': 'South America',
        'si': 'Siberia',
    }
    return names.get(region, region)


def load_all_regions_at_level(level: int) -> gpd.GeoDataFrame:
    """
    Load and combine all regions at a given level.

    Args:
        level: HydroBASINS level (1-12)

    Returns:
        Combined GeoDataFrame with all regions
    """
    # All actual region codes (not including 'all')
    actual_regions = ['af', 'ar', 'as', 'au', 'eu', 'gr', 'na', 'sa', 'si']
    gdfs = []

    for region in actual_regions:
        try:
            gdf = load_watersheds(region, level)
            gdf['region'] = region  # Add region column for reference
            gdfs.append(gdf)
        except Exception as e:
            print(f"[WARNING] Could not load {region} level {level}: {e}")

    if gdfs:
        combined = gpd.pd.concat(gdfs, ignore_index=True)
        print(f"[INFO] Combined {len(combined)} watersheds from {len(gdfs)} regions at level {level}")
        return combined

    return gpd.GeoDataFrame()

def filter_nearby_watersheds(
    full_gdf: gpd.GeoDataFrame, 
    target_hybas_id: int, 
    expansion_factor: float = 1.5
) -> gpd.GeoDataFrame:
    """
    Filters watersheds within expanded bounding box of target watershed.
    This reduces the amount of data sent to frontend, preventing WebSocket overload.
    
    Args:
        full_gdf: Complete GeoDataFrame with all watersheds
        target_hybas_id: HYBAS_ID of the selected watershed
        expansion_factor: How much to expand the bounding box (1.5 = 50% larger)
    
    Returns:
        Filtered GeoDataFrame with nearby watersheds only
    
    Example:
        >>> gdf = load_watersheds("as", 7)
        >>> filtered = filter_nearby_watersheds(gdf, 4070026610, expansion_factor=2.0)
        >>> print(f"Filtered from {len(gdf)} to {len(filtered)} watersheds")
    """
    # Find the target watershed
    target = full_gdf[full_gdf['HYBAS_ID'] == target_hybas_id]
    
    if target.empty:
        print(f"Warning: HYBAS_ID {target_hybas_id} not found in GeoDataFrame")
        return full_gdf
    
    # Get bounding box of target watershed
    minx, miny, maxx, maxy = target.total_bounds
    
    # Calculate center and expansion
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    width = maxx - minx
    height = maxy - miny
    
    # Expand bounding box
    expanded_width = width * expansion_factor
    expanded_height = height * expansion_factor
    
    expanded_minx = center_x - expanded_width / 2
    expanded_maxx = center_x + expanded_width / 2
    expanded_miny = center_y - expanded_height / 2
    expanded_maxy = center_y + expanded_height / 2
    
    # Use cx indexer for fast spatial filtering
    filtered_gdf = full_gdf.cx[
        expanded_minx:expanded_maxx, 
        expanded_miny:expanded_maxy
    ]
    
    print(f"Filtered from {len(full_gdf)} to {len(filtered_gdf)} nearby watersheds.")
    
    return filtered_gdf

def find_watersheds_by_coordinates(
    region: str, 
    level: int, 
    lat: float, 
    lon: float,
    buffer_degrees: float = 5.0
) -> gpd.GeoDataFrame:
    """
    Find watersheds within buffer range of given coordinates.
    
    Args:
        region: Region code (af, ar, as, au, eu, gr, na, sa)
        level: HydroBASINS level (1-12)
        lat: Latitude in WGS84
        lon: Longitude in WGS84
        buffer_degrees: Buffer range in degrees (default: 5.0)
    
    Returns:
        Filtered GeoDataFrame with watersheds in the buffer range
    
    Example:
        >>> # Search for watersheds near Taipei (25.0, 121.5)
        >>> gdf = find_watersheds_by_coordinates("as", 7, 25.0, 121.5, buffer_degrees=5.0)
        >>> print(f"Found {len(gdf)} watersheds near Taipei")
    """
    # Load full shapefile for the region/level
    full_gdf = load_watersheds(region, level)
    
    # Filter by bounding box using GeoPandas cx indexer
    # cx uses [x_min:x_max, y_min:y_max] format (lon, lat)
    filtered_gdf = full_gdf.cx[
        lon - buffer_degrees : lon + buffer_degrees,
        lat - buffer_degrees : lat + buffer_degrees
    ]
    
    print(f"Filtered from {len(full_gdf)} to {len(filtered_gdf)} watersheds near ({lat}, {lon}).")
    
    return filtered_gdf

