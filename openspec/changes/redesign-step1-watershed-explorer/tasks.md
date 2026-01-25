# Tasks: Redesign Step 1 Watershed Explorer

## 1. Data Layer Updates
- [x] 1.1 Update `utils.py`: Add `get_shapefile_path(region, level)` function
- [x] 1.2 Update `utils.py`: Add `load_watershed_by_id(hybas_id)` search function
- [x] 1.3 Update `utils.py`: Add `get_watershed_bounds(gdf)` for zoom calculation
- [x] 1.4 Remove dependency on Sentinel-2 image bounds
- [x] 1.5 Add Siberia (si) region support
- [x] 1.6 Add `filter_nearby_watersheds()` for spatial filtering
- [x] 1.7 Add `find_watersheds_by_coordinates()` for buffer search

## 2. UI Components - Sidebar
- [x] 2.1 Add region dropdown (af, ar, as, au, eu, gr, na, sa, si)
- [x] 2.2 Add level selector (1-12)
- [x] 2.3 Add search mode toggle (Coordinates / HYBAS ID)
- [x] 2.4 Add HYBAS_ID search input field
- [x] 2.5 Add lat/lon input fields for coordinate search
- [x] 2.6 Add "Load Watersheds Boundaries" checkbox with ±5° buffer
- [x] 2.7 Add watershed info panel (HYBAS_ID, SUB_AREA, UP_AREA)
- [x] 2.8 Add Return Period selector

## 3. Map Interactions
- [x] 3.1 Implement HYBAS_ID search with auto region/level detection
- [x] 3.2 Implement coordinate search with map centering
- [x] 3.3 Implement click-to-select with metadata display
- [x] 3.4 Implement layer toggle functionality
- [x] 3.5 Fix map layer accumulation issue (use_effect with clear_layers)

## 4. State Management
- [x] 4.1 Add reactive state: region, level, search_mode, search_id, lat, lon
- [x] 4.2 Add reactive state: show_global_layer, show_context_layer
- [x] 4.3 Add reactive state: watershed_result_gdf, watershed_context_gdf, watershed_global_gdf
- [x] 4.4 Update global state.py with selected_return_period
- [x] 4.5 Pass selection to Step 2 on Submit

## 5. Testing & Validation
- [x] 5.1 Test region switching (including Siberia)
- [x] 5.2 Test HYBAS_ID search (e.g., 3080576250 for Siberia level 8)
- [x] 5.3 Test coordinate search and buffer loading
- [x] 5.4 Test metadata display
- [x] 5.5 Verify shapefile requirements (.shp, .shx, .dbf, .prj in same folder)
