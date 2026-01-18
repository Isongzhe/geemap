"""
Step 2: Flood Visualization Application

This module provides an interactive visualization interface for flood classification
and uncertainty mapping using Solara, geemap, and localtileserver.

Features:
- Display Sentinel-2 imagery and model outputs
- Split-map view for side-by-side comparison
- Interactive uncertainty threshold filtering
- Watershed boundary overlay
"""

import os
import functools
import solara
import geemap
import rioxarray
import yaml
import ee
import geopandas as gpd
from ipyleaflet import GeoJSON, SplitMapControl
from localtileserver import TileClient, get_leaflet_tile_layer
from pyproj import Transformer

# ============================================================================
# Configuration Constants
# ============================================================================

# Tile server configuration for remote access (e.g., VSCode dev containers)
TILE_SERVER_HOST = '0.0.0.0'  # Listen on all network interfaces
TILE_SERVER_PORT = 9000        # Fixed port for VSCode auto-forwarding
CLIENT_HOST = 'localhost'      # Client-side host for tile requests

# Earth Engine configuration
EE_PROJECT = "geemap-484609"

# Map configuration
DEFAULT_CENTER = (20, 0)       # Default map center (lat, lon)
DEFAULT_ZOOM = 2               # Default zoom level
WATERSHED_ZOOM = 11            # Zoom level when watershed is loaded

# Visualization parameters
CLASSIFICATION_COLORMAP = 'viridis'
UNCERTAINTY_COLORMAP = 'rdylgn_r'
WATERSHED_COLOR = '#FFD700'    # Gold color for watershed boundary
WATERSHED_LINE_WIDTH = 4

# ============================================================================
# Environment Setup
# ============================================================================

# Configure localtileserver for remote environments
os.environ['REST_SERVER_HOST'] = TILE_SERVER_HOST
os.environ['LOCALTILESERVER_CLIENT_PORT'] = str(TILE_SERVER_PORT)

# ============================================================================
# Earth Engine Initialization
# ============================================================================

try:
    ee.Initialize()
except Exception:
    try:
        ee.Authenticate()
        ee.Initialize(project=EE_PROJECT)
    except Exception as e:
        print(f"[STEP2] Earth Engine initialization failed: {e}")

# ============================================================================
# Load Configuration
# ============================================================================

try:
    with open("dataset/config.yaml", "r") as f:
        config_data = yaml.safe_load(f)
        WATERSHED_CFG = config_data.get("watershed", {})
        WATERSHED_PATH = WATERSHED_CFG.get("path")
        WATERSHED_ID = WATERSHED_CFG.get("default_id")
        INPUT_PATH = config_data["model"]["input_path"]
        OUTPUT_PATH = config_data["model"]["output_path"]
        print(f"[STEP2] Configuration loaded successfully")
except Exception as e:
    print(f"[STEP2] Configuration error: {e}")
    WATERSHED_PATH = None
    WATERSHED_ID = None
    INPUT_PATH = None
    OUTPUT_PATH = None

# ============================================================================
# Reactive State
# ============================================================================

uncertainty_threshold = solara.reactive(0.5)
show_split_map = solara.reactive(True)
map_layer_mode = solara.reactive("Flood Classification") 

# ============================================================================
# Helper Functions
# ============================================================================

@functools.lru_cache(maxsize=1)
def get_map_center():
    """
    Calculate the center point and zoom level for the map based on input data bounds.
    
    Returns:
        tuple: (longitude, latitude, zoom_level)
    """
    try:
        if not INPUT_PATH or not os.path.exists(INPUT_PATH):
            return DEFAULT_CENTER[1], DEFAULT_CENTER[0], DEFAULT_ZOOM
        
        with rioxarray.open_rasterio(INPUT_PATH) as src:
            bounds = src.rio.bounds()
            crs = src.rio.crs
            cx = (bounds[0] + bounds[2]) / 2
            cy = (bounds[1] + bounds[3]) / 2
            
            # Transform to WGS84 if necessary
            if crs and crs != "EPSG:4326":
                transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                cx, cy = transformer.transform(cx, cy)
            
            return cx, cy, WATERSHED_ZOOM
    except Exception as e:
        print(f"[STEP2] Error calculating map center: {e}")
        return DEFAULT_CENTER[1], DEFAULT_CENTER[0], DEFAULT_ZOOM


