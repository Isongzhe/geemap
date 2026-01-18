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

**Step 1: Watershed Selection** (`src/step1/`)
- Interactive map displaying Sentinel-2 footprint and HydroBASINS watersheds
- User selects watershed by clicking on map or dropdown
- Selection is persisted to `dataset/config.yaml`

**Step 2: Flood Visualization** (`src/step2/`)
- Displays three data layers using COG files:
  - Input (Sentinel-2 from `input_path`)
  - Flood Classification (from `output_path` band 1)
  - Uncertainty (from `output_path` band 2)
- Split-view comparison mode
- Confidence slider to filter uncertainty visualization

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

When running on remote server (e.g., NAS via SSH), forward this port:
- **8765**: Solara Web Interface (only port needed)

```bash
ssh -L 8765:localhost:8765 user@remote-server
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
- `model.input_path`: Sentinel-2 COG file path
- `model.output_path`: Flood model output COG file path (2 bands: classification, uncertainty)
- `watershed.path`: HydroBASINS shapefile path
- `watershed.default_id`: Currently selected watershed ID

### State Management

**`src/state.py`**: Global reactive state for navigation
- `current_step = solara.reactive(1)` - Navigation between steps

**Step-specific reactive state** (defined in each `app.py`):
- Step 1: `selected_watershed_id`, `candidates_gdf`, `map_center`
- Step 2: `uncertainty_threshold`, `show_split_map`, `map_layer_mode`

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

**`src/step2/app.py`**: Flood visualization UI
- **Key Function**: `get_tile_client(path, band=None)` - Creates TileClient for COG file
- Uses `localtileserver.get_leaflet_tile_layer()` to create map layers
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

### Tiles Not Loading

1. **Check COG format**: Ensure files are valid COG
   ```bash
   uv run rio cogeo validate /path/to/file.tif
   ```

2. **Check file paths**: Verify config.yaml paths are correct and files exist
   ```bash
   cat dataset/config.yaml
   ls -lh /path/to/input.tif
   ```

3. **Check logs**: View tmux logs for errors
   ```bash
   tmux attach -t geemap
   ```

4. **Verify port forwarding**: If on remote server, ensure port 8765 is forwarded

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
