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
    get_available_regions,
    get_region_display_name,
    filter_nearby_watersheds,  # Spatial filtering to reduce frontend data
    find_watersheds_by_coordinates,  # Search watersheds by lat/lon
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

selected_region = solara.reactive("as")  # Current region selection
selected_level = solara.reactive(2)  # Current level selection (default: 2)
selected_watershed_id = solara.reactive(None)  # Currently selected HYBAS_ID
selected_watershed_info = solara.reactive(None)  # Dict with SUB_AREA, UP_AREA metadata
watershed_result_gdf = solara.reactive(None)  # Single selected watershed GeoDataFrame
watershed_context_gdf = solara.reactive(None)  # Nearby watersheds for context (optional)
watershed_global_gdf = solara.reactive(None)  # Global watersheds for current region/level
show_context_layer = solara.reactive(False)  # Whether to show nearby watersheds (default: off)
show_global_layer = solara.reactive(False)  # Whether to show global region/level shp (default: OFF, user controls manually)


search_id_input = solara.reactive("")  # User input for HYBAS_ID search
lat_input = solara.reactive("")  # Latitude input for coordinate navigation
lon_input = solara.reactive("")  # Longitude input for coordinate navigation
map_center = solara.reactive(list(DEFAULT_CENTER))  # Current map center [lat, lon]
map_zoom = solara.reactive(DEFAULT_ZOOM)  # Current map zoom level
error_message = solara.reactive("")  # Error message to display to user
loading = solara.reactive(False)  # Loading state indicator
search_mode = solara.reactive("Coordinates")  # Search mode: "Coordinates" or "HYBAS ID" (default: Coordinates)
selected_return_period = solara.reactive("T_200")  # Selected return period (default: T_200, only T_200+ available)


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
    region = ws_config.get("region", "as")
    level = ws_config.get("level", 2)
    default_id = ws_config.get("default_id")

    selected_region.set(region)
    selected_level.set(level)

    if default_id:
        selected_watershed_id.set(default_id)