def _create_base_map():
    """
    Create a base geemap.Map widget with initial settings.
    
    Returns:
        geemap.Map: Configured map widget
    """
    cx, cy, zoom = get_map_center()
    m = geemap.Map(
        center=[cy, cx],
        zoom=zoom,
        lite_mode=False,
        toolbar_ctrl=False,
        draw_ctrl=False,
        search_control=False,
        data_ctrl=False
    )
    return m


def _create_tile_clients():
    """
    Create TileClient instances for input and output GeoTIFF files.
    Uses a fixed port for compatibility with remote development environments.
    
    Returns:
        dict: Dictionary with 'input' and 'output' TileClient instances
    """
    clients = {}
    
    # Create input TileClient (Sentinel-2 imagery)
    if INPUT_PATH and os.path.exists(INPUT_PATH):
        try:
            clients['input'] = TileClient(
                INPUT_PATH,
                port=TILE_SERVER_PORT,
                host=TILE_SERVER_HOST,
                client_port=TILE_SERVER_PORT,
                client_host=CLIENT_HOST
            )
            print(f"[STEP2] Input TileClient created: {clients['input'].client_base_url}")
        except Exception as e:
            print(f"[STEP2] Failed to create input TileClient: {e}")
    
    # Create output TileClient (model predictions)
    if OUTPUT_PATH and os.path.exists(OUTPUT_PATH):
        try:
            clients['output'] = TileClient(
                OUTPUT_PATH,
                port=TILE_SERVER_PORT,
                host=TILE_SERVER_HOST,
                client_port=TILE_SERVER_PORT,
                client_host=CLIENT_HOST
            )
            print(f"[STEP2] Output TileClient created: {clients['output'].client_base_url}")
        except Exception as e:
            print(f"[STEP2] Failed to create output TileClient: {e}")
    
    return clients


def _create_watershed_layer():
    """
    Create a GeoJSON layer for the watershed boundary.
    
    Returns:
        GeoJSON: ipyleaflet GeoJSON layer or None if not available
    """
    if not WATERSHED_PATH or not WATERSHED_ID:
        return None
    
    try:
        gdf = gpd.read_file(WATERSHED_PATH)
        target = gdf[gdf['HYBAS_ID'] == WATERSHED_ID]
        
        if not target.empty:
            return GeoJSON(
                data=target.__geo_interface__,
                style={
                    'color': WATERSHED_COLOR,
                    'fillOpacity': 0.0,
                    'weight': WATERSHED_LINE_WIDTH
                },
                name=f"Watershed {WATERSHED_ID}"
            )
    except Exception as e:
        print(f"[STEP2] Error loading watershed: {e}")
    
    return None


# ============================================================================
# Main Component
# ============================================================================

