"""
Step 2: Flood Analytics Dashboard

This module provides an interactive analytics dashboard for flood event comparison
with analog selection, permanent water visualization, and similarity scoring.

Features:
- Multi-event selection from analog catalog
- Permanent water boundary overlay
- Split-map view for side-by-side comparison
- Analytics panel with event table and score distribution chart
- Watershed boundary overlay
"""

import os
import functools
from pathlib import Path
import base64
import solara
import geemap
import rioxarray
import ee
import geopandas as gpd
import pandas as pd
from ipyleaflet import GeoJSON, SplitMapControl, WidgetControl, FullScreenControl
from localtileserver import TileClient, get_leaflet_tile_layer
from matplotlib.colors import ListedColormap
import plotly.graph_objects as go
from pyproj import Transformer
from typing import Optional

import src.state as state
from src.config import (
    INPUT_TILE_PORT,
    OUTPUT_TILE_PORT,
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
)

# ============================================================================
# Global TileClient Singleton
# ============================================================================

# Module-level cache to prevent recreating TileClient on hot-reload
_tile_clients_cache = {}

# Module-level reference to current SplitMapControl (singleton)
_current_split_control = None

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

map_layer_mode = solara.reactive("Flood Classification")  # "Flood Classification" or "Uncertainty"

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
        data_ctrl=False,
        height="800px",
    )
    # Add modern layer manager for better UX
    m.add("layer_manager")
    return m


def _create_permanent_water_client():
    """
    Create TileClient for permanent water COG (static across all events).
    Uses module-level singleton cache to prevent port conflicts.

    Returns:
        TileClient or None
    """
    global _tile_clients_cache

    # Check if already cached
    if 'water' in _tile_clients_cache:
        return _tile_clients_cache['water']

    water_path = permanent_water_path.value
    if not water_path or not os.path.exists(water_path):
        print("[STEP2] Permanent water file not configured or not found")
        return None

    try:
        water_client = TileClient(
            water_path,
            port=PERMANENT_WATER_PORT,
            host='0.0.0.0',
            client_port=PERMANENT_WATER_PORT,
            client_host='localhost'
        )
        _tile_clients_cache['water'] = water_client
        print(f"[STEP2] Permanent water TileClient created on port {PERMANENT_WATER_PORT}")
        return water_client
    except Exception as e:
        print(f"[STEP2] Error creating permanent water TileClient: {e}")
        return None


