# Change: Upgrade Step 2 to Flood Analytics Dashboard

## Why

The current Step 2 visualization shows a single flood event with basic layer toggling. However, users need to:
1. **Compare multiple flood events** - Understand similarities between historical flood events and select the most relevant analogs
2. **Visualize permanent water boundaries** - Distinguish normal water bodies from actual flood extent
3. **Analyze event similarity metrics** - Make data-driven decisions about which analog events best match the target scenario

**Current Limitations**:
- Single event visualization only
- No permanent water overlay to distinguish flood extent from normal water bodies
- No similarity scoring or event comparison interface
- No preview images for quick event identification

**Use Case**:
Flood analysts need to:
1. Select from ranked analog flood events based on similarity scores (from GloFAS data)
2. Visualize permanent water boundaries to understand baseline conditions
3. Compare satellite imagery and model predictions across different dates
4. Use similarity metrics (MAE score distribution) to evaluate analog quality

## What Changes

Transform Step 2 from static single-event viewer into dynamic **Flood Analytics Dashboard**:

1. **Multi-Event Selection System**:
   - Load analogue events from CSV (`analog_df.path` in config.yaml)
   - Event dropdown with rank-based sorting
   - Display similarity metrics (rank, datetime, MAE score)
   - Preview image display for quick visual reference

2. **Permanent Water Overlay**:
   - Load permanent water COG from `model.permanent_water_path`
   - Overlay as blue semi-transparent layer (opacity 0.5) on flood classification
   - Higher z-index to appear above classification layer
   - Helps distinguish normal water bodies from flood extent

3. **Dynamic Data Loading**:
   - **Strict S2 requirement**: Only load Sentinel-2 files matching `S2_{event_date}*.tif`
   - Support both `S2_` and `LS_` prefixed output files with wildcard pattern
   - Update TileClients when event selection changes
   - Find preview PNG files (`*{event_date}*_EDL_prediction.png`)

4. **Analytics Panel**:
   - **Table view**: Display all analog events with rank, datetime, score
   - **Box + Strip plot**: Show score distribution across all events
   - **Highlight selected event**: Mark current selection with red star in chart
   - Insight text: "Similarity Score Distribution (Lower is Better)"

5. **Split Map Enhancement**:
   - Left: Sentinel-2 input (unchanged)
   - Right: **Flood Classification + Permanent Water Overlay** (new composition)
   - Permanent water uses blue palette `['transparent', '#0000FF']`

## Impact

**Affected specs**:
- `specs/step2-visualization/spec.md` - Major enhancements to requirements

**Affected code**:
- `src/step2/utils.py` - Add event discovery functions, CSV loading, preview finding
- `src/step2/app.py` - Add event selector UI, analytics panel, permanent water layer, multi-event state management
- `dataset/config.yaml` - Add `analog_df` and `permanent_water_path` configuration

**Breaking Changes**:
- **BEHAVIOR CHANGE**: Step 2 now loads event list from CSV instead of single hardcoded event
- **BEHAVIOR CHANGE**: Map right side now shows composite layer (flood + permanent water) instead of single layer
- **ADDED**: New config sections `analog_df.path`, `analog_df.top_n`, `model.permanent_water_path`
- **MODIFIED**: `find_event_input()` now strictly requires S2 files (no fallback)
- **MODIFIED**: `find_event_output()` now uses wildcard prefix pattern to support both S2/LS files

**Performance Impact**:
- CSV loading: < 100ms (typically 10-50 events)
- Permanent water COG: Similar overhead to existing output layer (~1s initial load)
- Event switching: ~500ms (reload 2 TileClients)
- Analytics chart rendering: < 200ms (Plotly/Matplotlib)

**Dependencies**:
- pandas (already used)
- matplotlib or plotly (for box + strip plot)
- No new external dependencies