@solara.component
def Page():
    """
    Main Solara component for the flood visualization interface.
    
    Provides:
    - Interactive map with COG tile layers
    - Split-map view for side-by-side comparison
    - Layer mode selection (Classification vs Uncertainty)
    - Uncertainty threshold filtering
    - Watershed boundary overlay
    """
    # Reactive state values
    threshold = uncertainty_threshold.value
    is_split = show_split_map.value
    layer_mode = map_layer_mode.value
    
    # Create map widget (memoized)
    map_widget = solara.use_memo(_create_base_map, dependencies=[])
    
    # Create tile clients (memoized)
    tile_clients = solara.use_memo(_create_tile_clients, dependencies=[])
    
    # Create watershed layer (memoized)
    watershed_layer = solara.use_memo(_create_watershed_layer, dependencies=[])
    
    def update_layers():
        """
        Update map layers based on current state (split mode, layer mode, threshold).
        This function is called whenever reactive dependencies change.
        """
        m = map_widget
        
        try:
            # Clear existing layers and reset basemap
            m.clear_layers()
            m.add_basemap("OpenStreetMap")
            
            # Remove existing SplitMapControl to prevent duplication
            # This fixes the split panel corruption issue when threshold changes
            controls_to_remove = [ctrl for ctrl in m.controls if isinstance(ctrl, SplitMapControl)]
            for ctrl in controls_to_remove:
                m.remove_control(ctrl)
            
            input_available = 'input' in tile_clients
            output_available = 'output' in tile_clients
            
            if is_split and input_available and output_available:
                # Split-map mode: show input on left, output on right
                print(f"[STEP2] Rendering split-map view")
                
                # Create input layer (Sentinel-2)
                l_input = get_leaflet_tile_layer(
                    tile_clients['input'],
                    name="Sentinel-2",
                    opacity=1.0
                )
                
                # Create output layer based on selected mode
                if layer_mode == "Flood Classification":
                    l_output = get_leaflet_tile_layer(
                        tile_clients['output'],
                        name="Classification",
                        indexes=[1],
                        colormap=CLASSIFICATION_COLORMAP,
                        opacity=0.7
                    )
                else:  # Uncertainty mode
                    l_output = get_leaflet_tile_layer(
                        tile_clients['output'],
                        name="Uncertainty",
                        indexes=[2],
                        colormap=UNCERTAINTY_COLORMAP,
                        vmin=0.0,
                        vmax=threshold,
                        opacity=0.7
                    )
                
                # Add layers to map
                m.add_layer(l_input)
                m.add_layer(l_output)
                
                # Add split map control
                split_control = SplitMapControl(left_layer=l_input, right_layer=l_output)
                m.add_control(split_control)
                
            else:
                # Single layer mode
                if input_available:
                    print(f"[STEP2] Adding Sentinel-2 layer")
                    l_input = get_leaflet_tile_layer(
                        tile_clients['input'],
                        name="Sentinel-2",
                        opacity=1.0
                    )
                    m.add_layer(l_input)
                
                if output_available:
                    print(f"[STEP2] Adding {layer_mode} layer")
                    if layer_mode == "Flood Classification":
                        l_output = get_leaflet_tile_layer(
                            tile_clients['output'],
                            name="Classification",
                            indexes=[1],
                            colormap=CLASSIFICATION_COLORMAP,
                            opacity=0.7
                        )
                    else:  # Uncertainty mode
                        l_output = get_leaflet_tile_layer(
                            tile_clients['output'],
                            name="Uncertainty",
                            indexes=[2],
                            colormap=UNCERTAINTY_COLORMAP,
                            vmin=0.0,
                            vmax=threshold,
                            opacity=0.7
                        )
                    m.add_layer(l_output)
            
            # Always add watershed boundary on top
            if watershed_layer:
                m.add_layer(watershed_layer)
                
        except Exception as e:
            print(f"[STEP2] Error updating layers: {e}")
            import traceback
            traceback.print_exc()
    
    # Update layers when dependencies change
    solara.use_effect(update_layers, dependencies=[is_split, layer_mode, threshold])
    
    # ========================================================================
    # UI Layout
    # ========================================================================
    
    with solara.Column(style={"height": "100vh"}):
        solara.Title("Step 2: Flood Visualization")
        
        with solara.Sidebar():
            solara.Markdown("### Configuration")
            
            # Split view toggle
            solara.Checkbox(
                label="Enable Split View",
                value=show_split_map,
            )
            
            # Layer mode selection
            solara.ToggleButtonsSingle(
                value=map_layer_mode,
                values=["Flood Classification", "Uncertainty"]
            )
            
            # Uncertainty threshold slider (only visible in Uncertainty mode)
            if layer_mode == "Uncertainty":
                solara.Markdown("#### Confidence Filter")
                solara.SliderFloat(
                    label="Max Uncertainty",
                    value=uncertainty_threshold,
                    min=0.0,
                    max=1.0,
                    step=0.05
                )
                solara.Info(f"Showing ≤ {threshold:.2f}")
        
        # Display map
        solara.display(map_widget)


# ============================================================================
# Entry Point
# ============================================================================

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    Page()
