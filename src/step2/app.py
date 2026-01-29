"""
Step 2: Flood Analytics Dashboard

This module provides an interactive analytics dashboard for flood event comparison
with analog selection, permanent water visualization, and similarity scoring.

Features:
- Multi-event selection from analog catalog
- All-in-one layer view with independent layer control via Layer Manager
- Layer stack (bottom to top):
  * Basemap (OpenStreetMap)
  * Permanent Water (hidden by default, blue overlay)
  * Sentinel-2 RGB (visible by default)
  * Flood Classification (visible by default)
  * Model Uncertainty (hidden by default)
  * Watershed Boundary (always visible)
- Users can toggle any layer on/off and adjust opacity via Layer Manager
- Analytics panel with event table and score distribution chart
"""

import os
import functools
import time
from pathlib import Path
import base64
import solara
import geemap
import rioxarray
import ee
import geopandas as gpd
import pandas as pd
from ipyleaflet import GeoJSON, WidgetControl, FullScreenControl
from localtileserver import TileClient, get_leaflet_tile_layer
from matplotlib.colors import ListedColormap
import plotly.graph_objects as go
from pyproj import Transformer
from typing import Optional

import src.state as state
from src.config import (
    EVENT_2020_INPUT_PORT,
    EVENT_2020_OUTPUT_PORT,
    EVENT_2024_INPUT_PORT,
    EVENT_2024_OUTPUT_PORT,
    PERMANENT_WATER_PORT,
    EE_PROJECT,
    DEFAULT_CENTER,
    DEFAULT_ZOOM,
    WATERSHED_ZOOM,
    CLASSIFICATION_COLORMAP,
    UNCERTAINTY_COLORMAP,
    CLASSIFICATION_OPACITY,
    PERMANENT_WATER_OPACITY,
    WATERSHED_COLOR,
    WATERSHED_LINE_WIDTH,
    STEP2_TITLE,
    load_yaml_config,
    get_model_paths,
    get_model_config,
    get_watershed_config,
    get_analog_df_config,
)
from src.step2.utils import (
    find_event_input,
    find_event_output,
    find_event_preview,
    load_analog_catalog,
    build_file_mapping,
    get_glofas_plot_path,
)

# ============================================================================
# Global TileClient Singleton
# ============================================================================

# Persistent TileClients - created once, never shutdown
_DEMO_TILE_CLIENTS = {
    '2020-04-18': {'input': None, 'output': None},
    '2024-04-20': {'input': None, 'output': None},
}
_PERMANENT_WATER_CLIENT = None
_CLIENTS_INITIALIZED = False

# Demo mode: Use local cached files for instant loading
DEMO_MODE = True
DEMO_EVENTS = ['2020-04-18', '2024-04-20']
LOCAL_CACHE_DIR = Path('/tmp/geemap_demo_cache')

# ============================================================================
# Lazy Initialization (Moved to Page() function to prevent blocking Step 1)
# ============================================================================

# Module-level variables (will be set by initialize_step2_data())
INPUT_PATH = None
OUTPUT_PATH = None
WATERSHED_CFG = None
WATERSHED_PATH = None
WATERSHED_ID = None
FILE_MAPPING = {}  # Cache: event_date -> {input, output, preview} paths

