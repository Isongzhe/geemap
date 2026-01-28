"""
Step 1: Watershed Selection Interface

This module uses Solara, a reactive UI framework for Python.
Key concepts:
- solara.reactive(): Creates reactive state variables that trigger UI updates when changed
- @solara.component: Decorator for defining reusable UI components
- solara.use_effect(): Runs side effects when dependencies change (like React useEffect)
- solara.use_memo(): Memoizes expensive computations (like React useMemo)
"""

import solara
import geemap
from ipyleaflet import GeoJSON
from src.step1.utils import (
    load_config,
    load_watersheds,
    load_watershed_by_id,
    get_watershed_bounds,
    calculate_zoom_level,
    save_selected_watershed,
    filter_nearby_watersheds,
    load_watersheds_in_viewport,
    get_level_for_zoom,
)
from src.config import (
    DEFAULT_CENTER,
    DEFAULT_ZOOM,
    STEP1_TITLE,
    get_return_period_config,
    parse_return_period_variables,
)
import src.state as state

# ============================================================================
# Reactive State (Local to Step 1)
# ============================================================================

selected_level = solara.reactive(2)  # Current level selection (default: 2)
selected_watershed_id = solara.reactive(None)  # Currently selected HYBAS_ID
selected_watershed_info = solara.reactive(None)  # Dict with SUB_AREA, UP_AREA metadata
watershed_result_gdf = solara.reactive(None)  # Single selected watershed GeoDataFrame
watershed_global_gdf = solara.reactive(None)  # Viewport watersheds
show_global_layer = solara.reactive(False)  # Whether to show watersheds (default: OFF for demo)
layer_version = solara.reactive(0)  # Version counter to force layer refresh

search_id_input = solara.reactive("")  # User input for HYBAS_ID search
lat_input = solara.reactive("")  # Latitude input
lon_input = solara.reactive("")  # Longitude input
map_center = solara.reactive(list(DEFAULT_CENTER))  # Current map center [lat, lon]
map_zoom = solara.reactive(DEFAULT_ZOOM)  # Current map zoom level
error_message = solara.reactive("")  # Error message to display
loading = solara.reactive(False)  # Loading state indicator
search_mode = solara.reactive("HYBAS ID")  # Search mode: "Coordinates" or "HYBAS ID"
selected_return_period = solara.reactive("T_200")  # Selected return period


# ============================================================================
# State Snapshot - For debugging and inspection
# ============================================================================

class Step1State:
    """Snapshot of all Step 1 reactive state values for easy inspection."""

    @staticmethod
    def get():
        """Get current state snapshot as a dict."""
        return {
            # Selection
            "level": selected_level.value,
            "watershed_id": selected_watershed_id.value,
            "watershed_info": selected_watershed_info.value,
            "return_period": selected_return_period.value,

            # Map
            "map_center": map_center.value,
            "map_zoom": map_zoom.value,

            # Layers
            "show_global": show_global_layer.value,
            "layer_version": layer_version.value,
            "global_gdf_count": len(watershed_global_gdf.value) if watershed_global_gdf.value is not None else 0,
            "result_gdf_count": len(watershed_result_gdf.value) if watershed_result_gdf.value is not None else 0,

            # Search
            "search_mode": search_mode.value,
            "search_id": search_id_input.value,
            "lat": lat_input.value,
            "lon": lon_input.value,

            # UI
            "loading": loading.value,
            "error": error_message.value,
        }

    @staticmethod
    def print():
        """Print current state in a readable format."""
        state = Step1State.get()
        print("\n" + "=" * 50)
        print("STEP 1 STATE SNAPSHOT")
        print("=" * 50)
        print(f"Level: {state['level']}")
        print(f"Watershed ID: {state['watershed_id']}")
        print(f"Return Period: {state['return_period']}")
        print(f"Map Center: {state['map_center']}")
        print(f"Map Zoom: {state['map_zoom']}")
        print("-" * 50)
        print(f"Show Global: {state['show_global']} ({state['global_gdf_count']} features)")
        print(f"Selected: {state['result_gdf_count']} features")
        print(f"Layer Version: {state['layer_version']}")
        print("-" * 50)
        print(f"Search Mode: {state['search_mode']}")
        print(f"Loading: {state['loading']}")
        print(f"Error: {state['error'] or 'None'}")
        print("=" * 50 + "\n")
        return state


