# Capability: Configuration

## Overview

Centralized configuration management for the Geemap Flood Visualization Application. Provides both Python constants and YAML-based user configuration.

---

## Requirements

### Requirement: Centralized Python Configuration

The system SHALL provide a single `src/config.py` module containing all application constants.

#### Scenario: Import configuration constants
- **WHEN** any module imports from `src.config`
- **THEN** all constants (ports, colormaps, defaults) are accessible
- **AND** no hardcoded values exist in other modules

#### Scenario: Port configuration
- **GIVEN** the configuration module
- **WHEN** checking port settings
- **THEN** SOLARA_PORT equals 8765
- **AND** INPUT_TILE_PORT equals 9100
- **AND** OUTPUT_TILE_PORT equals 9101

---

### Requirement: YAML Configuration Loading

The system SHALL load user-configurable settings from `dataset/config.yaml`.

#### Scenario: Load model configuration
- **WHEN** `get_model_config()` is called
- **THEN** return dict with `input_folder`, `output_folder`, `event_date`

#### Scenario: Load watershed configuration
- **WHEN** `get_watershed_config()` is called
- **THEN** return dict with `root_path`, `region`, `level`, `default_id`

#### Scenario: Load return period configuration
- **WHEN** `get_return_period_config()` is called
- **THEN** return dict with `intake_catalogs_path`, `source`, `variable`

---

### Requirement: Application Title Configuration

The system SHALL provide configurable titles for the application and each step.

#### Scenario: Access title constants
- **WHEN** accessing title configuration
- **THEN** APP_TITLE, STEP1_TITLE, STEP2_TITLE are available
- **AND** navigation labels STEP1_NAV_LABEL, STEP2_NAV_LABEL are available

---

### Requirement: Map Default Configuration

The system SHALL provide default map settings.

#### Scenario: Default map center and zoom
- **GIVEN** the configuration module
- **WHEN** checking map defaults
- **THEN** DEFAULT_CENTER is (20.0, 0.0) as (lat, lon)
- **AND** DEFAULT_ZOOM is 2
- **AND** WATERSHED_ZOOM is 11

---

### Requirement: Visualization Configuration

The system SHALL provide visualization settings for map layers.

#### Scenario: Colormap configuration
- **GIVEN** the configuration module
- **WHEN** checking colormap settings
- **THEN** CLASSIFICATION_COLORMAP is 'viridis'
- **AND** UNCERTAINTY_COLORMAP is 'rdylgn_r'
- **AND** WATERSHED_COLOR is '#FFD700'
- **AND** WATERSHED_LINE_WIDTH is 4

---

### Requirement: Return Period Options

The system SHALL provide predefined return period options.

#### Scenario: Available return periods
- **WHEN** accessing AVAILABLE_RETURN_PERIODS
- **THEN** return list containing T_2, T_5, T_10, T_20, T_50, T_100, T_200
- **AND** DEFAULT_RETURN_PERIOD is "T_200"

---

## Implementation Notes

### File: src/config.py

Key exports:
- Constants: `SOLARA_PORT`, `INPUT_TILE_PORT`, `OUTPUT_TILE_PORT`, `DEFAULT_CENTER`, `DEFAULT_ZOOM`, etc.
- Functions: `load_yaml_config()`, `get_model_config()`, `get_watershed_config()`, `get_return_period_config()`, `save_yaml_config()`

### File: dataset/config.yaml

User-editable configuration for:
- Model paths and event date
- Watershed data location and defaults
- Return period data source
