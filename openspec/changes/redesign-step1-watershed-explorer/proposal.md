# Change: Redesign Step 1 Watershed Explorer

## Why
Current Step 1 is tightly coupled to Sentinel-2 image bounds filtering, limiting exploration. Users need a global watershed browser with search, navigation, and metadata display for demo purposes.

## What Changes
- **BREAKING**: Remove image-based watershed filtering; load watersheds from HydroBASINS by region/level
- Add HYBAS_ID search functionality
- Add lat/lon coordinate navigation with zoom control
- Add region selector (af, ar, as, au, eu, gr, na, sa)
- Add level selector (01-12, default: 07)
- Add layer visibility toggle
- Display watershed metadata (SUB_AREA, UP_AREA) on selection
- Update Submit to pass selected watershed info to Step 2

## Impact
- Affected specs: `step1-watershed-selection` (new capability)
- Affected code:
  - `src/step1/app.py` - Complete UI redesign
  - `src/step1/utils.py` - New data loading functions
  - `dataset/config.yaml` - Uses existing `root_path`, `region`, `level` structure