def _create_tile_clients_for_event(event_date: str, input_folder: str, output_folder: str):
    """
    Create or update TileClient instances for a specific event.

    Permanent water client is NOT recreated (static across events).
    Input and output clients are recreated for each event change.

    Uses FILE_MAPPING cache for fast lookups instead of slow glob operations.

    Args:
        event_date: Event date string
        input_folder: Folder containing input files (not used if cache available)
        output_folder: Folder containing output files (not used if cache available)

    Returns:
        dict: Dictionary with 'input', 'output', and optionally 'water' TileClient instances
    """
    global _tile_clients_cache, INPUT_PATH, OUTPUT_PATH

    # Use cached file mapping for fast lookup
    if event_date in FILE_MAPPING:
        file_info = FILE_MAPPING[event_date]
        input_file = file_info.get('input')
        output_file = file_info.get('output')
        preview_file = file_info.get('preview')
        
        print(f"[STEP2] Using cached file mapping for event {event_date}")
    else:
        # Fallback to slow glob operations
        print(f"[STEP2] WARNING: Event {event_date} not in cache, using fallback discovery")
        input_file = find_event_input(event_date, input_folder)
        output_file = find_event_output(event_date, output_folder)
        preview_file = find_event_preview(event_date, output_folder)

    # Clear old input/output clients (but keep water client)
    # NOTE: Do NOT call shutdown() - localtileserver manages servers internally
    # Just remove the reference and let the new TileClient reuse the same port
    if 'input' in _tile_clients_cache:
        print(f"[STEP2] Removing old input TileClient reference (port {INPUT_TILE_PORT} will be reused)")
        del _tile_clients_cache['input']

    if 'output' in _tile_clients_cache:
        print(f"[STEP2] Removing old output TileClient reference (port {OUTPUT_TILE_PORT} will be reused)")
        del _tile_clients_cache['output']

    # Create Input TileClient (STRICT S2 CHECK)
    if input_file and input_file.exists():
        # Double-check: Ensure file is S2 prefix
        if not input_file.name.startswith('S2_'):
            print(f"[STEP2] ERROR: Input file is not S2: {input_file.name}")
            INPUT_PATH = None
        else:
            INPUT_PATH = str(input_file)
            _tile_clients_cache['input'] = TileClient(
                INPUT_PATH,
                port=INPUT_TILE_PORT,
                host='0.0.0.0',
                client_port=INPUT_TILE_PORT,
                client_host='localhost'
            )
            print(f"[STEP2] Input TileClient created for {event_date}: {input_file.name}")
    else:
        INPUT_PATH = None
        print(f"[STEP2] No S2 input file found for {event_date}")

    # Create Output TileClient (STRICT S2 CHECK)
    if output_file and output_file.exists():
        # Double-check: Ensure file is S2 prefix
        if not output_file.name.startswith('S2_'):
            print(f"[STEP2] ERROR: Output file is not S2: {output_file.name}")
            OUTPUT_PATH = None
        else:
            OUTPUT_PATH = str(output_file)
            _tile_clients_cache['output'] = TileClient(
                OUTPUT_PATH,
                port=OUTPUT_TILE_PORT,
                host='0.0.0.0',
                client_port=OUTPUT_TILE_PORT,
                client_host='localhost'
            )
            print(f"[STEP2] Output TileClient created for {event_date}: {output_file.name}")
    else:
        OUTPUT_PATH = None
        print(f"[STEP2] No S2 output file found for {event_date}")

    # Create permanent water client if not already created
    if 'water' not in _tile_clients_cache:
        _create_permanent_water_client()

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
    Main Solara component for the flood analytics dashboard.

    Provides:
    - Multi-event selection from analog catalog
    - Interactive map with COG tile layers
    - Permanent water overlay
    - Split-map view (always enabled)
    - Layer mode selection (Classification vs Uncertainty)
    - Analytics panel with table and chart
    - Watershed boundary overlay
    """
    # Lazy initialization - only runs once when Step 2 is first opened
    init_data = solara.use_memo(initialize_step2_data, dependencies=[])

    # Get configuration values
    input_folder = init_data.get("input_folder", "")
    output_folder = init_data.get("output_folder", "")

    # Reactive state values
    layer_mode = map_layer_mode.value
    current_event_date = selected_event_date.value
    current_metadata = selected_event_metadata.value
    events_df = analog_events_df.value

    # Create map widget (memoized)
    map_widget = solara.use_memo(_create_base_map, dependencies=[])

    # Dynamic file loading when event changes
    def load_files_for_event():
        if current_event_date and input_folder and output_folder:
            _create_tile_clients_for_event(current_event_date, input_folder, output_folder)

            # Update preview image path from cache
            if current_event_date in FILE_MAPPING:
                preview_file = FILE_MAPPING[current_event_date].get('preview')
                preview_image_path.set(str(preview_file) if preview_file else None)
            else:
                # Fallback to slow discovery
                preview_file = find_event_preview(current_event_date, output_folder)
                preview_image_path.set(str(preview_file) if preview_file else None)

            # Reset map view to watershed center after files are loaded
            if map_widget and INPUT_PATH:
                cx, cy, zoom = get_map_center()
                map_widget.center = [cy, cx]
                map_widget.zoom = zoom
                print(f"[STEP2] Map centered on watershed: ({cy:.4f}, {cx:.4f}), zoom={zoom}")

    solara.use_effect(load_files_for_event, dependencies=[current_event_date])

    # Get tile clients after they've been created
    tile_clients = _tile_clients_cache

    # Create watershed layer (memoized, updates when global state changes)
    watershed_layer = solara.use_memo(
        _create_watershed_layer,
        dependencies=[
            state.selected_watershed_geojson.value,
            state.selected_watershed_id.value
        ]
    )
    
    def update_layers():
        """
        Update map layers based on current layer mode.

        Split view is always enabled:
        - Classification mode: Left = Sentinel-2, Right = Classification
        - Uncertainty mode: Left = Classification, Right = Uncertainty
        """
        # Initialize water_layer to None
        water_layer = None
        global _current_split_control  # FIX: Ensure module-level variable is updated, not local
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
                # VERIFY: Ensure input is S2 file
                if INPUT_PATH and not Path(INPUT_PATH).name.startswith('S2_'):
                    print(f"[STEP2] ERROR: Input path is not S2: {Path(INPUT_PATH).name}")
                    return

                print(f"[STEP2] Creating left layer from: {Path(INPUT_PATH).name if INPUT_PATH else 'None'}")
                left_layer = get_leaflet_tile_layer(
                    tile_clients['input'],
                    name="Sentinel-2",
                    vmin=0,
                    vmax=3500,  # S2 DN scaling for proper visualization
                    opacity=1.0
                )

                # Right: Flood classification (base layer)
                # Create custom colormap with user-defined colors
                classification_cmap = ListedColormap(CLASSIFICATION_COLORMAP)
                right_layer = get_leaflet_tile_layer(
                    tile_clients['output'],
                    name="Classification",
                    indexes=[1],
                    colormap=classification_cmap,  # Custom ListedColormap
                    vmin=0,
                    vmax=4,
                    opacity=CLASSIFICATION_OPACITY  # 0.6 for semi-transparency
                )

                # Permanent water overlay (on top of classification)
                water_layer = None
                if 'water' in tile_clients:
                    try:
                        # Use blue color list directly
                        water_layer = get_leaflet_tile_layer(
                            tile_clients['water'],
                            name="Permanent Water",
                            colormap=['#00000000', '#0000FF'],  # List: transparent -> pure blue
                            opacity=PERMANENT_WATER_OPACITY  # 1.0 fully opaque
                        )
                    except Exception as e:
                        print(f"[STEP2] Could not create permanent water layer: {e}")
            else:  # Uncertainty mode
                # Left: Flood classification
                # Create custom colormap with user-defined colors
                classification_cmap = ListedColormap(CLASSIFICATION_COLORMAP)
                left_layer = get_leaflet_tile_layer(
                    tile_clients['output'],
                    name="Classification",
                    indexes=[1],
                    colormap=classification_cmap,  # Custom ListedColormap
                    vmin=0,
                    vmax=4,
                    opacity=CLASSIFICATION_OPACITY  # 0.6 for semi-transparency
                )

                # Right: Uncertainty map (full range 0-1)
                right_layer = get_leaflet_tile_layer(
                    tile_clients['output'],
                    name="Uncertainty",
                    indexes=[2],
                    colormap='rdylgn_r',  # rio-tiler uses lowercase
                    vmin=0.0,
                    vmax=1.0,  # Show full uncertainty range
                    opacity=0.7
                )

            # Add layers to map
            m.add_layer(left_layer)
            m.add_layer(right_layer)

            # Add permanent water overlay AFTER classification layer
            # In Classification mode: on top of right layer (classification)
            # In Uncertainty mode: on top of left layer (classification)
            if water_layer:
                m.add_layer(water_layer)
                print("[STEP2] Added permanent water overlay")

            # Create and store new SplitMapControl
            print(f"[STEP2 DEBUG] Creating SplitMapControl:")
            print(f"  - Left layer: {left_layer.name if hasattr(left_layer, 'name') else 'Unknown'}")
            print(f"  - Right layer: {right_layer.name if hasattr(right_layer, 'name') else 'Unknown'}")
            print(f"  - Mode: {layer_mode}")

            _current_split_control = SplitMapControl(left_layer=left_layer, right_layer=right_layer)
            m.add_control(_current_split_control)

            # FIX: Re-enable dragging after adding SplitMapControl
            # This fixes the ipyleaflet bug where panning/dragging gets disabled
            if hasattr(m, 'dragging'):
                m.dragging = True
                print("[STEP2] Re-enabled map dragging after SplitMapControl")

            # Always add watershed boundary on top
            if watershed_layer:
                m.add_layer(watershed_layer)

            print(f"[STEP2] ✅ Rendered split-map: {layer_mode}")

        except Exception as e:
            print(f"[STEP2] Error updating layers: {e}")
            import traceback
            traceback.print_exc()
    
    # Update layers when mode or event changes
    solara.use_effect(update_layers, dependencies=[layer_mode, current_event_date])
    
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
                            solara.Text(f"Rank: {current_metadata.get('rank', 'N/A')}", style={"font-weight": "bold"})
                            solara.Text(f"Date: {current_metadata.get('datetime', 'N/A')}")
                            solara.Text(f"MAE: {current_metadata.get('score', 'N/A'):.4f}")

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

            solara.Markdown("### Display Mode")

            # Layer mode selection
            solara.ToggleButtonsSingle(
                value=map_layer_mode,
                values=["Flood Classification", "Uncertainty"]
            )

            solara.Markdown("---")

            # Display legend based on mode
            if layer_mode == "Flood Classification":
                solara.Markdown("### Split View")
                solara.Markdown("**Left:** Sentinel-2 Original Image")
                solara.Markdown("**Right:** Flood Classification + Permanent Water")

                solara.Markdown("### Legend")
                with solara.Card(elevation=0):
                    # Use HTML for rectangular color boxes - simplified 4 categories
                    solara.HTML(unsafe_innerHTML="""
                        <div style="font-size: 14px; line-height: 1.8;">
                            <p style="margin-top: 0;"><strong>Classification:</strong></p>
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
                            <p><strong>Permanent Water:</strong></p>
                            <div style="display: flex; align-items: center;">
                                <span style="display: inline-block; width: 20px; height: 14px; background-color: #0000FF; margin-right: 8px; border: 1px solid #999;"></span>
                                <span>Permanent water (Pure Blue)</span>
                            </div>
                        </div>
                    """)
            else:  # Uncertainty mode
                solara.Markdown("### Split View")
                solara.Markdown("**Left:** Flood Classification + Permanent Water")
                solara.Markdown("**Right:** Uncertainty Map")

                solara.Markdown("### Legend")
                with solara.Card(elevation=0):
                    # Classification legend - simplified 4 categories
                    solara.HTML(unsafe_innerHTML="""
                        <div style="font-size: 14px; line-height: 1.8;">
                            <p style="margin-top: 0;"><strong>Classification:</strong></p>
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
                            <p><strong>Permanent Water:</strong></p>
                            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                                <span style="display: inline-block; width: 20px; height: 14px; background-color: #0000FF; margin-right: 8px; border: 1px solid #999;"></span>
                                <span>Permanent water (Pure Blue)</span>
                            </div>
                            <p><strong>Uncertainty:</strong></p>
                            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                                <span style="display: inline-block; width: 20px; height: 14px; background: linear-gradient(to right, #d73027, #fee08b, #1a9850); margin-right: 8px; border: 1px solid #999;"></span>
                                <span>Red (High) → Yellow → Green (Low)</span>
                            </div>
                            <div style="font-size: 12px; color: #666; margin-top: 4px;">
                                Values: 0 (certain) to 1 (uncertain)
                            </div>
                        </div>
                    """)

        # Display map
        solara.display(map_widget)

        # Analytics Panel (only show if we have analog events)
        if events_df is not None and not events_df.empty:
            with solara.Card(style={"margin-top": "1rem", "padding": "1rem"}):
                solara.Markdown("## Analytics Panel")

                with solara.Columns([1, 1]):
                    # Left: Event Table
                    with solara.Column():
                        solara.Markdown("### Event Catalog")
                        # Display only relevant columns
                        display_df = events_df[['rank', 'datetime', 'score']].copy()
                        solara.DataFrame(display_df, items_per_page=10)

                    # Right: Score Statistics (simplified text display)
                    with solara.Column():
                        solara.Markdown("### Score Statistics")
                        if events_df is not None and not events_df.empty:
                            with solara.Card(elevation=0):
                                solara.Markdown(f"**Total Events:** {len(events_df)}")
                                solara.Markdown(f"**Min Score:** {events_df['score'].min():.4f}")
                                solara.Markdown(f"**Max Score:** {events_df['score'].max():.4f}")
                                solara.Markdown(f"**Mean Score:** {events_df['score'].mean():.4f}")
                                solara.Markdown(f"**Median Score:** {events_df['score'].median():.4f}")

                                if current_event_date:
                                    selected_row = events_df[events_df['datetime'] == current_event_date]
                                    if not selected_row.empty:
                                        solara.Markdown("---")
                                        solara.Markdown("**Selected Event:**")
                                        solara.Markdown(f"🔴 Score: **{selected_row['score'].values[0]:.4f}**")
                                        solara.Markdown(f"🔴 Rank: **{selected_row['rank'].values[0]}**")


if __name__ == "__main__":
    Page()
