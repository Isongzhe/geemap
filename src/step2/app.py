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
from pathlib import Path
import solara
import geemap
import rioxarray
import ee
import geopandas as gpd
from ipyleaflet import GeoJSON, SplitMapControl
from localtileserver import TileClient, get_leaflet_tile_layer
from pyproj import Transformer

import src.state as state
from src.config import (
    INPUT_TILE_PORT,
    OUTPUT_TILE_PORT,
    EE_PROJECT,
    DEFAULT_CENTER,
    DEFAULT_ZOOM,
    WATERSHED_ZOOM,
    CLASSIFICATION_COLORMAP,
    UNCERTAINTY_COLORMAP,
    WATERSHED_COLOR,
    WATERSHED_LINE_WIDTH,
    STEP2_TITLE,
    load_yaml_config,
    get_model_paths,
    get_model_config,
    get_watershed_config,
)
from src.step2.utils import find_event_input, find_event_output

# ============================================================================
# Global TileClient Singleton
# ============================================================================

# Module-level cache to prevent recreating TileClient on hot-reload
_tile_clients_cache = {}

# Module-level reference to current SplitMapControl (singleton)
_current_split_control = None

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
# Configuration & File Discovery
# ============================================================================

# Get model configuration
model_config = get_model_config()
event_date = model_config.get("event_date")
input_folder = model_config.get("input_folder")
output_folder = model_config.get("output_folder")

# Get return period from Step 1
selected_return_period = state.selected_return_period.value

print(f"[STEP2] Event Date: {event_date}")
print(f"[STEP2] Return Period: {selected_return_period}")
print(f"[STEP2] Input Folder: {input_folder}")
print(f"[STEP2] Output Folder: {output_folder}")

# Find files for this event
INPUT_PATH = None
OUTPUT_PATH = None

if event_date and input_folder and output_folder:
    input_file = find_event_input(event_date, input_folder)
    output_file = find_event_output(event_date, output_folder)
    
    if input_file:
        INPUT_PATH = str(input_file)
    if output_file:
        OUTPUT_PATH = str(output_file)

if INPUT_PATH and OUTPUT_PATH:
    print("[STEP2] Configuration loaded successfully")
    print(f"[STEP2] Input: {Path(INPUT_PATH).name}")
    print(f"[STEP2] Output: {Path(OUTPUT_PATH).name}")
else:
    print("[STEP2] Warning: Could not find input/output files for this event")

# Re-adding watershed config for now, as it's used later and not part of the refactor instruction
WATERSHED_CFG = get_watershed_config()
WATERSHED_PATH = WATERSHED_CFG.get("path")
WATERSHED_ID = WATERSHED_CFG.get("default_id")

# ============================================================================
# Reactive State
# ============================================================================