# Export for external access
step1_state = Step1State()


# ==================== Initialization ====================

def load_initial_data():
    """
    Load initial config values and pre-fill UI fields.
    This runs once when the page loads (via solara.use_memo).
    
    NOTE: This only pre-fills the Region and Level selectors,
    it does NOT load any watershed data to avoid initial lag.
    """
    config = load_config()
    ws_config = config.get("watershed", {})

    # Set initial values from config to pre-fill UI
    level = ws_config.get("level", 2)
    default_id = ws_config.get("default_id")

    selected_level.set(level)

    if default_id:
        selected_watershed_id.set(default_id)


def load_viewport_watersheds():
    """
    Load watersheds in current viewport based on zoom level.
    Replaces load_global_watershed_data().
    """
    if not show_global_layer.value:
        watershed_global_gdf.set(None)
        layer_version.set(layer_version.value + 1)
        return

    loading.set(True)
    error_message.set("")

    center_lat, center_lon = map_center.value
    zoom = map_zoom.value

    print(f"[DEBUG app] Loading viewport: center=({center_lat:.2f},{center_lon:.2f}), zoom={zoom}")

    gdf = load_watersheds_in_viewport(
        center_lat=center_lat,
        center_lon=center_lon,
        zoom=zoom,
        max_features=5000
    )

    if len(gdf) > 0:
        watershed_global_gdf.set(gdf)
        level = get_level_for_zoom(zoom)
        error_message.set(f"Loaded {len(gdf)} watersheds (level {level})")
    else:
        watershed_global_gdf.set(None)
        error_message.set("No watersheds in viewport")

    layer_version.set(layer_version.value + 1)
    loading.set(False)




def handle_coordinates_search():
    """
    Search by coordinates (lat/lon) - only moves map, doesn't load ShP.
    
    Workflow:
    1. Validate lat/lon input
    2. Move map to the coordinates
    3. User can then manually enable "Load ShP" to load ±5° watersheds
    """
    lat_text = lat_input.value.strip()
    lon_text = lon_input.value.strip()
    
    if not lat_text or not lon_text:
        error_message.set("Please enter both latitude and longitude")
        return
    
    try:
        lat = float(lat_text)
        lon = float(lon_text)
    except ValueError:
        error_message.set("Invalid coordinate format")
        return
    
    # Validate coordinate range
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        error_message.set("Coordinates out of range")
        return
    
    print(f"[DEBUG coordinates_search] Setting map_center to [{lat}, {lon}]")
    print(f"[DEBUG coordinates_search] Before: map_center.value = {map_center.value}")

    # Move map to the coordinates
    map_center.set([lat, lon])
    map_zoom.set(8)

    # Auto-enable watershed layer to show nearby watersheds
    show_global_layer.set(True)

    print(f"[DEBUG coordinates_search] After: map_center.value = {map_center.value}")
    error_message.set(f"Map centered at ({lat:.2f}, {lon:.2f}). Loading watersheds...")


def handle_search():
    """
    Unified search handler that dispatches to appropriate search function
    based on current search mode (Coordinates or HYBAS ID).
    """
    if search_mode.value == "Coordinates":
        handle_coordinates_search()
    else:  # HYBAS ID mode
        handle_hybas_id_search()


def handle_hybas_id_search():
    """
    Search for watershed by HYBAS_ID.

    Workflow:
    1. Parse HYBAS_ID to determine region and level (from ID structure)
    2. Find the watershed and highlight it
    3. Center map on the watershed
    4. Viewport loading will automatically load nearby watersheds
    """
    search_text = search_id_input.value.strip()
    if not search_text:
        error_message.set("Please enter a HYBAS_ID")
        return

    try:
        hybas_id = int(search_text)
    except ValueError:
        error_message.set("Invalid HYBAS_ID format")
        return

    loading.set(True)
    error_message.set("")

    result_gdf, region, level = load_watershed_by_id(hybas_id)

    if result_gdf is not None and not result_gdf.empty:
        selected_level.set(level)
        selected_watershed_id.set(hybas_id)
        watershed_result_gdf.set(result_gdf)

        row = result_gdf.iloc[0]
        selected_watershed_info.set({
            'HYBAS_ID': hybas_id,
            'SUB_AREA': row.get('SUB_AREA', 'N/A'),
            'UP_AREA': row.get('UP_AREA', 'N/A'),
        })

        bounds = get_watershed_bounds(result_gdf)
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        zoom = calculate_zoom_level(bounds)

        map_center.set([center_lat, center_lon])
        map_zoom.set(zoom)
        error_message.set(f"Found watershed {hybas_id}")
    else:
        error_message.set(f"Watershed {hybas_id} not found")

    loading.set(False)