def initialize_step2_data():
    """
    Lazy initialization - only runs when Step 2 Page() is first rendered.

    Prevents blocking Step 1 startup with slow operations:
    - Earth Engine initialization (~1-2s)
    - Analog catalog loading (~100ms)
    - File discovery (~1-2s)

    Returns:
        dict with INPUT_PATH, OUTPUT_PATH, analog_df, etc.
    """
    global INPUT_PATH, OUTPUT_PATH, WATERSHED_CFG, WATERSHED_PATH, WATERSHED_ID, FILE_MAPPING

    # Earth Engine Initialization
    try:
        ee.Initialize()
    except Exception:
        try:
            ee.Authenticate()
            ee.Initialize(project=EE_PROJECT)
        except Exception as e:
            print(f"[STEP2] Earth Engine initialization failed: {e}")

    # Get model configuration
    model_config = get_model_config()
    input_folder = model_config.get("input_folder")
    output_folder = model_config.get("output_folder")

    # Get return period from Step 1
    selected_return_period = state.selected_return_period.value

    # Load permanent water path
    permanent_water_file = model_config.get("permanent_water_path")
    if permanent_water_file:
        permanent_water_path.set(permanent_water_file)
        print(f"[STEP2] Permanent water: {Path(permanent_water_file).name}")

    # Load analog catalog
    analog_config = get_analog_df_config()
    csv_path = analog_config.get("path")
    top_n = analog_config.get("top_n", 10)

    if csv_path:
        df = load_analog_catalog(csv_path, top_n)
        if df is not None and not df.empty:
            analog_events_df.set(df)
            # Set default to rank 1 event
            default_event = df.iloc[0]
            selected_event_date.set(default_event['datetime'])
            selected_event_metadata.set({
                'rank': int(default_event['rank']),
                'datetime': default_event['datetime'],
                'score': float(default_event['score'])
            })
            print(f"[STEP2] Loaded {len(df)} analog events, default: {default_event['datetime']}")
        else:
            # Fallback to single event from config
            fallback_date = model_config.get("event_date", "2024-04-13")
            selected_event_date.set(fallback_date)
            print(f"[STEP2] No analog catalog, using fallback date: {fallback_date}")
    else:
        # No analog catalog configured, use single event
        fallback_date = model_config.get("event_date", "2024-04-13")
        selected_event_date.set(fallback_date)
        print(f"[STEP2] No analog catalog configured, using single event: {fallback_date}")

    # Initial file discovery will be handled by use_effect in Page()
    print(f"[STEP2] Return Period: {selected_return_period}")
    print(f"[STEP2] Input Folder: {input_folder}")
    print(f"[STEP2] Output Folder: {output_folder}")

    # Load watershed config
    WATERSHED_CFG = get_watershed_config()
    WATERSHED_PATH = WATERSHED_CFG.get("path")
    WATERSHED_ID = WATERSHED_CFG.get("default_id")

    # Build file mapping cache for fast lookups
    FILE_MAPPING = build_file_mapping(input_folder, output_folder)
    print(f"[STEP2] File mapping cache built with {len(FILE_MAPPING)} events")

    return {
        "INPUT_PATH": INPUT_PATH,
        "OUTPUT_PATH": OUTPUT_PATH,
        "WATERSHED_PATH": WATERSHED_PATH,
        "WATERSHED_ID": WATERSHED_ID,
        "input_folder": input_folder,
        "output_folder": output_folder,
    }

# ============================================================================
# Reactive State
# ============================================================================

# Analog event management
analog_events_df = solara.reactive(None)  # DataFrame of analog events from CSV
selected_event_date = solara.reactive(None)  # Currently selected event date
selected_event_metadata = solara.reactive({})  # {rank, datetime, score} for selected event
preview_image_path = solara.reactive(None)  # Path to preview PNG for selected event

# Permanent water path (static across events)
permanent_water_path = solara.reactive(None) 

# ============================================================================
# Helper Functions
# ============================================================================

