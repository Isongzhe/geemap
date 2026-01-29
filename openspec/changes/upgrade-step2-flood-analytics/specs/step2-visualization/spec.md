## ADDED Requirements

### Requirement: Analog Event Catalog Loading

The system SHALL load analog flood events from CSV file specified in configuration.

#### Scenario: Load analog events from CSV
- **GIVEN** config.yaml contains `analog_df.path` pointing to valid CSV
- **AND** CSV has columns: rank, method, datetime, score
- **WHEN** Step 2 initializes
- **THEN** system loads CSV using pandas
- **AND** sorts by rank ascending
- **AND** limits to `analog_df.top_n` events
- **AND** extracts available dates for dropdown

#### Scenario: CSV file missing
- **GIVEN** `analog_df.path` does not exist
- **WHEN** Step 2 initializes
- **THEN** system falls back to single-event mode
- **AND** uses `model.event_date` from config
- **AND** logs warning message

---

### Requirement: Event Selection Interface

The system SHALL provide UI for selecting analog events from the catalog.

#### Scenario: Display event selector
- **GIVEN** analog events are loaded
- **WHEN** viewing the sidebar
- **THEN** dropdown shows available event dates
- **AND** default selection is rank 1 event
- **AND** current rank, date, and MAE score are displayed below selector

#### Scenario: Change event selection
- **GIVEN** event selector dropdown
- **WHEN** user selects different event date
- **THEN** map layers update to show new event data
- **AND** preview image updates if available
- **AND** info card shows new event metadata
- **AND** red star in analytics chart moves to new selection

---

### Requirement: Event Preview Images

The system SHALL display prediction preview images when available.

#### Scenario: Load preview image
- **GIVEN** selected event date
- **WHEN** system searches output folder
- **THEN** finds PNG file matching `*{event_date}*_EDL_prediction.png`
- **AND** displays image below event selector

#### Scenario: Preview image missing
- **GIVEN** no preview image exists for event date
- **WHEN** searching output folder
- **THEN** display placeholder text "Preview not available"
- **AND** continue normal operation without error

---

### Requirement: Permanent Water Overlay

The system SHALL display permanent water boundaries on the flood classification map.

#### Scenario: Load permanent water layer
- **GIVEN** config contains `model.permanent_water_path`
- **WHEN** Step 2 initializes
- **THEN** system creates TileClient for permanent water COG
- **AND** uses port 9102 for permanent water tiles
- **AND** layer is cached as singleton

#### Scenario: Render permanent water overlay
- **GIVEN** permanent water TileClient exists
- **AND** layer mode is "Flood Classification"
- **WHEN** rendering right side of split map
- **THEN** flood classification layer is base
- **AND** permanent water layer overlays on top
- **AND** permanent water uses blue palette `['transparent', '#0000FF']`
- **AND** permanent water has opacity 0.5
- **AND** permanent water z-index is higher than classification

#### Scenario: Permanent water file missing
- **GIVEN** `model.permanent_water_path` does not exist
- **WHEN** Step 2 initializes
- **THEN** log warning message
- **AND** skip permanent water overlay
- **AND** classification layer still renders normally

---

### Requirement: Analytics Panel - Event Table

The system SHALL display all analog events in a data table.

#### Scenario: Display events table
- **GIVEN** analog events are loaded
- **WHEN** viewing bottom panel
- **THEN** left side shows DataFrame with columns: rank, datetime, score
- **AND** table is scrollable if events exceed viewport
- **AND** selected event row is not highlighted (chart shows selection)

---

### Requirement: Analytics Panel - Score Distribution Chart

The system SHALL visualize similarity score distribution with highlighted selection.

#### Scenario: Display box + strip plot
- **GIVEN** analog events are loaded
- **WHEN** viewing bottom panel
- **THEN** right side shows box plot of all scores
- **AND** strip plot overlays individual event scores
- **AND** y-axis is MAE score
- **AND** chart title is "Similarity Score Distribution (Lower is Better)"

