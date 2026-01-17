# Dataset Documentation

This document describes the data sources used in the project as defined in `config.yaml`.

## 1. Watershed Shapefile
**Path**: `/home/NAS/homes/cjchen-10025/data/HydroBASINS/hybas_au_lev01-12_v1c/hybas_au_lev12_v1c.shp`
**Description**: Detailed watershed boundaries (HydroBASINS Level 12) for the Australia/Oceania region (implied by `au` code).
**Metadata**:
- **CRS**: EPSG:4326 (WGS 84)
- **Key Columns**:
    - `HYBAS_ID`: Unique Watershed Identifier (e.g., `5120274340`)
    - `NEXT_DOWN`: ID of the next downstream unit
    - `NEXT_SINK`: ID of the final sink
    - `SUB_AREA`: Area of the sub-basin
    - `UP_AREA`: Total upstream area

## 2. Model Input/Output (Raster)

### Input: Sentinel-2 Imagery
**Path**: `/home/NAS/homes/cjchen-10025/data/worldfloods_v2/data/test/S2/EMSR342_07SOUTHNORMANTON_DEL_MONIT03_v2.tif`
**Description**: Multi-spectral satellite imagery used as input for the flood model.
- **Shape**: (13, 5579, 5469) (Bands, Height, Width)
- **CRS**: EPSG:32630 (WGS 84 / UTM zone 30N)
- **Resolution**: (10.0, -10.0) meters
- **Bands**: 13 bands (Sentinel-2 L1C/L2A typical stack: B1, B2, B3, B4, B5, B6, B7, B8, B8A, B9, B10, B11, B12)

### Output: Flood Classification & Uncertainty
**Path**: `/home/NAS/homes/cjchen-10025/ML4FloodsUncertainty/result/EMSR342_07SOUTHNORMANTON_DEL_MONIT03_v2_output_EDL.tif`
**Description**: Model inference output containing classification and uncertainty estimation using Evidential Deep Learning (EDL).
- **Shape**: (2, 5579, 5469)
- **CRS**: EPSG:32630
- **Resolution**: (10.0, -10.0) meters
- **Bands**:
    1. **Classification Map**: Pixel class (0=invalid, 1=land, 2=water, 3=cloud, 4=flood_trace)
    2. **Uncertainty**: Aleatoric/Epistemic uncertainty metric (Values > 0).

## 3. IMERG Precipitation Catalog
**Catalog Path**: `/home/sungche/NAS/stac/wangup-stac-manager/config/catalogs/imerg_intake_catalog.yaml`
**Collection**: `imerg_return_periods`
**Description**: Extreme precipitation return period estimates derived from GPM IMERG V07.
**Format**: NetCDF (accessed via Intake/Xarray)
**Content**:
- **Variables**: Return period rainfall estimates (e.g., 2yr, 5yr, 100yr).
- **Spatial Resolution**: 0.1° x 0.1°
