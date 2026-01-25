# Capability: Step 1 - Watershed Explorer

## Overview

Interactive watershed selection interface using HydroBASINS data. Provides region/level browsing, HYBAS_ID search, coordinate navigation, and return period selection.

---

## Requirements

### Requirement: Region and Level Selection

The system SHALL allow users to select HydroBASINS region and level.

#### Scenario: Select region
- **GIVEN** the Step 1 interface
- **WHEN** user selects a region from dropdown
- **THEN** available regions include: af, ar, as, au, eu, gr, na, sa, si
- **AND** display names show full region names (e.g., "Siberia" for "si")

#### Scenario: Select level
- **GIVEN** the Step 1 interface
- **WHEN** user selects a level
- **THEN** available levels are 1 through 12
- **AND** higher levels have smaller, more detailed watersheds

---

### Requirement: HYBAS_ID Search

The system SHALL allow users to search for watersheds by HYBAS_ID.

#### Scenario: Search valid HYBAS_ID
- **GIVEN** user enters a valid 10-digit HYBAS_ID (e.g., 3080576250)
- **WHEN** user clicks Search
- **THEN** system auto-detects region from first digit (3 = Siberia)
- **AND** system auto-detects level from digits 2-3 (08 = level 8)
- **AND** map centers on the found watershed
- **AND** watershed is highlighted in yellow with red border
- **AND** info panel shows SUB_AREA and UP_AREA

#### Scenario: Search invalid HYBAS_ID
- **GIVEN** user enters an invalid HYBAS_ID
- **WHEN** user clicks Search
- **THEN** error message is displayed
- **AND** map state is unchanged

#### Scenario: HYBAS_ID region mapping
- **GIVEN** the search function
- **WHEN** parsing HYBAS_ID first digit
- **THEN** 1=af, 2=eu, 3=si, 4=as, 5=au, 6=sa, 7=na, 8=ar, 9=gr

---

### Requirement: Coordinate Search

The system SHALL allow users to navigate by latitude/longitude coordinates.

#### Scenario: Navigate to coordinates
- **GIVEN** user enters latitude and longitude
- **WHEN** user clicks Search (in Coordinates mode)
- **THEN** map centers on the specified location
- **AND** zoom level is set to 8
- **AND** info message shows "Map centered at (lat, lon)"

#### Scenario: Invalid coordinates
- **GIVEN** user enters out-of-range coordinates
- **WHEN** user clicks Search
- **THEN** error message "Coordinates out of range" is displayed

---

### Requirement: Load Watershed Boundaries

The system SHALL allow users to load and display watershed boundaries on demand.

#### Scenario: Load watersheds at default position
- **GIVEN** map is at default center position
- **WHEN** user enables "Load Watersheds Boundaries" checkbox
- **THEN** entire region/level shapefile is loaded
- **AND** watersheds are displayed as blue polygons

#### Scenario: Load watersheds at custom position
- **GIVEN** map has been moved from default position
- **WHEN** user enables "Load Watersheds Boundaries" checkbox
- **THEN** only watersheds within ±5° of map center are loaded
- **AND** info message indicates buffer zone

#### Scenario: Click watershed to select
- **GIVEN** watershed layer is displayed
- **WHEN** user clicks on a watershed polygon
- **THEN** watershed is selected and highlighted
- **AND** info panel updates with watershed metadata

---

### Requirement: Return Period Selection

The system SHALL allow users to select flood return period for analysis.

#### Scenario: Select return period
- **GIVEN** the Step 1 interface
- **WHEN** user selects from return period dropdown
- **THEN** available options are T_2, T_5, T_10, T_20, T_50, T_100, T_200
- **AND** selected value is stored in global state

---

### Requirement: Watershed Info Display

The system SHALL display metadata for selected watersheds.

#### Scenario: Display watershed info
- **GIVEN** a watershed is selected
- **WHEN** viewing the info panel
- **THEN** HYBAS_ID is displayed
- **AND** SUB_AREA (sub-basin area in km²) is displayed
- **AND** UP_AREA (upstream area in km²) is displayed

---

### Requirement: Submit to Step 2

The system SHALL allow users to submit selection and proceed to Step 2.

#### Scenario: Submit valid selection
- **GIVEN** a watershed is selected
- **WHEN** user clicks "Submit & Continue to Step 2"
- **THEN** selection is saved to config.yaml
- **AND** global state is updated
- **AND** navigation proceeds to Step 2

#### Scenario: Submit without selection
- **GIVEN** no watershed is selected
- **WHEN** viewing submit button
- **THEN** button is disabled

---

### Requirement: Map Layer Management

The system SHALL properly manage map layers to prevent accumulation.

#### Scenario: Layer update on state change
- **GIVEN** any relevant state changes (search, selection, checkbox)
- **WHEN** map updates
- **THEN** existing layers are cleared first
- **AND** new layers are added in correct order (bottom to top)
- **AND** no duplicate layers exist

#### Scenario: Layer order
- **GIVEN** multiple layers are displayed
- **WHEN** rendering the map
- **THEN** order is: basemap → global watersheds → context watersheds → selected watershed

---

## Implementation Notes

### File: src/step1/app.py

Key components:
- Reactive state: `selected_region`, `selected_level`, `selected_watershed_id`, `map_center`, `map_zoom`
- Search modes: "Coordinates" and "HYBAS ID"
- Layer management via `update_map_layers()` effect

### File: src/step1/utils.py

Key functions:
- `load_watershed_by_id(hybas_id)`: Auto-detect region/level and load
- `load_watersheds(region, level)`: Load shapefile
- `filter_nearby_watersheds(gdf, id, expansion_factor)`: Spatial filtering
- `find_watersheds_by_coordinates(region, level, lat, lon, buffer)`: Buffer search
- `get_available_regions()`: Returns ['af', 'ar', 'as', 'au', 'eu', 'gr', 'na', 'sa', 'si']

### File: src/state.py

Global state shared with Step 2:
- `selected_watershed_id`: Selected HYBAS_ID
- `selected_return_period`: Selected return period (default: "T_200")
- `current_step`: Navigation state (1 or 2)