#### Scenario: Highlight selected event
- **GIVEN** user has selected an event
- **WHEN** viewing the chart
- **THEN** selected event is marked with large red star
- **AND** red star has z-index 10 (top layer)
- **AND** red star size is 200 points

---

### Requirement: Strict Sentinel-2 Input Requirement

The system SHALL only load Sentinel-2 files for input imagery.

#### Scenario: Find S2 input file
- **GIVEN** event_date and input_folder
- **WHEN** searching for input file
- **THEN** system matches pattern `S2_{event_date}*.tif`
- **AND** returns first match if multiple exist
- **AND** returns None if no S2 files found (no fallback to Landsat)

---

### Requirement: Wildcard Output Pattern Support

The system SHALL support both S2 and Landsat prefixed output files.

#### Scenario: Find output file with any sensor prefix
- **GIVEN** event_date and output_folder
- **WHEN** searching for output file
- **THEN** system matches pattern `*{event_date}*_EDL.tif` (wildcard prefix)
- **AND** accepts both `S2_` and `LS_` prefixed files
- **AND** returns first match if multiple exist

---

## MODIFIED Requirements

### Requirement: Event-Driven File Loading

The system SHALL load input/output files based on selected event date from analog catalog.

#### Scenario: Load files for selected event date
- **GIVEN** user selects event from dropdown
- **WHEN** event selection changes
- **THEN** system searches for `S2_{event_date}_*.tif` in input_folder (strict S2)
- **AND** system searches for `*{event_date}_*_EDL.tif` in output_folder (wildcard prefix)
- **AND** console logs show found file names
- **AND** TileClients are recreated for new files

#### Scenario: Missing files for selected event
- **GIVEN** selected event date does not have matching files
- **WHEN** searching for files
- **THEN** warning message is logged to console
- **AND** map shows only basemap
- **AND** user can select different event

---

### Requirement: Event Information Display

The system SHALL display selected event metadata in the sidebar.

#### Scenario: Show event info
- **GIVEN** Step 2 is loaded with analog events
- **WHEN** viewing the sidebar
- **THEN** Event Date from selected analog is displayed
- **AND** Return Period (from Step 1 selection) is displayed
- **AND** Rank (from CSV) is displayed
- **AND** MAE Score (from CSV) is displayed

---

### Requirement: Split Map View

The system SHALL provide split-map comparison view with permanent water overlay.

#### Scenario: Classification mode split view with permanent water
- **GIVEN** layer mode is "Flood Classification"
- **AND** permanent water layer is available
- **WHEN** viewing the map
- **THEN** left side shows Sentinel-2 original image
- **AND** right side shows composite: flood classification (base) + permanent water (overlay)
- **AND** permanent water uses blue color with 50% opacity
- **AND** draggable divider allows comparison

#### Scenario: Uncertainty mode split view (unchanged)
- **GIVEN** layer mode is "Uncertainty"
- **WHEN** viewing the map
- **THEN** left side shows flood classification
- **AND** right side shows uncertainty map
- **AND** permanent water is NOT shown in uncertainty mode
- **AND** draggable divider allows comparison

---

### Requirement: TileClient Singleton

The system SHALL use singleton TileClient instances including permanent water.

#### Scenario: Reuse TileClient on hot-reload
- **GIVEN** TileClient instances exist in module cache (input, output, water)
- **WHEN** Solara hot-reloads the component
- **THEN** cached TileClients are reused
- **AND** no new port bindings are created

#### Scenario: Create TileClient on first load
- **GIVEN** no cached TileClients exist
- **WHEN** Step 2 initializes
- **THEN** Input TileClient is created on port 9100
- **AND** Output TileClient is created on port 9101
- **AND** Permanent Water TileClient is created on port 9102

---

## REMOVED Requirements

None. All existing requirements are preserved with modifications for multi-event support.
