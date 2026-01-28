<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Geemap Flood Visualization Application** that provides an interactive Solara-based web interface for watershed selection and flood model output visualization. The application uses Sentinel-2 satellite imagery as input and displays flood classification and uncertainty analysis from deep learning models.

**Key Feature**: Direct COG (Cloud Optimized GeoTIFF) visualization without backend server.

## Architecture

### Single Service Architecture (Simplified)

```
Browser (localhost:8765)
    ↓
Solara App (src/main.py)
    ├─ Frontend: ipyleaflet + geemap
    ├─ Tile Service: localtileserver (embedded)
    └─ Data: Direct COG file access
```

**No separate backend server needed**. The application uses `localtileserver.TileClient` embedded within the Solara app to serve map tiles directly from COG files.

### Two-Step Workflow

**Step 1: Watershed Selection** (`src/step1/`) - **Clean Start Workflow**
- Map starts with **empty global view** (no pre-loaded data to avoid freeze)
- User manually navigates via coordinate input or HYBAS_ID search
- User clicks **"Load Watersheds in View"** button to load viewport data
- Zoom guard: Requires zoom ≥ 8 to prevent loading too many features
- BBox partial reading: Only loads watersheds in viewport (90%+ RAM reduction)
- Auto-level selection: Zoom 10 → Level 8 (for demo watershed 3080576250)
- User clicks watershed to select, then submits to Step 2

**Step 2: Flood Analytics Dashboard** (`src/step2/`)
- **Multi-Event Selection**: Load and switch between analog flood events from CSV catalog
- **Permanent Water Overlay**: Blue semi-transparent layer showing baseline water boundaries
- Displays data layers using COG files:
  - Input (Sentinel-2 from `input_folder`, strict S2 requirement)
  - Flood Classification (from `output_folder` band 1)
  - Uncertainty (from `output_folder` band 2)
  - Permanent Water (from `permanent_water_path`, static overlay)
- Split-view comparison mode with permanent water overlay in Classification mode
- **Analytics Panel**: Event table and similarity score distribution chart with highlighted selection

### Data Flow

```
config.yaml
  ├─ input_path: /path/to/sentinel2.tif (COG)
  └─ output_path: /path/to/model_output.tif (COG, 2 bands)
         ↓
localtileserver.TileClient (in-process)
         ↓
XYZ Map Tiles (EPSG:3857)
         ↓
ipyleaflet Map Widget
```

## Commands

### Running the Application

```bash
./start.sh          # Start Solara app in tmux session
./stop.sh           # Stop all services
tmux attach -t geemap  # View logs/attach to session
```

The start script:
- Kills processes on port 8765
- Launches Solara UI on port 8765 in tmux
- Uses `uv run solara run src/main.py --host=0.0.0.0 --port=8765`

### Port Forwarding (Remote Server)

When running on remote server (e.g., NAS via SSH), forward these ports:
- **8765**: Solara Web Interface
- **9100**: TileServer for Input (Sentinel-2)
- **9101**: TileServer for Output (Model predictions)
- **9102**: TileServer for Permanent Water (static overlay)

```bash
ssh -L 8765:localhost:8765 -L 9100:localhost:9100 -L 9101:localhost:9101 -L 9102:localhost:9102 user@remote-server
```

### Development Commands

```bash
# Run Solara directly (without tmux)
uv run solara run src/main.py --host=0.0.0.0 --port=8765

# Test individual steps
uv run solara run src/step1/app.py
uv run solara run src/step2/app.py
```

## Key Files

### Configuration

**`dataset/config.yaml`**: Central configuration for data paths and watershed selection
- `analog_df.path`: CSV file path for analog event catalog (columns: rank, method, datetime, score)
- `analog_df.top_n`: Number of top-ranked events to load (default: 10)
- `model.event_date`: Fallback event date if analog catalog is not available
- `model.input_folder`: Folder containing Sentinel-2 COG files (strict S2 requirement)
- `model.output_folder`: Folder containing flood model output COG files (2 bands: classification, uncertainty)
- `model.permanent_water_path`: Permanent water COG file path (static overlay)
- `watershed.path`: HydroBASINS shapefile path
- `watershed.default_id`: Currently selected watershed ID

### State Management

**`src/state.py`**: Global reactive state for navigation
- `current_step = solara.reactive(1)` - Navigation between steps

**Step-specific reactive state** (defined in each `app.py`):
- Step 1: `selected_watershed_id`, `candidates_gdf`, `map_center`
- Step 2: `map_layer_mode`, `analog_events_df`, `selected_event_date`, `selected_event_metadata`, `preview_image_path`, `permanent_water_path`