def get_map_center():
    """
    Calculate the center point and zoom level for the map based on watershed bounds from Step 1.

    Priority:
    1. Use watershed GeoJSON from Step 1 (state.selected_watershed_geojson)
    2. Fallback to INPUT_PATH bounds
    3. Fallback to DEFAULT_CENTER

    Returns:
        tuple: (longitude, latitude, zoom_level)
    """
    try:
        # Priority 1: Use watershed GeoJSON from Step 1
        watershed_geojson = state.selected_watershed_geojson.value
        if watershed_geojson:
            # Extract coordinates from GeoJSON
            coords = watershed_geojson['features'][0]['geometry']['coordinates'][0]
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            cx = (min(lons) + max(lons)) / 2
            cy = (min(lats) + max(lats)) / 2
            print(f"[STEP2] get_map_center: Using watershed GeoJSON: ({cx:.4f}, {cy:.4f})")
            return cx, cy, WATERSHED_ZOOM

        # Priority 2: Use INPUT_PATH bounds
        if INPUT_PATH and os.path.exists(INPUT_PATH):
            print(f"[STEP2] get_map_center: Using INPUT_PATH: {Path(INPUT_PATH).name}")
            with rioxarray.open_rasterio(INPUT_PATH) as src:
                bounds = src.rio.bounds()
                crs = src.rio.crs
                cx = (bounds[0] + bounds[2]) / 2
                cy = (bounds[1] + bounds[3]) / 2

                # Transform to WGS84 if necessary
                if crs and str(crs) != "EPSG:4326":
                    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                    cx, cy = transformer.transform(cx, cy)

                print(f"[STEP2] get_map_center: From INPUT_PATH: ({cx:.4f}, {cy:.4f})")
                return cx, cy, WATERSHED_ZOOM

        # Priority 3: Default fallback
        print(f"[STEP2] get_map_center: Using default center")
        return DEFAULT_CENTER[1], DEFAULT_CENTER[0], DEFAULT_ZOOM

    except Exception as e:
        print(f"[STEP2] Error calculating map center: {e}")
        import traceback
        traceback.print_exc()
        return DEFAULT_CENTER[1], DEFAULT_CENTER[0], DEFAULT_ZOOM


def _create_base_map():
    """
    Create base geemap Map widget.
    Returns a memoized map instance.
    """
    cx, cy, zoom = get_map_center()
    m = geemap.Map(
        center=[cy, cx],
        zoom=zoom,
        lite_mode=False,
        toolbar_ctrl=False,
        draw_ctrl=False,
        search_control=False,
        height="800px",
    )
    # Add modern layer manager for better UX
    m.add("layer_manager")
    return m


def _create_permanent_water_client():
    """
    Create TileClient for permanent water from local cache.
    Called once during initialization.
    """
    global _PERMANENT_WATER_CLIENT

    if _PERMANENT_WATER_CLIENT is not None:
        return _PERMANENT_WATER_CLIENT

    demo_water = LOCAL_CACHE_DIR / 'permanent_water.tif'
    if not demo_water.exists():
        raise FileNotFoundError(
            f"Permanent water cache missing. Run: uv run scripts/generate_demo_tiles.py"
        )
    
    print("[STEP2] Creating permanent water TileClient (persistent)")
    _PERMANENT_WATER_CLIENT = TileClient(
        str(demo_water),
        port=PERMANENT_WATER_PORT,
        host='0.0.0.0',
        client_port=PERMANENT_WATER_PORT,
        client_host='localhost'
    )
    return _PERMANENT_WATER_CLIENT


