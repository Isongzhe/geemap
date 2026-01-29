# Refactor Step 2 Visualization Logic

## Goal
Fix rendering stability issues in Step 2 by eliminating duplicate code, improving `SplitMapControl` lifecycle management, and resolving closure/state synchronization issues.

## Problem Analysis
1.  **Duplicate Code**: `load_files_for_event` and `solara.use_effect` are defined twice in `app.py`, causing double execution and race conditions.
2.  **SplitMapControl Residue**: `ipyleaflet` controls are not being cleaned up thoroughly, leading to visual artifacts and potential crashes.
3.  **Stale Closures**: `update_layers` relies on global/closure state that may be stale.
4.  **Port Conflicts**: `TileClient` recreation might be hitting port conflicts if previous clients aren't fully released.

## Proposed Changes

### 1. Cleanup `app.py` Structure
- Remove duplicate definitions of `map_widget`, `load_files_for_event`, and `use_effect`.
- Consolidate initialization logic.

### 2. Robust Map Cleanup
- Implement a comprehensive cleanup routine that removes all controls and layers (except basemap) before updating.
- Ensure `SplitMapControl` is fully detached.

### 3. Explicit State Passing
- Refactor `update_layers` to accept `tile_clients`, `event_date`, and `layer_mode` as arguments.
- Pass fresh state from `load_files_for_event` directly to `update_layers`.

### 4. TileClient & Layer Optimization
- Check for existing TileClients on ports before recreation.
- Use unique layer names to prevent browser caching of old tiles.

## Files to Modify
- `src/step2/app.py`