### Core Components

**`src/main.py`**: Main entry point
- Routes between Step 1 and Step 2 based on `state.current_step.value`

**`src/step1/app.py`**: Watershed selection UI
- Uses geemap.Map with ipyleaflet
- Loads candidate watersheds from shapefile
- Handles watershed selection and saves to config.yaml

**`src/step1/utils.py`**: Watershed utilities
- `get_candidate_watersheds()`: Finds watersheds intersecting with image bounds
- `save_selected_watershed()`: Updates config.yaml with selected ID

**`src/step2/app.py`**: Flood analytics dashboard
- **Multi-Event System**: Loads analog catalog from CSV, provides event dropdown selector
- **Permanent Water**: Creates static TileClient for permanent water overlay (port 9102)
- **Dynamic Loading**: Recreates input/output TileClients when event changes
- **Analytics Panel**: DataFrame table + matplotlib box/strip plot with red star for selected event
- **Key Functions**:
  - `_create_permanent_water_client()` - Static water TileClient (singleton)
  - `_create_tile_clients_for_event()` - Dynamic event-based TileClients
  - `create_score_chart()` - Matplotlib chart with box plot + strip plot + highlighted selection
- Uses `localtileserver.get_leaflet_tile_layer()` to create map layers with permanent water overlay

**`src/step2/utils.py`**: Event discovery and catalog utilities
- `find_event_input()` - **Strict S2 requirement**: Only matches `S2_{date}*.tif` (no Landsat fallback)
- `find_event_output()` - Wildcard prefix: Matches `*{date}*_EDL.tif` (supports S2/LS)
- `find_event_preview()` - Finds PNG preview: `*{date}*_EDL_prediction.png`
- `load_analog_catalog()` - Loads CSV with columns: rank, method, datetime, score
- Supports three layer modes:
  - Input (Sentinel-2 RGB)
  - Classification (OUTPUT_PATH band 1, with colormap)
  - Uncertainty (OUTPUT_PATH band 2, with colormap and threshold)

**`src/step2/optimize_data.py`**: **DEPRECATED**
- Legacy data preprocessing script (downsampling, color rendering, cache generation)
- **Not used in current architecture** - direct COG access is preferred
- Kept for reference or future use if preprocessing is needed

## Data Model

### Input Requirements

**All GeoTIFF files must be in COG format** for optimal performance.

**Sentinel-2 Input** (`input_path`):
- Format: COG (Cloud Optimized GeoTIFF)
- Bands: At least 3 bands (RGB)
- CRS: Any (automatically handled)

**Model Output** (`output_path`):
- Format: COG (Cloud Optimized GeoTIFF)
- Band 1: Flood Classification (uint8, values 0-4)
  - 0: Invalid/Transparent
  - 1: Land (gray)
  - 2: Water (blue)
  - 3: Cloud (white)
  - 4: Flood (red)
- Band 2: Uncertainty (float32, range 0.0-1.0)
  - 0.0 = High confidence
  - 1.0 = Low confidence

### COG Validation

```bash
# Validate COG format
uv run rio cogeo validate /path/to/file.tif

# Convert to COG if needed
uv run rio cogeo create /path/to/input.tif /path/to/output_cog.tif
```

## Python Environment

Uses `uv` package manager with Python 3.13+

Key dependencies:
- `solara`: Reactive web framework
- `geemap`: Geospatial mapping library (wraps ipyleaflet)
- `geopandas`: Vector data handling
- `rioxarray`: Raster I/O
- `localtileserver`: COG tile serving (embedded)
- `rasterio`: Low-level raster operations

## Development Notes

### Solara Component Structure

- Each step is a `@solara.component` function in `src/stepN/app.py`
- `src/main.py` routes between steps based on `state.current_step.value`
- Use `solara.use_memo()` for expensive initialization (data loading, map creation, TileClient)
- Use `solara.use_effect()` for side effects triggered by reactive dependencies

### TileClient Caching

The `get_tile_client(path, band=None)` function uses `@functools.lru_cache(maxsize=3)` to cache TileClient instances. This prevents recreating tile servers for the same files.

### Map Layer Updates

`src/step2/app.py` uses `update_layers()` in `use_effect` to rebuild map layers when state changes:
- Must clear layers/controls before rebuilding to avoid duplicates
- Split-map mode uses `geemap.Map.split_map()` method
- Layer creation uses `get_leaflet_tile_layer(tile_client, name=..., opacity=..., colormap=...)`