def _initialize_all_demo_clients():
    """
    Initialize ALL TileClients for both demo events at startup.
    These clients are NEVER shutdown - we just switch between them.
    
    Port allocation:
    - 2020-04-18: 9100 (input), 9101 (output)
    - 2024-04-20: 9103 (input), 9104 (output)
    - Permanent water: 9102 (shared)
    """
    global _DEMO_TILE_CLIENTS, _PERMANENT_WATER_CLIENT, _CLIENTS_INITIALIZED
    
    if _CLIENTS_INITIALIZED:
        print("[STEP2] Clients already initialized, skipping")
        return
    
    print("[STEP2] Initializing persistent TileClients for demo mode...")
    
    # 1. Create permanent water client (shared)
    _create_permanent_water_client()
    
    # 2. Create 2020-04-18 clients
    event_2020_dir = LOCAL_CACHE_DIR / '2020-04-18'
    input_2020 = event_2020_dir / 'input.tif'
    output_2020 = event_2020_dir / 'output.tif'
    
    if not input_2020.exists() or not output_2020.exists():
        raise FileNotFoundError(
            f"Demo cache missing for 2020-04-18. Run: uv run scripts/generate_demo_tiles.py"
        )
    
    print("[STEP2] Creating clients for 2020-04-18 (ports 9100, 9101)")
    _DEMO_TILE_CLIENTS['2020-04-18']['input'] = TileClient(
        str(input_2020),
        port=EVENT_2020_INPUT_PORT,
        host='0.0.0.0',
        client_port=EVENT_2020_INPUT_PORT,
        client_host='localhost'
    )
    _DEMO_TILE_CLIENTS['2020-04-18']['output'] = TileClient(
        str(output_2020),
        port=EVENT_2020_OUTPUT_PORT,
        host='0.0.0.0',
        client_port=EVENT_2020_OUTPUT_PORT,
        client_host='localhost'
    )
    
    # 3. Create 2024-04-20 clients
    event_2024_dir = LOCAL_CACHE_DIR / '2024-04-20'
    input_2024 = event_2024_dir / 'input.tif'
    output_2024 = event_2024_dir / 'output.tif'
    
    if not input_2024.exists() or not output_2024.exists():
        raise FileNotFoundError(
            f"Demo cache missing for 2024-04-20. Run: uv run scripts/generate_demo_tiles.py"
        )
    
    print("[STEP2] Creating clients for 2024-04-20 (ports 9103, 9104)")
    _DEMO_TILE_CLIENTS['2024-04-20']['input'] = TileClient(
        str(input_2024),
        port=EVENT_2024_INPUT_PORT,
        host='0.0.0.0',
        client_port=EVENT_2024_INPUT_PORT,
        client_host='localhost'
    )
    _DEMO_TILE_CLIENTS['2024-04-20']['output'] = TileClient(
        str(output_2024),
        port=EVENT_2024_OUTPUT_PORT,
        host='0.0.0.0',
        client_port=EVENT_2024_OUTPUT_PORT,
        client_host='localhost'
    )
    
    _CLIENTS_INITIALIZED = True
    print("[STEP2] All demo TileClients initialized and ready")


def _get_clients_for_event(event_date: str) -> dict:
    """
    Get pre-initialized TileClients for the given event.
    NO creation, NO shutdown - just returns existing clients.
    
    Args:
        event_date: '2020-04-18' or '2024-04-20'
    
    Returns:
        Dict with keys 'input', 'output', 'water'
    """
    if event_date not in DEMO_EVENTS:
        raise ValueError(f"Event {event_date} not supported. Only {DEMO_EVENTS} available.")
    
    if not _CLIENTS_INITIALIZED:
        raise RuntimeError("Clients not initialized. Call _initialize_all_demo_clients() first.")
    
    return {
        'input': _DEMO_TILE_CLIENTS[event_date]['input'],
        'output': _DEMO_TILE_CLIENTS[event_date]['output'],
        'water': _PERMANENT_WATER_CLIENT
    }