map_layer_mode = solara.reactive("Flood Classification")  # "Flood Classification" or "Uncertainty" 

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
    Uses module-level singleton cache to prevent port conflicts on hot-reload.

    Ports:
        - Input (Sentinel-2): port 9000
        - Output (Model): port 9001

    Returns:
        dict: Dictionary with 'input' and 'output' TileClient instances
    """
    global _tile_clients_cache

    # Return cached clients if already created (singleton pattern)
    if _tile_clients_cache:
        print("[STEP2] Using cached TileClients")
        return _tile_clients_cache

    # Create Input TileClient
    if INPUT_PATH and os.path.exists(INPUT_PATH):
        _tile_clients_cache['input'] = TileClient(
            INPUT_PATH,
            port=INPUT_TILE_PORT,
            host='0.0.0.0',
            client_port=INPUT_TILE_PORT,
            client_host='localhost'
        )
        print(f"[STEP2] Input TileClient created on port {INPUT_TILE_PORT}")

    # Create Output TileClient
    if OUTPUT_PATH and os.path.exists(OUTPUT_PATH):
        _tile_clients_cache['output'] = TileClient(
            OUTPUT_PATH,
            port=OUTPUT_TILE_PORT,
            host='0.0.0.0',
            client_port=OUTPUT_TILE_PORT,
            client_host='localhost'
        )
        print(f"[STEP2] Output TileClient created on port {OUTPUT_TILE_PORT}")

    return _tile_clients_cache


def _create_watershed_layer():
    """
    Create a GeoJSON layer for the watershed boundary.

    Uses GeoJSON from global state (passed from Step 1).
    Falls back to loading from file if state is empty.

    Returns:
        GeoJSON: ipyleaflet GeoJSON layer or None if not available
    """
    # Try to get GeoJSON from global state first (preferred)
    watershed_geojson = state.selected_watershed_geojson.value
    watershed_id = state.selected_watershed_id.value

    if watershed_geojson is not None:
        print(f"[STEP2] Using watershed GeoJSON from Step 1 (ID: {watershed_id})")
        return GeoJSON(
            data=watershed_geojson,
            style={
                'color': WATERSHED_COLOR,
                'fillOpacity': 0.0,
                'weight': WATERSHED_LINE_WIDTH
            },
            name=f"Watershed {watershed_id}"
        )

    # Fallback: Load from config file
    if not WATERSHED_PATH or not WATERSHED_ID:
        return None

    try:
        gdf = gpd.read_file(WATERSHED_PATH)
        target = gdf[gdf['HYBAS_ID'] == WATERSHED_ID]

        if not target.empty:
            print(f"[STEP2] Loaded watershed from file (ID: {WATERSHED_ID})")
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
    - Split-map view (always enabled)
    - Layer mode selection (Classification vs Uncertainty)
    - Watershed boundary overlay
    """
    # Reactive state values
    layer_mode = map_layer_mode.value
    
    # Create map widget (memoized)
    map_widget = solara.use_memo(_create_base_map, dependencies=[])
    
    # Create tile clients (memoized)
    tile_clients = solara.use_memo(_create_tile_clients, dependencies=[])

    # Create watershed layer (memoized, updates when global state changes)
    watershed_layer = solara.use_memo(
        _create_watershed_layer,
        dependencies=[state.selected_watershed_geojson.value, state.selected_watershed_id.value]
    )
    
    def update_layers():
        """
        Update map layers based on current layer mode.

        Split view is always enabled:
        - Classification mode: Left = Sentinel-2, Right = Classification
        - Uncertainty mode: Left = Classification, Right = Uncertainty
        """
        global _current_split_control
        m = map_widget

        try:
            # IMPORTANT: Remove SplitMapControl FIRST, before clearing layers
            # This prevents orphaned visual elements
            if _current_split_control is not None:
                try:
                    m.remove_control(_current_split_control)
                    print("[STEP2] Removed existing SplitMapControl")
                except Exception:
                    pass  # Control might already be removed
                _current_split_control = None

            # Also remove any other SplitMapControls (safety cleanup)
            controls_to_remove = [ctrl for ctrl in m.controls if isinstance(ctrl, SplitMapControl)]
            for ctrl in controls_to_remove:
                try:
                    m.remove_control(ctrl)
                except Exception:
                    pass

            # Now clear layers and reset basemap
            m.clear_layers()
            m.add_basemap("OpenStreetMap")

            input_available = 'input' in tile_clients
            output_available = 'output' in tile_clients

            if not (input_available and output_available):
                print("[STEP2] Missing input or output tiles")
                return

            # Create layers based on mode
            if layer_mode == "Flood Classification":
                # Left: Sentinel-2 original image
                left_layer = get_leaflet_tile_layer(
                    tile_clients['input'],
                    name="Sentinel-2",
                    opacity=1.0
                )

                # Right: Flood classification
                right_layer = get_leaflet_tile_layer(
                    tile_clients['output'],
                    name="Classification",
                    indexes=[1],
                    colormap=CLASSIFICATION_COLORMAP,
                    opacity=0.7
                )
            else:  # Uncertainty mode
                # Left: Flood classification
                left_layer = get_leaflet_tile_layer(
                    tile_clients['output'],
                    name="Classification",
                    indexes=[1],
                    colormap=CLASSIFICATION_COLORMAP,
                    opacity=0.7
                )

                # Right: Uncertainty map (full range 0-1)
                right_layer = get_leaflet_tile_layer(
                    tile_clients['output'],
                    name="Uncertainty",
                    indexes=[2],
                    colormap=UNCERTAINTY_COLORMAP,
                    vmin=0.0,
                    vmax=1.0,  # Show full uncertainty range
                    opacity=0.7
                )

            # Add layers to map
            m.add_layer(left_layer)
            m.add_layer(right_layer)

            # Create and store new SplitMapControl
            _current_split_control = SplitMapControl(left_layer=left_layer, right_layer=right_layer)
            m.add_control(_current_split_control)

            # Always add watershed boundary on top
            if watershed_layer:
                m.add_layer(watershed_layer)

            print(f"[STEP2] Rendered split-map: {layer_mode}")

        except Exception as e:
            print(f"[STEP2] Error updating layers: {e}")
            import traceback
            traceback.print_exc()
    
    # Update layers when mode changes (not on every threshold change)
    solara.use_effect(update_layers, dependencies=[layer_mode])
    
    # ========================================================================
    # UI Layout
    # ========================================================================
    
    with solara.Column(style={"height": "100vh"}):
        solara.Title(STEP2_TITLE)
        
        with solara.Sidebar():
            # Event Information
            solara.Markdown("### Event Information")
            with solara.Card(elevation=0, style={"margin-bottom": "1rem"}):
                solara.Markdown(f"**Event Date:** `{event_date}`")
                solara.Markdown(f"**Return Period:** `{selected_return_period}`")
            
            solara.Markdown("---")
            
            solara.Markdown("### Display Mode")
            
            # Layer mode selection (Classification vs Uncertainty)
            solara.ToggleButtonsSingle(
                value=map_layer_mode,
                values=["Flood Classification", "Uncertainty"]
            )
            
            solara.Markdown("---")
            
            # Display legend based on mode
            if layer_mode == "Flood Classification":
                solara.Markdown("### Split View")
                solara.Markdown("**Left:** Sentinel-2 Original Image")
                solara.Markdown("**Right:** Flood Classification")
                
                solara.Markdown("### Classification Legend")
                with solara.Card(elevation=0):
                    solara.Markdown(
                        "**Class Values** (Viridis colormap):\n\n"
                        "- **0**: Invalid/No Data (Dark Purple)\n"
                        "- **1**: Land (Purple-Blue)\n"
                        "- **2**: Water (Green-Blue)\n"
                        "- **3**: Cloud (Yellow-Green)\n"
                        "- **4**: Flood Trace (Yellow)"
                    )
            else:  # Uncertainty mode
                solara.Markdown("### Split View")
                solara.Markdown("**Left:** Flood Classification")
                solara.Markdown("**Right:** Uncertainty Map")
                
                solara.Markdown("### Uncertainty Legend")
                with solara.Card(elevation=0):
                    solara.Markdown(
                        "**Color Scale:**\n\n"
                        "- 🟢 **Green** = Low uncertainty (reliable)\n"
                        "- 🟡 **Yellow** = Medium uncertainty\n"
                        "- 🔴 **Red** = High uncertainty (unreliable)\n\n"
                        "Values range from 0 (certain) to 1 (uncertain)"
                    )
        
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
