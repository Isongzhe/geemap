# Capability: Step 2 - Flood Visualization

## Overview

Interactive flood visualization interface displaying Sentinel-2 imagery, flood classification, and uncertainty maps using COG tile layers and split-map comparison.

---

## Requirements

### Requirement: Event-Driven File Loading

The system SHALL load input/output files based on event_date from configuration.

#### Scenario: Load files for event date
- **GIVEN** config.yaml contains event_date, input_folder, output_folder
- **WHEN** Step 2 initializes
- **THEN** system searches for `S2_{event_date}_*.tif` in input_folder
- **AND** system searches for `S2_{event_date}_*_EDL.tif` in output_folder
- **AND** console logs show found file names

#### Scenario: Missing files
- **GIVEN** no files match the event_date pattern
- **WHEN** Step 2 initializes
- **THEN** warning message is displayed
- **AND** map shows only basemap

---

### Requirement: Event Information Display

The system SHALL display current event metadata in the sidebar.

#### Scenario: Show event info
- **GIVEN** Step 2 is loaded
- **WHEN** viewing the sidebar
- **THEN** Event Date is displayed
- **AND** Return Period (from Step 1 selection) is displayed

---

### Requirement: Split Map View

The system SHALL provide split-map comparison view.

#### Scenario: Classification mode split view
- **GIVEN** layer mode is "Flood Classification"
- **WHEN** viewing the map
- **THEN** left side shows Sentinel-2 original image
- **AND** right side shows flood classification layer
- **AND** draggable divider allows comparison

#### Scenario: Uncertainty mode split view
- **GIVEN** layer mode is "Uncertainty"
- **WHEN** viewing the map
- **THEN** left side shows flood classification
- **AND** right side shows uncertainty map
- **AND** draggable divider allows comparison

---

### Requirement: Layer Mode Toggle

The system SHALL allow switching between Classification and Uncertainty modes.

#### Scenario: Toggle layer mode
- **GIVEN** the mode toggle buttons
- **WHEN** user clicks "Flood Classification" or "Uncertainty"
- **THEN** split map updates to show appropriate layers
- **AND** legend updates to match current mode

---

### Requirement: Classification Legend

The system SHALL display classification legend when in Classification mode.

#### Scenario: Show classification legend
- **GIVEN** layer mode is "Flood Classification"
- **WHEN** viewing the legend
- **THEN** display class values with Viridis colormap:
  - 0: Invalid/No Data (Dark Purple)
  - 1: Land (Purple-Blue)
  - 2: Water (Green-Blue)
  - 3: Cloud (Yellow-Green)
  - 4: Flood Trace (Yellow)

---

### Requirement: Uncertainty Legend

The system SHALL display uncertainty legend when in Uncertainty mode.

#### Scenario: Show uncertainty legend
- **GIVEN** layer mode is "Uncertainty"
- **WHEN** viewing the legend
- **THEN** display color scale:
  - Green = Low uncertainty (reliable)
  - Yellow = Medium uncertainty
  - Red = High uncertainty (unreliable)
- **AND** note that values range from 0 (certain) to 1 (uncertain)

---

### Requirement: TileClient Singleton

The system SHALL use singleton TileClient instances to prevent port conflicts.

#### Scenario: Reuse TileClient on hot-reload
- **GIVEN** TileClient instances exist in module cache
- **WHEN** Solara hot-reloads the component
- **THEN** cached TileClients are reused
- **AND** no new port bindings are created

#### Scenario: Create TileClient on first load
- **GIVEN** no cached TileClients exist
- **WHEN** Step 2 initializes
- **THEN** Input TileClient is created on port 9100
- **AND** Output TileClient is created on port 9101

---

### Requirement: SplitMapControl Management

The system SHALL properly manage SplitMapControl to prevent duplication.

#### Scenario: Remove control before layer update
- **GIVEN** SplitMapControl exists on map
- **WHEN** layer mode changes
- **THEN** existing SplitMapControl is removed first
- **AND** new SplitMapControl is created with new layers
- **AND** no ghost controls remain on map

#### Scenario: Track control reference
- **GIVEN** module-level `_current_split_control` variable
- **WHEN** creating new SplitMapControl
- **THEN** reference is stored for later cleanup

---

### Requirement: Watershed Overlay

The system SHALL display selected watershed boundary on the map.

#### Scenario: Show watershed boundary
- **GIVEN** watershed is selected in Step 1
- **WHEN** viewing Step 2 map
- **THEN** watershed boundary is displayed in gold color (#FFD700)
- **AND** boundary has line width of 4
- **AND** fill is transparent

---

### Requirement: Map Center Calculation

The system SHALL center map on input data bounds.

#### Scenario: Calculate map center from COG
- **GIVEN** input COG file exists
- **WHEN** Step 2 initializes
- **THEN** map centers on COG bounds center
- **AND** coordinates are transformed to WGS84 if necessary
- **AND** zoom is set to WATERSHED_ZOOM (11)

#### Scenario: Fallback to default center
- **GIVEN** input COG file does not exist
- **WHEN** Step 2 initializes
- **THEN** map uses DEFAULT_CENTER and DEFAULT_ZOOM

---

## Implementation Notes

### File: src/step2/app.py

Key components:
- Module-level caches: `_tile_clients_cache`, `_current_split_control`
- Reactive state: `map_layer_mode`
- Memoized functions: `_create_base_map()`, `_create_tile_clients()`, `_create_watershed_layer()`
- Effect: `update_layers()` triggered by `layer_mode` changes

### File: src/step2/utils.py

Key functions:
- `find_event_input(event_date, input_folder)`: Find Sentinel-2 input file
- `find_event_output(event_date, output_folder)`: Find EDL output file

### Colormap Configuration

- Classification: `viridis` (Band 1)
- Uncertainty: `rdylgn_r` with vmin=0.0, vmax=1.0 (Band 2)

### Port Configuration

- Input TileClient: port 9100
- Output TileClient: port 9101
- Both bind to 0.0.0.0 with client_host='localhost'
