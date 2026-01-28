# Implementation Tasks

## 1. Add Viewport Calculation Functions
- [x] 1.1 Implement `calculate_viewport_bounds(center_lat, center_lon, zoom, buffer_factor)` in utils.py
- [x] 1.2 Implement `get_level_for_zoom(zoom)` mapping function in utils.py
- [x] 1.3 Add region bounding box data and `find_intersecting_regions(minx, miny, maxx, maxy)` in utils.py

## 2. Implement Viewport-Based Loading
- [x] 2.1 Implement `load_watersheds_in_viewport(center_lat, center_lon, zoom, max_features)` in utils.py
- [x] 2.2 Add feature limit enforcement (max 5000)
- [x] 2.3 Add debug logging for viewport bounds and feature counts

## 3. Update App.py Loading Logic
- [x] 3.1 Replace `load_global_watershed_data()` with `load_viewport_watersheds()`
- [x] 3.2 Update effect hook to trigger on `map_zoom` instead of `selected_level`
- [x] 3.3 Remove pan-based reloading (keep zoom-only triggers)

## 4. Simplify Reactive State
- [x] 4.1 Remove `watershed_context_gdf` reactive state
- [x] 4.2 Remove `show_context_layer` reactive state
- [x] 4.3 Remove `selected_region` reactive state (not applicable, was never used)
- [x] 4.4 Update state snapshot class to match new state

## 5. Simplify UI Components
- [x] 5.1 Remove region selector from sidebar (not applicable, was never in UI)
- [x] 5.2 Remove level selector from sidebar (keeping for manual override, not implemented in this phase)
- [x] 5.3 Remove "Show Nearby Watersheds" checkbox
- [x] 5.4 Simplify error messages (already clean, no icons used)

## 6. Update Layer Rendering
- [x] 6.1 Simplify `update_map_layers()` to only render global + selected layers
- [x] 6.2 Remove context layer rendering logic
- [x] 6.3 Update layer dependencies in effect hook

## 7. Testing and Validation
- [ ] 7.1 Test zoom 3 → level 1 loading (< 100 features)
- [ ] 7.2 Test zoom 10 → level 5 loading (~500 features)
- [ ] 7.3 Test zoom 15 → level 8 loading (~100 features in viewport)
- [ ] 7.4 Verify HYBAS_ID search for 3080576250 works
- [ ] 7.5 Verify no WebSocket timeout at any zoom level
- [ ] 7.6 Record demo video showing smooth interaction

## 8. Update Documentation
- [ ] 8.1 Update CLAUDE.md with new loading strategy
- [ ] 8.2 Update dataset/README.md if needed
- [ ] 8.3 Add comments explaining viewport calculation logic
