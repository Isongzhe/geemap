# Project Context

## Purpose

Geemap Flood Visualization Application - 一個互動式 Solara 網頁應用程式，用於流域選擇和洪水模型輸出視覺化。使用 Sentinel-2 衛星影像作為輸入，顯示深度學習模型的洪水分類和不確定性分析結果。

**核心特色**: 直接 COG (Cloud Optimized GeoTIFF) 視覺化，無需後端伺服器。

## Tech Stack

- **Framework**: Solara (Reactive web framework)
- **Mapping**: geemap + ipyleaflet
- **Tile Service**: localtileserver (embedded COG tile server)
- **Data Processing**: geopandas, rioxarray, rasterio
- **Runtime**: Python 3.13+, uv package manager
- **Earth Engine**: ee (optional, for future extensions)

## Project Conventions

### Code Style

- Python: Standard PEP 8 with type hints where practical
- Reactive state: Use `solara.reactive()` for component state
- Memoization: Use `solara.use_memo()` for expensive operations
- Effects: Use `solara.use_effect()` for side effects with dependencies
- Module-level singletons: Use for resources that shouldn't be recreated (TileClient, SplitMapControl)

### Architecture Patterns

```
Browser (localhost:8765)
    │
    ▼
Solara App (src/main.py)
    ├─ Frontend: ipyleaflet + geemap
    ├─ Tile Service: localtileserver (embedded)
    └─ Data: Direct COG file access
```

**Two-Step Workflow**:
1. **Step 1**: Watershed Selection - Browse HydroBASINS, search by ID/coordinates, select return period
2. **Step 2**: Flood Visualization - View Sentinel-2 imagery, flood classification, uncertainty maps

### Testing Strategy

- Manual testing via Solara hot-reload
- Python import tests for module validation
- COG validation via `rio cogeo validate`

### Git Workflow

- Main branch: `master`
- Commit format: `type: description` (feat, fix, refactor, docs)
- Co-authored commits when using AI assistance

## Domain Context

### HydroBASINS

- Global watershed database with hierarchical levels (1-12)
- HYBAS_ID format: 10 digits
  - Digit 1: Region (1=Africa, 2=Europe, 3=Siberia, 4=Asia, 5=Australia, 6=South America, 7=North America, 8=Arctic, 9=Greenland)
  - Digits 2-3: Pfafstetter level (01-12)
  - Digits 4-9: Unique identifier
  - Digit 10: Side indicator (0=noSide, 1=Left, 2=Right)

### Region Codes

| Code | Region |
|------|--------|
| af | Africa |
| ar | Arctic |
| as | Asia |
| au | Australia |
| eu | Europe |
| gr | Greenland |
| na | North America |
| sa | South America |
| si | Siberia |

### Flood Model Output

- Band 1: Classification (0=Invalid, 1=Land, 2=Water, 3=Cloud, 4=Flood)
- Band 2: Uncertainty (0.0=certain, 1.0=uncertain)

### Return Periods

Available: T_2, T_5, T_10, T_20, T_50, T_100, T_200

## Important Constraints

1. **Single Port**: Only port 8765 needs to be accessible (Solara + embedded tile servers)
2. **COG Format**: All GeoTIFF files must be Cloud Optimized for performance
3. **No Backend Server**: localtileserver runs embedded in Solara app
4. **Shapefile Requirements**: `.shp`, `.shx`, `.dbf`, `.prj` must be in same directory

## External Dependencies

- **HydroBASINS Data**: `/home/sungche/NAS/dataset/hydro_basins/{region}/shp/`
- **Sentinel-2 Images**: Configured via `dataset/config.yaml` → `model.input_folder`
- **Model Outputs**: Configured via `dataset/config.yaml` → `model.output_folder`
- **GloFAS Catalog**: For return period data (intake catalog)

## File Structure

```
src/
├── main.py           # Entry point, routes between steps
├── state.py          # Global reactive state
├── config.py         # Centralized configuration
├── step1/
│   ├── app.py        # Watershed selection UI
│   └── utils.py      # Watershed query utilities
└── step2/
    ├── app.py        # Flood visualization UI
    └── utils.py      # File discovery utilities

dataset/
└── config.yaml       # User-configurable paths

openspec/
├── project.md        # This file
├── AGENTS.md         # AI assistant instructions
├── specs/            # Current truth - what IS built
└── changes/          # Proposals - what SHOULD change
```

## Key Configuration Files

### dataset/config.yaml

```yaml
model:
  input_folder: /path/to/sentinel2/
  output_folder: /path/to/predictions/
  event_date: "2024-04-13"

watershed:
  root_path: /path/to/hydro_basins/
  region: "si"
  level: 8
  default_id: 3080576250

return_period_ds:
  intake_catalogs_path: /path/to/catalog.yaml
  source: glofas_return_periods
  variable: T_2, T_5, T_10, T_20, T_50, T_100, T_200
```

### src/config.py

Centralized Python constants:
- Port configuration (SOLARA_PORT, INPUT_TILE_PORT, OUTPUT_TILE_PORT)
- Map defaults (DEFAULT_CENTER, DEFAULT_ZOOM, WATERSHED_ZOOM)
- Visualization (CLASSIFICATION_COLORMAP, UNCERTAINTY_COLORMAP)
- Helper functions (load_yaml_config, get_model_config, get_watershed_config)