def _create_tile_clients_for_event(event_date: str, input_folder: str, output_folder: str):
    """
    Create TileClient instances for demo events from local cache.
    Demo mode only supports: 2020-04-18, 2024-04-20

    Returns: Dict with keys 'input', 'output', 'water'
    """
    global INPUT_PATH, OUTPUT_PATH, _tile_clients_cache

    # Shutdown old input/output clients to release ports
    for key in ['input', 'output']:
        if key in _tile_clients_cache:
            old_client = _tile_clients_cache[key]
            if hasattr(old_client, 'shutdown'):
                old_client.shutdown()
                print(f"[STEP2] Shutdown old {key} TileClient")
            del _tile_clients_cache[key]
    
    # Wait for ports to be fully released
    if len(_tile_clients_cache) == 0 or 'input' not in _tile_clients_cache:
        time.sleep(0.5)

    # Resolve file paths from local cache
    new_input_path = None
    new_output_path = None
    new_preview_path = None

    if event_date in DEMO_EVENTS:
        event_dir = LOCAL_CACHE_DIR / event_date
        demo_input = event_dir / 'input.tif'
        demo_output = event_dir / 'output.tif'
        
        if not demo_input.exists() or not demo_output.exists():
            raise FileNotFoundError(
                f"Demo cache missing for {event_date}. Run: uv run scripts/generate_demo_tiles.py"
            )
        
        new_input_path = str(demo_input)
        new_output_path = str(demo_output)
        print(f"[STEP2] DEMO MODE: Using local cache for {event_date}")
        
        # Get preview from FILE_MAPPING if available
        if event_date in FILE_MAPPING:
            file_info = FILE_MAPPING[event_date]
            if file_info.get('preview'):
                new_preview_path = str(file_info.get('preview'))
    else:
        raise ValueError(f"Event {event_date} not supported in demo mode. Only {DEMO_EVENTS} are supported.")
    current_clients = {}

    # 3. Create Input Client
    if new_input_path:
        if not Path(new_input_path).name.startswith('S2_'):
            print(f"[STEP2] ERROR: Input file is not S2: {Path(new_input_path).name}")
            INPUT_PATH = None
        else:
            INPUT_PATH = new_input_path
            print(f"[STEP2] Creating Input TileClient: {Path(INPUT_PATH).name}")
            input_client = TileClient(
                INPUT_PATH,
                port=INPUT_TILE_PORT,
                host='0.0.0.0',
                client_port=INPUT_TILE_PORT,
                client_host='localhost'
            )
            current_clients['input'] = input_client
            _tile_clients_cache['input'] = input_client  # Update cache
            print(f"[STEP2] Input TileClient server running on {input_client.server_base_url}")

    # 4. Create Output Client
    if new_output_path:
        OUTPUT_PATH = new_output_path
        print(f"[STEP2] Creating Output TileClient: {Path(OUTPUT_PATH).name}")
        output_client = TileClient(
            OUTPUT_PATH,
            port=OUTPUT_TILE_PORT,
            host='0.0.0.0',
            client_port=OUTPUT_TILE_PORT,
            client_host='localhost'
        )
        current_clients['output'] = output_client
        _tile_clients_cache['output'] = output_client  # Update cache
        print(f"[STEP2] Output TileClient server running on {output_client.server_base_url}")

    # 5. Add Water Client (singleton, never recreated)
    if 'water' not in _tile_clients_cache:
        _create_permanent_water_client()
    if 'water' in _tile_clients_cache:
        current_clients['water'] = _tile_clients_cache['water']

    # Validate all clients are ready
    for key, client in current_clients.items():
        if not hasattr(client, 'server'):
            raise RuntimeError(f"TileClient {key} has no server attribute")
    
    print(f"[STEP2] All TileClients ready for {event_date}")
    return current_clients


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
    Main Solara component for the flood analytics dashboard.

    Provides:
    - Multi-event selection from analog catalog
    - Interactive map with COG tile layers
    - Independent layer control with layer manager (all layers in one view)
    - Layer stack order (bottom to top):
      * Basemap (OpenStreetMap)
      * Permanent Water (hidden by default)
      * Sentinel-2 RGB (visible by default)
      * Flood Classification (visible by default)
      * Model Uncertainty (hidden by default)
      * Watershed Boundary (always visible)
    - All layers can be toggled on/off via Layer Manager
    - Analytics panel with table and chart
    """
    # Lazy initialization - only runs once when Step 2 is first opened
    init_data = solara.use_memo(initialize_step2_data, dependencies=[])
    
    # Initialize persistent TileClients (only once)
    solara.use_memo(_initialize_all_demo_clients, dependencies=[])

    # Get configuration values
    input_folder = init_data.get("input_folder", "")
    output_folder = init_data.get("output_folder", "")

    # Reactive state values
    current_event_date = selected_event_date.value
    current_metadata = selected_event_metadata.value
    events_df = analog_events_df.value

    # Create map widget (memoized)
    map_widget = solara.use_memo(_create_base_map, dependencies=[])

    def cleanup_map(m):
        """Thoroughly clean up map layers (keep basemap only)."""
        # Clear all layers and re-add basemap
        m.clear_layers()
        m.add_basemap("OpenStreetMap")
        print("[STEP2] Map cleaned up")

    def update_layers(tile_clients, current_event_date):
        """
        Update map layers with all available data.
        All layers are added, with Uncertainty and Permanent Water hidden by default.

        Args:
            tile_clients: Dict containing 'input', 'output', 'water' clients
            current_event_date: String date for unique naming
        """
        m = map_widget

        # Validate tile clients exist
        if 'input' not in tile_clients or 'output' not in tile_clients:
            raise ValueError("Missing required tile clients")
        
        # Clean up map first
        cleanup_map(m)

        # Unique suffix to prevent browser caching
        import time
        unique_suffix = f"{current_event_date}_{int(time.time())}"

        # Layer order (bottom to top): Basemap -> Permanent Water -> S2 RGB -> Classification -> Uncertainty -> Watershed
        # Default visibility: S2 RGB (ON), Classification (ON), Permanent Water (OFF), Uncertainty (OFF)

        # Layer 1: Permanent Water (HIDDEN by default)
        if 'water' in tile_clients:
            water_layer = get_leaflet_tile_layer(
                tile_clients['water'],
                name="Permanent Water",
                colormap='blues',  # Use built-in colormap (0=transparent, 1=blue)
                vmin=0,
                vmax=1,
                nodata=0,  # Make 0 values transparent
                opacity=PERMANENT_WATER_OPACITY
            )
            water_layer.visible = False  # Hidden by default
            m.add_layer(water_layer)
            print("[STEP2] Added permanent water layer (hidden by default)")

        # Layer 2: Sentinel-2 RGB (VISIBLE by default)
        print(f"[STEP2] Adding S2 RGB from: {Path(INPUT_PATH).name if INPUT_PATH else 'None'}")
        s2_layer = get_leaflet_tile_layer(
            tile_clients['input'],
            name="Sentinel-2 RGB",
            indexes=[4, 3, 2],
            vmin=0, vmax=4000, opacity=1.0
        )
        s2_layer.visible = True  # Visible by default
        m.add_layer(s2_layer)

        # Layer 3: Flood Classification (VISIBLE by default)
        classification_cmap = ListedColormap(CLASSIFICATION_COLORMAP)
        classification_layer = get_leaflet_tile_layer(
            tile_clients['output'],
            name="Flood Classification",
            indexes=[1],
            colormap=classification_cmap,
            vmin=0, vmax=4, opacity=CLASSIFICATION_OPACITY
        )
        classification_layer.visible = True  # Visible by default
        m.add_layer(classification_layer)
        print("[STEP2] Added Flood Classification layer")

        # Layer 4: Model Uncertainty (HIDDEN by default)
        uncertainty_layer = get_leaflet_tile_layer(
            tile_clients['output'],
            name="Model Uncertainty",
            indexes=[2],
            colormap='rdylgn_r',
            vmin=0.0, vmax=1.0, opacity=0.7
        )
        uncertainty_layer.visible = False  # Hidden by default
        m.add_layer(uncertainty_layer)
        print("[STEP2] Added Uncertainty layer (hidden by default)")

        # Layer 5: Watershed boundary (always on top, always visible)
        watershed_layer = _create_watershed_layer()
        if watershed_layer:
            m.add_layer(watershed_layer)
            print("[STEP2] Added watershed boundary overlay")

        # Re-enable dragging
        if hasattr(m, 'dragging'):
            m.dragging = True

        print(f"[STEP2] Rendered all layers for event: {current_event_date}")


    # Sync map when event changes
    def sync_map_state():
        if not current_event_date:
            return
        
        print(f"[STEP2] Switching to event: {current_event_date}")
        
        # Get pre-initialized TileClients (no creation, no shutdown)
        current_clients = _get_clients_for_event(current_event_date)
        
        # Update preview image
        file_info = FILE_MAPPING.get(current_event_date, {})
        preview_image_path.set(str(file_info.get('preview')) if file_info.get('preview') else None)
        
        # Reset map viewport
        cx, cy, zoom = get_map_center()
        map_widget.center = [cy, cx]
        map_widget.zoom = zoom
        
        # Update all map layers
        update_layers(current_clients, current_event_date)

    # Trigger sync when event changes (no layer_mode dependency anymore)
    solara.use_effect(sync_map_state, dependencies=[current_event_date])
    
    # Helper function to create chart as base64 data URL
    # ========================================================================
    # UI Layout
    # ========================================================================

    with solara.Column(style={"height": "100vh"}):
        solara.Title(STEP2_TITLE)

        with solara.Sidebar():
            # Event Selection
            solara.Markdown("### Event Selection")

            if events_df is not None and not events_df.empty:
                # Event dropdown
                available_dates = events_df['datetime'].tolist()

                def on_event_change(new_date):
                    selected_event_date.set(new_date)
                    # Update metadata
                    event_row = events_df[events_df['datetime'] == new_date].iloc[0]
                    selected_event_metadata.set({
                        'rank': int(event_row['rank']),
                        'datetime': event_row['datetime'],
                        'score': float(event_row['score'])
                    })

                solara.Select(
                    label="Select Event",
                    value=selected_event_date,
                    values=available_dates,
                    on_value=on_event_change
                )

                # Event metadata and preview in one card with controlled height
                with solara.Card(elevation=0, style={"margin-top": "0.5rem", "margin-bottom": "1rem"}):
                    if current_metadata:
                        with solara.Column(gap="4px"):
                            # Show return period from state
                            return_period_display = state.selected_return_period.value.replace('T_', '') + '-year'
                            solara.Text(f"Return Period: {return_period_display}", style={"font-weight": "bold"})
                            solara.Text(f"Rank: {current_metadata.get('rank', 'N/A')}", style={"font-weight": "bold"})
                            solara.Text(f"Date: {current_metadata.get('datetime', 'N/A')}")
                            solara.Text(f"RMSE: {current_metadata.get('score', 'N/A'):.4f}")

                    solara.Markdown("---")

                    # Preview image with fixed height container
                    preview_path = preview_image_path.value
                    if preview_path and os.path.exists(preview_path):
                        # Use HTML for better control over image styling
                        import base64
                        try:
                            with open(preview_path, 'rb') as f:
                                img_data = base64.b64encode(f.read()).decode()
                            html = f'''
                            <div style="height: 200px; display: flex; justify-content: center; align-items: center; background-color: #f0f0f0; border-radius: 4px;">
                                <img src="data:image/png;base64,{img_data}" style="max-height: 100%; max-width: 100%; object-fit: contain;">
                            </div>
                            '''
                            solara.HTML(unsafe_innerHTML=html)
                        except Exception as e:
                            print(f"[STEP2] Error loading preview: {e}")
                            solara.Markdown("_Preview load error_", style={"color": "red", "font-style": "italic"})
                    else:
                        solara.Markdown("_Preview not available_", style={"color": "gray", "font-style": "italic"})

            else:
                # Single event mode (fallback)
                with solara.Card(elevation=0):
                    solara.Markdown(f"**Event Date:** `{current_event_date}`")
                    solara.Markdown(f"**Return Period:** `{state.selected_return_period.value}`")

            solara.Markdown("---")

            # Map view reset button
            solara.Markdown("### Map View")
            def reset_map_view():
                """Reset map to focus on selected watershed."""
                if map_widget:
                    cx, cy, zoom = get_map_center()
                    map_widget.center = [cy, cx]
                    map_widget.zoom = zoom
                    print(f"[STEP2] Map view reset to watershed center: ({cy:.4f}, {cx:.4f}), zoom={zoom}")

            solara.Button(
                "Reset Map View to Watershed",
                on_click=reset_map_view,
                block=True,
                color="primary",
                style={"margin-bottom": "1rem"}
            )

            solara.Markdown("---")

            solara.Markdown("### Layers Info")
            solara.Markdown("")
            solara.Markdown("**Default visibility:**")
            solara.Markdown("- Sentinel-2 RGB")
            solara.Markdown("- Flood Classification")
            solara.Markdown("- Watershed Boundary")
            solara.Markdown("- Permanent Water (hidden)")
            solara.Markdown("- Model Uncertainty (hidden)")

            solara.Markdown("---")

            solara.Markdown("### Legend")
            with solara.Card(elevation=0):
                # Combined legend for all layers
                solara.HTML(unsafe_innerHTML="""
                    <div style="font-size: 14px; line-height: 1.8;">
                        <p style="margin-top: 0; font-weight: bold;">Flood Classification:</p>
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="display: inline-block; width: 20px; height: 14px; background-color: #000000; margin-right: 8px; border: 1px solid #999;"></span>
                            <span><strong>0</strong>: Invalid</span>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="display: inline-block; width: 20px; height: 14px; background-color: #d2b48c; margin-right: 8px; border: 1px solid #999;"></span>
                            <span><strong>1</strong>: Land (Tan)</span>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="display: inline-block; width: 20px; height: 14px; background-color: #ff0000; margin-right: 8px; border: 1px solid #999;"></span>
                            <span><strong>2</strong>: Water (Red)</span>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <span style="display: inline-block; width: 20px; height: 14px; background-color: #ffffff; margin-right: 8px; border: 1px solid #999;"></span>
                            <span><strong>3</strong>: Cloud (White)</span>
                        </div>

                        <p style="font-weight: bold; margin-top: 8px;">Permanent Water:</p>
                        <div style="display: flex; align-items: center; margin-bottom: 12px;">
                            <span style="display: inline-block; width: 20px; height: 14px; background-color: #0000FF; margin-right: 8px; border: 1px solid #999;"></span>
                            <span>Permanent water (Pure Blue)</span>
                        </div>

                        <p style="font-weight: bold; margin-top: 8px;">Model Uncertainty:</p>
                        <div style="display: flex; align-items: center; margin-bottom: 4px;">
                            <span style="display: inline-block; width: 20px; height: 14px; background: linear-gradient(to right, #d73027, #fee08b, #1a9850); margin-right: 8px; border: 1px solid #999;"></span>
                            <span>Red (High) → Yellow → Green (Low)</span>
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 4px;">
                            Values: 0 (certain) to 1 (uncertain)
                        </div>
                    </div>
                """)

        # Display map (outside sidebar, inside column)
        solara.display(map_widget)

        # # Analytics Panel (only show if we have analog events)
        # if events_df is not None and not events_df.empty:
        #     solara.Markdown("## Analytics Panel")
            
            # with solara.Card(style={"margin-top": "1rem", "padding": "1rem"}):
            #     with solara.Columns([3, 7]):  # 3:7 ratio - Left: catalog, Right: details
            #         # Left: Event Catalog Table (30%)
            #         with solara.Column():
            #             solara.Markdown("### Event Catalog")
            #             # Display only relevant columns
            #             display_df = events_df[['rank', 'datetime', 'score']].copy()
            #             solara.DataFrame(display_df, items_per_page=10)

            #         # Right: Selected Event Details (70%)
            #         with solara.Column():
            #             solara.Markdown("### Selected Event Details")
            #             if current_event_date:
            #                 selected_row = events_df[events_df['datetime'] == current_event_date]
            #                 if not selected_row.empty:
            #                     with solara.Card(elevation=0, style={"padding": "1rem"}):
            #                         # Event metadata
            #                         return_period_display = state.selected_return_period.value.replace('T_', '') + '-year'
            #                         solara.Markdown(f"**Return Period:** {return_period_display}")
            #                         solara.Markdown(f"**Date:** {current_event_date}")
            #                         solara.Markdown(f"**Rank:** {selected_row['rank'].values[0]}")
            #                         solara.Markdown(f"**RMSE Score:** {selected_row['score'].values[0]:.4f}")
                                    
            #                         solara.Markdown("---")
                                    
            #                         # GloFAS Analogue Plot
            #                         plot_path = get_glofas_plot_path(current_event_date)
            #                         if plot_path:
            #                             solara.Markdown("**GloFAS Analogue Analysis:**")
            #                             try:
            #                                 with open(plot_path, "rb") as f:
            #                                     img_data = base64.b64encode(f.read()).decode()
            #                                 solara.HTML(unsafe_innerHTML=f'''
            #                                     <div style="margin-top: 1rem;">
            #                                         <img src="data:image/png;base64,{img_data}" style="width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px;">
            #                                     </div>
            #                                 ''')
            #                             except Exception as e:
            #                                 solara.Error(f"Failed to load plot: {e}")
            #                         else:
            #                             solara.Warning(f"Plot not found for {current_event_date}")
            #                 else:
            #                     solara.Info("Event not found in catalog")
            #             else:
            #                 solara.Info("No event selected")


if __name__ == "__main__":
    Page()