# ==================== Callback Functions ====================

def handle_goto_coords():
    """
    Navigate map to specified lat/lon coordinates.
    
    Users can input latitude and longitude to jump to a specific location.
    If both fields are empty, resets to global view.
    
    NOTE: This is different from handle_coordinates_search().
    This function only moves the map, doesn't search for watersheds.
    """
    try:
        lat = float(lat_input.value) if lat_input.value.strip() else None
        lon = float(lon_input.value) if lon_input.value.strip() else None

        if lat is not None and lon is not None:
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                map_center.set([lat, lon])
                map_zoom.set(10)
                error_message.set("")
            else:
                error_message.set("Coordinates out of range")
        # If coordinates are empty, do nothing - let user control the map
    except ValueError:
        error_message.set("Invalid coordinate format")


def handle_submit():
    """
    Submit selected watershed and return period to Step 2.
    Saves to global state and navigates to visualization page.
    """
    current_id = selected_watershed_id.value
    if current_id is None:
        error_message.set("Please select a watershed first")
        return

    result_gdf = watershed_result_gdf.value
    if result_gdf is None or result_gdf.empty:
        error_message.set("No watershed geometry available")
        return

    # Save to global state (shared across steps)
    state.selected_watershed_id.set(current_id)
    state.selected_return_period.set(selected_return_period.value)

    # Convert GeoDataFrame to GeoJSON for Step 2
    watershed_geojson = result_gdf.__geo_interface__
    state.selected_watershed_geojson.set(watershed_geojson)

    # Save watershed info to config
    save_selected_watershed(current_id, level=selected_level.value)

    print(f"[STEP1] Submit: Watershed={current_id}, Return Period={selected_return_period.value}")
    print(f"[STEP1] GeoJSON saved to global state")

    # Start transition
    state.is_transitioning.set(True)

    # Navigate to Step 2 after transition delay
    import time
    import threading

    def navigate_after_delay():
        time.sleep(5)
        state.current_step.set(2)
        state.is_transitioning.set(False)

    threading.Thread(target=navigate_after_delay, daemon=True).start()


