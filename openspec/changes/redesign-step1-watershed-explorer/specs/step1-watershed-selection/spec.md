# Step 1: Watershed Selection

## ADDED Requirements

### Requirement: Region and Level Selection
The system SHALL allow users to select a HydroBASINS region and level to load watershed data.

#### Scenario: User selects region and level
- **WHEN** user selects region "as" and level "07"
- **THEN** system loads `/home/sungche/NAS/dataset/hydro_basins/as/shp/hybas_as_lev07_v1c.shp`
- **AND** displays watershed polygons on the map

#### Scenario: Default values on page load
- **WHEN** Step 1 page loads
- **THEN** region defaults to config value (e.g., "as")
- **AND** level defaults to 07
- **AND** map shows global view without zoom lock

### Requirement: HYBAS_ID Search
The system SHALL provide a search input for finding watersheds by HYBAS_ID.

#### Scenario: Valid HYBAS_ID search
- **WHEN** user enters "4070026610" in search field
- **AND** clicks search or presses Enter
- **THEN** system finds the watershed with matching HYBAS_ID
- **AND** centers map on the watershed
- **AND** zooms to fit the watershed bounds
- **AND** selects the watershed

#### Scenario: Invalid HYBAS_ID search
- **WHEN** user enters an invalid or non-existent HYBAS_ID
- **THEN** system displays "Watershed not found" message
- **AND** map position remains unchanged

### Requirement: Coordinate Navigation
The system SHALL allow users to navigate to a specific lat/lon coordinate (WGS84).

#### Scenario: Navigate to coordinates
- **WHEN** user enters latitude "25.0" and longitude "121.5"
- **AND** clicks "Go" button
- **THEN** map centers on (25.0, 121.5)
- **AND** zooms to a reasonable level (e.g., zoom 10)

#### Scenario: Empty coordinates
- **WHEN** coordinate fields are empty or cleared
- **THEN** map returns to global view (default center, zoom 2)

### Requirement: Layer Visibility Toggle
The system SHALL provide a toggle to show/hide the current watershed layer.

#### Scenario: Hide layer
- **WHEN** user unchecks the layer visibility toggle
- **THEN** watershed polygons are hidden from the map
- **AND** base map remains visible

#### Scenario: Show layer
- **WHEN** user checks the layer visibility toggle
- **THEN** watershed polygons are displayed on the map

### Requirement: Watershed Metadata Display
The system SHALL display metadata for the selected watershed.

#### Scenario: Click watershed to view metadata
- **WHEN** user clicks on a watershed polygon
- **THEN** system selects the watershed
- **AND** displays in sidebar:
  - HYBAS_ID
  - SUB_AREA (in km²)
  - UP_AREA (in km²)

#### Scenario: No selection
- **WHEN** no watershed is selected
- **THEN** metadata panel shows "Click a watershed to view details"

### Requirement: Submit Selection
The system SHALL allow users to submit the selected watershed and proceed to Step 2.

#### Scenario: Submit with selection
- **WHEN** user has selected a watershed
- **AND** clicks "Submit" button
- **THEN** system saves selected watershed info to config
- **AND** navigates to Step 2

#### Scenario: Submit without selection
- **WHEN** no watershed is selected
- **THEN** "Submit" button is disabled or shows warning
