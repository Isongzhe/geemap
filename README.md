# Flood Visualization Web Application

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Solara](https://img.shields.io/badge/Solara-1.56+-green.svg)](https://solara.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An interactive web application for visualizing flood classification and uncertainty mapping using Solara, geemap, and Cloud Optimized GeoTIFF (COG). Built for analyzing Evidential Deep Learning (EDL) model outputs on Sentinel-2 imagery.

## Features

- **Interactive Map Visualization**: Display Sentinel-2 imagery and model predictions with tile-based rendering
- **Split-Map View**: Side-by-side comparison of input imagery and model outputs
- **Dual Visualization Modes**:
  - Flood Classification: Binary flood/non-flood mapping
  - Uncertainty Analysis: Model confidence visualization with interactive filtering
- **Watershed Integration**: Overlay watershed boundaries from HydroBASINS dataset
- **Remote Development Ready**: Configured for VSCode dev containers with auto port-forwarding

## Architecture

### Technology Stack

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (Client)                      │
│                http://localhost:8765                    │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │   Solara Server      │  Port 8765
         │   (Web Framework)    │
         │   src/main.py        │
         └───────────┬──────────┘
                     │
         ┌───────────▼──────────┐
         │  localtileserver     │  Port 9000 (fixed)
         │  (Tile Generation)   │
         │  TileClient          │
         └───────────┬──────────┘
                     │
         ┌───────────▼──────────┐
         │   COG Files          │
         │   - Input: 13-band   │
         │   - Output: 2-band   │
         └──────────────────────┘
```

**Key Components**:
- **Solara**: Reactive Python web framework for the UI
- **geemap**: Geospatial visualization library built on ipyleaflet
- **localtileserver**: On-the-fly tile generation from COG files
- **ipyleaflet**: Interactive Leaflet.js maps in Python

### Data Flow

1. **Tile Server Initialization**:
   - TileClient instances created for input (Sentinel-2) and output (predictions)
   - Fixed port (9000) for VSCode port forwarding compatibility
   - REST server listens on `0.0.0.0` for remote access

2. **Map Rendering**:
   - Browser requests tiles via `http://localhost:9000/api/tiles/{z}/{x}/{y}.png`
   - TileClient generates tiles on-demand from COG files
   - Layers composited with OpenStreetMap basemap

3. **Interactive Updates**:
   - Solara reactive state triggers re-rendering
   - SplitMapControl dynamically updates on mode/threshold changes
   - Controls properly cleaned up to prevent duplication

## Data Requirements

### Input Data Structure

```yaml
model:
  input_path: path/to/sentinel2_image.tif
    # Multi-spectral Sentinel-2 imagery
    # Format: (13, H, W) - 13 bands
    # CRS: EPSG:32630 (or other UTM zone)
    # Resolution: 10m
    
  output_path: path/to/model_predictions.tif
    # Model output with classification and uncertainty
    # Format: (2, H, W)
    # Band 1: Flood classification (0=no flood, 1=flood)
    # Band 2: Uncertainty estimation (0.0-1.0)

watershed:
  path: path/to/hybas_shapefile.shp
    # HydroBASINS Level 12 watershed boundaries
    # CRS: EPSG:4326
    # Required field: HYBAS_ID
    
  default_id: 5120274340
    # Target watershed HYBAS_ID
```

See [dataset/README.md](dataset/README.md) for detailed data specifications.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- Git
- VSCode with Dev Containers extension (optional, for containerized development)

### Installation

#### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd geemap

# Install dependencies with uv
uv sync

# Configure data paths
cp dataset/config.yaml.example dataset/config.yaml
# Edit dataset/config.yaml with your data paths
```

#### Option 2: Using pip

```bash
# Clone the repository
git clone <repository-url>
cd geemap

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure data paths
cp dataset/config.yaml.example dataset/config.yaml
# Edit dataset/config.yaml with your data paths
```

### Configuration

Edit `dataset/config.yaml`:

```yaml
model:
  input_path: "/absolute/path/to/sentinel2_input.tif"
  output_path: "/absolute/path/to/model_output.tif"

watershed:
  default_id: 5120274340  # Your target watershed ID
  path: "/absolute/path/to/hybas_shapefile.shp"
```

**Important**: Use absolute paths to avoid path resolution issues.

## Usage

### Starting the Application

#### Quick Start (Production Mode)

```bash
./start.sh
```

This script:
- Cleans up any existing processes on port 8765
- Starts Solara server in a tmux session
- Configures environment for remote access

Access the application at: **http://localhost:8765**

#### Manual Start (Development Mode)

```bash
uv run solara run src/main.py --host=0.0.0.0 --port=8765
```

### Stopping the Application

```bash
./stop.sh
```

### Application Workflow

1. **Access the Interface**:
   - Open browser to http://localhost:8765
   - The map will center on your configured watershed

2. **Visualization Modes**:
   - **Flood Classification**: Binary classification visualization
     - Green: High confidence flood areas
     - Purple: Non-flood areas
   
   - **Uncertainty**: Model confidence analysis
     - Colormap: Red (high uncertainty) → Yellow (medium) → Green (low uncertainty)
     - Use slider to adjust visualization range

3. **Interactive Controls**:
   - **Enable Split View**: Toggle side-by-side comparison
     - Left panel: Original Sentinel-2 imagery
     - Right panel: Model predictions
     - Drag the divider to compare regions
   
   - **Max Uncertainty** (Uncertainty mode only):
     - Adjust color mapping range
     - Lower values: Compress dynamic range for detail
     - Higher values: Expand range for full spectrum

4. **Map Interaction**:
   - Zoom: Mouse wheel or +/- buttons
   - Pan: Click and drag
   - Fullscreen: Click fullscreen button
   - Yellow boundary: Watershed boundary (fixed)

## Development

### Project Structure

```
geemap/
├── src/
│   ├── main.py              # Application entry point
│   ├── state.py             # Shared reactive state
│   ├── validator.py         # Configuration validation
│   ├── step1/               # Watershed selection (future feature)
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── utils.py
│   └── step2/               # Flood visualization (current)
│       ├── __init__.py
│       └── app.py           # Main visualization component
├── dataset/
│   ├── config.yaml          # Data configuration
│   └── README.md            # Data specifications
├── .vscode/
│   └── settings.json        # VSCode port forwarding config
├── pyproject.toml           # Python dependencies
├── start.sh                 # Production startup script
├── stop.sh                  # Shutdown script
└── README.md                # This file
```

### Key Configuration Parameters

In [src/step2/app.py](src/step2/app.py):

```python
# Tile server configuration
TILE_SERVER_HOST = '0.0.0.0'  # Listen on all interfaces
TILE_SERVER_PORT = 9000        # Fixed port for port forwarding
CLIENT_HOST = 'localhost'      # Client-side hostname

# Visualization parameters
CLASSIFICATION_COLORMAP = 'viridis'
UNCERTAINTY_COLORMAP = 'rdylgn_r'
WATERSHED_COLOR = '#FFD700'
WATERSHED_LINE_WIDTH = 4
```

### Remote Development (VSCode Dev Containers)

1. **Port Forwarding**:
   - Port 8765 (Solara): Auto-forwarded
   - Port 9000 (Tile Server): Auto-forwarded
   - Configuration in `.vscode/settings.json`

2. **Environment Variables**:
   ```python
   os.environ['REST_SERVER_HOST'] = '0.0.0.0'
   os.environ['LOCALTILESERVER_CLIENT_PORT'] = '9000'
   ```

3. **Verify Port Forwarding**:
   - Open VSCode → Ports tab (next to Terminal)
   - Ensure ports 8765 and 9000 are forwarded
   - If missing, manually add port 9000

## Troubleshooting

### Common Issues

#### 1. Tile Server Not Accessible

**Symptom**: Map shows basemap and watershed but no COG layers

**Solutions**:
- Check port 9000 is forwarded (VSCode Ports tab)
- Verify TileClient creation in logs:
  ```bash
  tail -f ~/.solara/logs/*.log | grep "TileClient"
  ```
- Manually forward port 9000:
  ```bash
  # In VSCode Command Palette (Cmd/Ctrl+Shift+P)
  > Forward a Port
  > Enter: 9000
  ```

#### 2. Split Panel Corruption

**Symptom**: Multiple split controls when adjusting uncertainty threshold

**Fix**: Already implemented in `update_layers()`:
```python
# Remove existing SplitMapControl to prevent duplication
controls_to_remove = [ctrl for ctrl in m.controls if isinstance(ctrl, SplitMapControl)]
for ctrl in controls_to_remove:
    m.remove_control(ctrl)
```

#### 3. File Not Found Errors

**Symptoms**:
- `[STEP2] Failed to create input TileClient`
- `Configuration error`

**Solutions**:
- Verify paths in `dataset/config.yaml` are absolute
- Check file permissions: `ls -lh /path/to/your/data.tif`
- Ensure files are COG format: `gdalinfo your_file.tif | grep -i "optimized"`

#### 4. Memory Issues with Large Files

**Symptoms**:
- Slow tile generation
- Application crashes

**Solutions**:
- Ensure files are COG format (tiled and overviews)
- Convert non-COG files:
  ```bash
  gdal_translate -co TILED=YES -co COMPRESS=DEFLATE \
                 -co COPY_SRC_OVERVIEWS=YES \
                 input.tif output_cog.tif
  gdaladdo -r average output_cog.tif 2 4 8 16
  ```

### Debug Mode

Enable detailed logging:

```bash
# View Solara server logs
tmux attach -t geemap

# Or check log files
tail -f ~/.solara/logs/*.log

# Python debug logging
export SOLARA_LOG_LEVEL=DEBUG
uv run solara run src/main.py
```

## Dependencies

Core dependencies (see `pyproject.toml` for complete list):

| Package | Version | Purpose |
|---------|---------|---------|
| solara | ≥1.56.0 | Reactive web framework |
| geemap | ≥0.36.6 | Geospatial visualization |
| localtileserver | ≥0.10.7 | COG tile serving |
| rioxarray | ≥0.20.0 | Raster data I/O |
| geopandas | ≥1.1.2 | Vector data processing |
| pyproj | ≥3.7.2 | Coordinate transformations |
| jupyter-server-proxy | ≥4.4.0 | Proxy support |

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Solara](https://solara.dev/) - Reactive Python web framework
- [geemap](https://geemap.org/) - Geospatial visualization library
- [localtileserver](https://github.com/banesullivan/localtileserver) - Local COG tile serving
- [HydroBASINS](https://www.hydrosheds.org/products/hydrobasins) - Watershed boundary dataset

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review [Troubleshooting](#troubleshooting) section

---

**Built with Python and Solara**