@solara.component
def Page():
    """
    Main application component for Step 1: Watershed Selection.
    
    This function is decorated with @solara.component, which makes it a reactive UI component.
    Solara will automatically re-render this component when any reactive state it depends on changes.
    """
    
    # Load initial data once when page mounts (similar to React useEffect with empty dependencies)
    # solara.use_memo ensures this runs exactly once, not on every re-render
    solara.use_memo(load_initial_data, dependencies=[])

    # Load viewport watersheds only when show_global_layer changes
    # (not on zoom changes - user must click "Load Watersheds in View" button)
    solara.use_effect(
        load_viewport_watersheds,
        [show_global_layer.value]  # Removed map_zoom.value
    )

    # Get current state values (these will update when reactive state changes)
    current_id = selected_watershed_id.value
    result_gdf = watershed_result_gdf.value  # Selected watershed
    global_gdf = watershed_global_gdf.value  # Viewport watersheds
    show_global = show_global_layer.value  # Whether to show global layer
    layer_ver = layer_version.value  # Version counter for forcing updates
    info = selected_watershed_info.value
    is_loading = loading.value
    error = error_message.value
    
    # Debug: Print state snapshot on each render (disabled for performance)
    # Step1State.print()

    # Determine if showing transition overlay
    show_transition = state.is_transitioning.value

    with solara.Column(style={"height": "100vh"}):
        solara.Title(STEP1_TITLE)

        with solara.Sidebar():
            solara.Markdown("## Watershed Explorer")

            # Return Period Selection
            with solara.Card("Return Period", elevation=0, style={"margin-bottom": "1rem"}):
                solara.Markdown("_Select flood return period for analysis_")
                
                # Get return period options from config
                rp_config = get_return_period_config()
                variables_str = rp_config.get("variable", "T_100")
                rp_options = parse_return_period_variables(variables_str)
                
                solara.Select(
                    label="Return Period",
                    value=selected_return_period.value,
                    values=rp_options,
                    on_value=selected_return_period.set,
                )
                
                # Display selected value
                solara.Info(f"Selected: {selected_return_period.value}", dense=True)

            # Search Section
            with solara.Card("Search Watershed", elevation=0, style={"margin-bottom": "1rem"}):
                # Search mode toggle
                solara.ToggleButtonsSingle(
                    value=search_mode,
                    values=["Coordinates", "HYBAS ID"],
                )
                
                solara.Markdown("") #  spacing
                
                # Conditional input based on search mode
                if search_mode.value == "Coordinates":
                    solara.Markdown("_Search by Lat/Lon (±5° buffer)_")
                    with solara.Row():
                        solara.InputText(
                            label="Latitude",
                            value=lat_input.value,
                            on_value=lat_input.set,
                            style={"width": "100%"}
                        )
                        solara.InputText(
                            label="Longitude",
                            value=lon_input.value,
                            on_value=lon_input.set,
                            style={"width": "100%"}
                        )
                else:  # HYBAS ID mode
                    solara.Markdown("_Search by HYBAS ID_")
                    solara.InputText(
                        label="HYBAS_ID",
                        value=search_id_input.value,
                        on_value=search_id_input.set,
                        style={"width": "100%"}
                    )
                
                # Unified search button
                solara.Button(
                    "Search",
                    on_click=handle_search,
                    disabled=is_loading,
                    block=True,
                    color="primary",
                )


            # Map Layers Control
            with solara.Card("Map Layers", elevation=0, style={"margin-bottom": "1rem"}):
                def reload_watersheds():
                    """Reload watersheds in current viewport."""
                    show_global_layer.set(True)
                    layer_version.set(layer_version.value + 1)
                    print(f"[DEBUG] Reload watersheds triggered at zoom {map_zoom.value}")

                solara.Button(
                    "Load Watersheds in View",
                    on_click=reload_watersheds,
                    block=True,
                    color="primary",
                    style={"margin-bottom": "0.5rem"}
                )

                if show_global_layer.value and global_gdf is not None:
                    count = len(global_gdf)
                    level = get_level_for_zoom(map_zoom.value)
                    solara.Info(f"Showing {count} watersheds (level {level})", dense=True)

            # Watershed Info Panel
            with solara.Card("Selected Watershed", elevation=0, style={"margin-bottom": "1rem"}):
                if info:
                    sub_area = f"{info['SUB_AREA']:,.2f}" if isinstance(info['SUB_AREA'], (int, float)) else str(info['SUB_AREA'])
                    up_area = f"{info['UP_AREA']:,.2f}" if isinstance(info['UP_AREA'], (int, float)) else str(info['UP_AREA'])

                    solara.Info(f"**ID:** `{info['HYBAS_ID']}`", dense=True)
                    solara.Markdown(f"**Sub Area:** {sub_area} km²")
                    solara.Markdown(f"**Upstream Area:** {up_area} km²")

                    solara.Button(
                        "Submit & Continue to Step 2",
                        on_click=handle_submit,
                        color="primary",
                        block=True,
                        style={"margin-top": "1rem"},
                    )
                else:
                    solara.Text("Search or click a watershed to select")

            # Error Display
            if error:
                solara.Error(error)

            if is_loading:
                solara.ProgressLinear(True)

        # Map Component
        # Create map widget once (memoized) - DO NOT depend on map_center to avoid reset loop
        def create_map():
            """Create map widget once with default center, then update dynamically"""
            return geemap.Map(
                center=list(DEFAULT_CENTER),  # Use DEFAULT_CENTER for initialization only
                zoom=DEFAULT_ZOOM,
                toolbar_ctrl=False,
                draw_ctrl=False,
                data_ctrl=False,
                search_control=False,
                layers_control=True,
                height="800px",
                max_zoom=15,
                scale_ctrl=True,
                zoom_ctrl=True,
                measure_ctrl=True,
                
            )
        
        m = solara.use_memo(create_map, dependencies=[])
        
        # Store click handler references at component level
        click_handlers = solara.use_reactive({})

        def update_map_layers():
            """
            Update map layers when state changes.
            Simplified to only show viewport watersheds + selected watershed.
            """
            print(f"[DEBUG update_layers] Updating layers...")

            m.clear_layers()
            m.add_basemap("OpenStreetMap")

            def make_click_handler(source_gdf):
                def handler(event=None, feature=None, **kwargs):
                    if feature:
                        props = feature.get("properties", {})
                        hid = props.get("HYBAS_ID")
                        if hid:
                            selected_watershed_id.set(int(hid))
                            clicked_row = source_gdf[source_gdf['HYBAS_ID'] == int(hid)]
                            if not clicked_row.empty:
                                watershed_result_gdf.set(clicked_row)
                                selected_watershed_info.set({
                                    'HYBAS_ID': hid,
                                    'SUB_AREA': props.get('SUB_AREA', 'N/A'),
                                    'UP_AREA': props.get('UP_AREA', 'N/A'),
                                })
                return handler

            # Layer 1: Viewport watersheds (blue, clickable)
            if show_global and global_gdf is not None and not global_gdf.empty:
                print(f"[DEBUG update_layers] Adding {len(global_gdf)} viewport watersheds")
                style_global = {
                    'color': 'blue',
                    'fillOpacity': 0.2,
                    'weight': 2
                }
                json_global = GeoJSON(
                    data=global_gdf.__geo_interface__,
                    style=style_global,
                    hover_style={'fillOpacity': 0.35},
                    name="Watersheds"
                )
                json_global.on_click(make_click_handler(global_gdf))
                m.add_layer(json_global)

            # Layer 2: Selected watershed (highlighted)
            if result_gdf is not None and not result_gdf.empty:
                print(f"[DEBUG update_layers] Adding selected watershed")
                style_selected = {
                    'color': 'red',
                    'fillColor': 'yellow',
                    'fillOpacity': 0.5,
                    'weight': 3
                }
                json_selected = GeoJSON(
                    data=result_gdf.__geo_interface__,
                    style=style_selected,
                    name="Selected"
                )
                m.add_layer(json_selected)

            print(f"[DEBUG update_layers] Done")

        # Update layers when data changes (not on zoom/pan)
        solara.use_effect(
            update_map_layers,
            dependencies=[
                # map_center.value,  # Removed: panning doesn't need layer rebuild
                # map_zoom.value,    # Removed: zoom doesn't auto-reload (user clicks button)
                show_global,
                layer_ver,
                id(global_gdf),
                id(result_gdf),
            ]
        )

        # Update map view separately (efficient, no layer rebuild)
        def update_map_view():
            m.center = map_center.value
            m.zoom = map_zoom.value

        solara.use_effect(
            update_map_view,
            dependencies=[map_center.value, map_zoom.value]
        )

        solara.display(m)

        # Transition overlay (rendered on top of everything)
        if show_transition:
            with solara.Column(style={
                "position": "fixed",
                "top": "0",
                "left": "0",
                "width": "100vw",
                "height": "100vh",
                "background": "rgba(0, 0, 0, 0.8)",
                "z-index": "9999",
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
                "flex-direction": "column",
            }):
                solara.HTML(tag="div", unsafe_innerHTML="""
                    <div style="text-align: center; color: white;">
                        <h2 style="margin-bottom: 2rem; font-size: 2rem;">Loading Flood Visualization...</h2>
                        <div style="margin: 2rem 0;">
                            <div style="width: 80px; height: 80px; border: 8px solid #f3f3f3; border-top: 8px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                        </div>
                        <p style="font-size: 1.2rem; opacity: 0.8;">Preparing watershed data and model outputs...</p>
                    </div>
                    <style>
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    </style>
                """)


if __name__ == "__main__":
    Page()