### Colormap Support

localtileserver supports matplotlib colormaps:
- Classification: `viridis`, `plasma`, `tab10`, etc.
- Uncertainty: `RdYlGn_r` (Red=high uncertainty, Green=low)
- Can pass `vmin` and `vmax` to control colormap range

### Coordinate Systems

- All vector data (watersheds) should be in EPSG:4326
- Raster data can be in any CRS; bounds are transformed to 4326 for leaflet display
- Tile service uses EPSG:3857 (Web Mercator) for XYZ tiles (handled automatically by localtileserver)

## Troubleshooting

### Analog Catalog Issues

**Error**: "Analog catalog CSV not found"
- **Solution**: Verify `analog_df.path` in config.yaml exists
  ```bash
  ls -lh /path/to/analog_catalog.csv
  ```

**Error**: "CSV missing required columns"
- **Solution**: Ensure CSV has columns: `rank`, `datetime`, `score`
  ```bash
  head -5 /path/to/analog_catalog.csv
  ```

**Behavior**: Falls back to single event mode
- **Cause**: CSV not configured or loading failed
- **Expected**: App uses `model.event_date` as fallback

### Permanent Water Overlay Issues

**Problem**: Blue water overlay not visible
- **Check**: Verify `model.permanent_water_path` in config.yaml
- **Check**: Ensure file exists and is valid COG
  ```bash
  uv run rio cogeo validate /path/to/permanent_water.tif
  ```
- **Check**: Only visible in "Flood Classification" mode (not Uncertainty mode)

**Problem**: Port 9102 conflict
- **Solution**: Kill existing process or change `PERMANENT_WATER_PORT` in `src/config.py`

### Event Selection Issues

**Problem**: No preview images shown
- **Cause**: PNG files not found matching pattern `*{date}*_EDL_prediction.png`
- **Expected Behavior**: Shows "Preview not available" placeholder

**Problem**: Cannot load files for some events
- **Cause**: Missing S2 input files (strict requirement)
- **Solution**: Ensure all events in CSV have corresponding `S2_{date}*.tif` files

### Tiles Not Loading

1. **Check COG format**: Ensure files are valid COG
   ```bash
   uv run rio cogeo validate /path/to/file.tif
   ```

2. **Check file paths**: Verify config.yaml paths are correct and files exist
   ```bash
   cat dataset/config.yaml
   ls -lh /path/to/input_folder/
   ```

3. **Check logs**: View tmux logs for errors
   ```bash
   tmux attach -t geemap
   ```

4. **Verify port forwarding**: If on remote server, ensure ports 8765, 9100, 9101, 9102 are forwarded

### TileClient Errors

**Error**: "File is not a COG"
- **Solution**: Convert to COG using `rio cogeo create`

**Error**: "Cannot read band X"
- **Solution**: Verify file has required bands using `rio info`

**Error**: Performance issues / slow rendering
- **Solution**: Ensure COG has internal tiling and overviews

### Watershed Selection Issues

- Shapefile must overlap with Sentinel-2 image bounds
- `HYBAS_ID` field must exist in shapefile attributes
- Uses geopandas bbox filtering for performance

## File Structure

```
src/
├── main.py                 # Entry point, routes between steps
├── state.py                # Global reactive state
├── step1/
│   ├── app.py              # Watershed selection UI
│   └── utils.py            # Watershed query and save utilities
└── step2/
    ├── app.py              # Flood visualization UI (uses TileClient)
    ├── optimize_data.py    # DEPRECATED - not used in current architecture
    └── debug/              # Debug utilities (optional)

dataset/
├── config.yaml             # Main configuration (paths, watershed ID)
└── cache/                  # DEPRECATED - not used in current architecture

start.sh                    # Launch Solara in tmux
stop.sh                     # Stop tmux session
```

## Important Notes

1. **No Backend Server**: Unlike previous architecture, there is no separate Flask server. localtileserver runs embedded in the Solara app.

2. **Direct COG Access**: The app reads COG files directly from `input_path` and `output_path` in config.yaml. No preprocessing or cache directory is needed.

3. **Single Port**: Only port 8765 needs to be accessible (previously required both 8765 and 7777).

4. **Simplified Deployment**: Just run `./start.sh` - no need to manage multiple services.

5. **Earth Engine**: Step 2 initializes Earth Engine but it's not actively used. Initialization errors can be safely ignored.