def load_global_watershed_data():
    """
    Load watershed shapefile based on current settings.
    
    Behavior:
    - If user has moved map from default position (coordinates search): load ±5° buffer around map center
    - Otherwise: load entire region/level shapefile
    """
    if not show_global_layer.value:
        # User unchecked, clear the global layer
        watershed_global_gdf.set(None)
        return
    
    loading.set(True)
    error_message.set("")
    
    try:
        center = map_center.value
        # Check if user has moved map from default position (coordinates search)
        is_custom_location = center != list(DEFAULT_CENTER)
        
        print(f"[DEBUG load_global] map_center: {center}, DEFAULT_CENTER: {list(DEFAULT_CENTER)}")
        print(f"[DEBUG load_global] is_custom_location: {is_custom_location}")
        print(f"[DEBUG load_global] selected_region: {selected_region.value}, selected_level: {selected_level.value}")
        
        if is_custom_location:
            # Load ±5° buffer around current map center
            lat, lon = center
            print(f"[DEBUG load_global] Loading ±5° around ({lat}, {lon})")
            filtered_gdf = find_watersheds_by_coordinates(
                selected_region.value,
                selected_level.value,
                lat,
                lon,
                buffer_degrees=5.0
            )
            watershed_global_gdf.set(filtered_gdf)
            
            if filtered_gdf.empty:
                error_message.set(f"No watersheds found near ({lat:.2f}, {lon:.2f})")
            else:
                error_message.set(f"Loaded {len(filtered_gdf)} watersheds around map center")
        else:
            # Load entire region/level
            print(f"[DEBUG load_global] Loading entire region/level")
            gdf = load_watersheds(selected_region.value, selected_level.value)
            watershed_global_gdf.set(gdf)
            error_message.set("")
            
    except Exception as e:
        error_message.set(f"Error loading data: {str(e)}")
        watershed_global_gdf.set(None)
        show_global_layer.set(False)  # Auto-uncheck on error
    finally:
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
    
    # Simply move map to the coordinates
    map_center.set([lat, lon])
    map_zoom.set(8)
    
    print(f"[DEBUG coordinates_search] After: map_center.value = {map_center.value}")
    error_message.set(f"Map centered at ({lat:.2f}, {lon:.2f}). Enable 'Load shp' to show watersheds.")


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
    2. Load full shapefile for that region/level
    3. Apply spatial filtering to only keep nearby watersheds
    4. Update UI with filtered data (prevents WebSocket overload)
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

    # Step 1: Find the watershed (auto-detects region/level from ID)
    result_gdf, region, level = load_watershed_by_id(hybas_id)

    if result_gdf is not None and not result_gdf.empty:
        # Update state to match the found watershed
        selected_region.set(region)
        selected_level.set(level)
        selected_watershed_id.set(hybas_id)

        # Step 2: Load full watershed dataset for this region/level
        full_gdf = load_watersheds(region, level)
        
        # Step 3: Apply spatial filtering to get nearby watersheds (for optional context layer)
        filtered_gdf = filter_nearby_watersheds(full_gdf, hybas_id, expansion_factor=1.5)
        
        # Store the selected watershed and nearby context separately
        watershed_result_gdf.set(result_gdf)  # Always show the selected one
        watershed_context_gdf.set(filtered_gdf)  # Nearby watersheds (optional)

        # Step 4: Update info panel with watershed metadata
        row = result_gdf.iloc[0]
        selected_watershed_info.set({
            'HYBAS_ID': hybas_id,
            'SUB_AREA': row.get('SUB_AREA', 'N/A'),
            'UP_AREA': row.get('UP_AREA', 'N/A'),
        })

        # Step 5: Center map on the watershed
        bounds = get_watershed_bounds(result_gdf)
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        zoom = calculate_zoom_level(bounds)

        map_center.set([center_lat, center_lon])
        map_zoom.set(zoom)
        error_message.set("")
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
    
    # Save to global state (shared across steps)
    state.selected_watershed_id.set(current_id)
    state.selected_return_period.set(selected_return_period.value)
    
    # Save watershed info to config
    save_selected_watershed(current_id, selected_region.value, selected_level.value)
    
    print(f"[STEP1] Submit: Watershed={current_id}, Return Period={selected_return_period.value}")
    
    # Navigate to Step 2
    # solara.use_router().push("/step-2-visualization")  # Navigate to Step 2


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

    # REMOVED: Auto-loading on region/level change to improve performance
    # Watersheds are now loaded only when user searches by HYBAS_ID
    # This prevents WebSocket from being overwhelmed by thousands of polygons

    # Auto-load global shp when checkbox state or settings change
    solara.use_effect(
        load_global_watershed_data, 
        [show_global_layer.value, selected_region.value, selected_level.value, map_center.value]
    )

    # Get current state values (these will update when reactive state changes)
    current_id = selected_watershed_id.value
    result_gdf = watershed_result_gdf.value  # Selected watershed
    context_gdf = watershed_context_gdf.value  # Nearby watersheds
    global_gdf = watershed_global_gdf.value  # Global region/level shp
    show_context = show_context_layer.value  # Whether to show context layer
    show_global = show_global_layer.value  # Whether to show global layer
    info = selected_watershed_info.value
    is_loading = loading.value
    error = error_message.value
    
    # Debug: Print all reactive state values on each render
    print(f"\n{'='*60}")
    print(f"[DEBUG Page render] Reactive State:")
    print(f"  - selected_region: {selected_region.value}")
    print(f"  - selected_level: {selected_level.value}")
    print(f"  - map_center: {map_center.value}")
    print(f"  - map_zoom: {map_zoom.value}")
    print(f"  - search_mode: {search_mode.value}")
    print(f"  - selected_watershed_id: {current_id}")
    print(f"  - show_context_layer: {show_context}")
    print(f"  - show_global_layer: {show_global}")
    print(f"  - result_gdf: {result_gdf is not None and not result_gdf.empty if result_gdf is not None else None}")
    print(f"  - context_gdf: {len(context_gdf) if context_gdf is not None else None}")
    print(f"  - global_gdf: {len(global_gdf) if global_gdf is not None else None}")
    print(f"  - is_loading: {is_loading}")
    print(f"  - error: {error[:50] if error else None}")
    print(f"{'='*60}\n")

    with solara.Column(style={"height": "100vh"}):
        solara.Title(STEP1_TITLE)

        with solara.Sidebar():
            solara.Markdown("## Watershed Explorer")

            # Region & Level Selection
            with solara.Card("Region & Level", elevation=0, style={"margin-bottom": "1rem"}):
                solara.Markdown("_Settings for search and display_")
                
                regions = get_available_regions()
                regions_name = [get_region_display_name(region) for region in regions]
                
                # solara.Select(
                #     label="Region",
                #     value=selected_region.value,
                #     values=regions_name.value,
                #     on_value=selected_region.set,
                # )

                # solara.Select(
                #     label="Level",
                #     value=selected_level.value,
                #     values=list(range(1, 13)),  # 1 to 12
                #     on_value=selected_level.set,
                # )
                
                # Option to load shp - behavior depends on map position
                solara.Checkbox(
                    label=f"Load Watersheds Boundaries ({selected_region.value.upper()} Lv{selected_level.value})",
                    value=show_global,
                    on_value=show_global_layer.set,
                    disabled=is_loading,
                )
                if map_center.value != list(DEFAULT_CENTER):
                    solara.Info("Will load ±5° around map center", dense=True)

            # Return Period Selection
            with solara.Car
            ("Return Period", elevation=0, style={"margin-bottom": "1rem"}):
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


            # Watershed Info Panel
            with solara.Card("Selected Watershed", elevation=0, style={"margin-bottom": "1rem"}):
                if info:
                    # Format area values
                    sub_area = f"{info['SUB_AREA']:,.2f}" if isinstance(info['SUB_AREA'], (int, float)) else str(info['SUB_AREA'])
                    up_area = f"{info['UP_AREA']:,.2f}" if isinstance(info['UP_AREA'], (int, float)) else str(info['UP_AREA'])
                    
                    # Use Info component for better styling
                    solara.Info(f"**ID:** `{info['HYBAS_ID']}`", dense=True)
                    solara.Markdown(f" **Sub Area:** {sub_area} km²")
                    solara.Markdown(f" **Upstream Area:** {up_area} km²")
                    
                    # Option to show nearby watersheds for context
                    solara.Checkbox(
                        label="Show Nearby Watersheds",
                        value=show_context,
                        on_value=show_context_layer.set,
                    )
                else:
                    solara.Text("Click a watershed or search by ID")

            # Error Display
            if error:
                solara.Error(error)

            # Submit Button
            solara.Button(
                "Submit & Continue to Step 2",
                on_click=handle_submit,
                disabled=current_id is None,
                color="primary",
            )

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
            )
        
        m = solara.use_memo(create_map, dependencies=[])
        
        # Store click handler references at component level
        click_handlers = solara.use_reactive({})

        def update_map_layers():
            """
            Update all map layers and view in one effect.
            This ensures proper cleanup and prevents layer accumulation.
            """
            print(f"[DEBUG update_map_layers] Starting layer update...")
            print(f"  - map_center: {map_center.value}, map_zoom: {map_zoom.value}")
            print(f"  - show_global: {show_global}, global_gdf: {global_gdf is not None}")
            print(f"  - show_context: {show_context}, context_gdf: {context_gdf is not None}")
            print(f"  - result_gdf: {result_gdf is not None}")

            # Step 1: Clear all existing layers
            m.clear_layers()
            m.add_basemap("OpenStreetMap")

            # Step 2: Update map view
            m.center = map_center.value
            m.zoom = map_zoom.value

            # Step 3: Define click handler factory
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

            # Step 4: Add layers in order (bottom to top)

            # Layer 0: Global Region/Level ShP
            if show_global and global_gdf is not None and not global_gdf.empty:
                print(f"[DEBUG] Adding global layer with {len(global_gdf)} watersheds")
                style_global = {
                    'color': 'blue',
                    'fillOpacity': 0.2,
                    'weight': 2
                }
                json_global = GeoJSON(
                    data=global_gdf.__geo_interface__,
                    style=style_global,
                    hover_style={'fillOpacity': 0.35},
                    name=f"{selected_region.value.upper()} Level {selected_level.value} ShP"
                )
                json_global.on_click(make_click_handler(global_gdf))
                m.add_layer(json_global)

            # Layer 1: Nearby watersheds (context)
            if show_context and context_gdf is not None and not context_gdf.empty:
                print(f"[DEBUG] Adding context layer with {len(context_gdf)} watersheds")
                style_context = {'color': 'blue', 'fillOpacity': 0.1, 'weight': 1}
                json_context = GeoJSON(
                    data=context_gdf.__geo_interface__,
                    style=style_context,
                    hover_style={'fillOpacity': 0.3},
                    name="Nearby Watersheds"
                )
                json_context.on_click(make_click_handler(context_gdf))
                m.add_layer(json_context)

            # Layer 2: Selected watershed (top, highlighted)
            if result_gdf is not None and not result_gdf.empty:
                print(f"[DEBUG] Adding selected watershed layer")
                style_selected = {
                    'color': 'red',
                    'fillColor': 'yellow',
                    'fillOpacity': 0.5,
                    'weight': 3
                }
                json_selected = GeoJSON(
                    data=result_gdf.__geo_interface__,
                    style=style_selected,
                    name="Selected Watershed"
                )
                m.add_layer(json_selected)

            print(f"[DEBUG update_map_layers] Layer update complete")

        # Trigger layer update when any relevant state changes
        solara.use_effect(
            update_map_layers,
            dependencies=[
                map_center.value,
                map_zoom.value,
                show_global,
                show_context,
                global_gdf,
                context_gdf,
                result_gdf,
            ]
        )

        solara.display(m)


if __name__ == "__main__":
    Page()
