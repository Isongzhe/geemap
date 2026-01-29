## MODIFIED Requirements

### Requirement: SplitMapControl Management

The system SHALL properly manage SplitMapControl to prevent duplication and ensure correct display in both modes.

#### Scenario: Remove control before layer update
- **GIVEN** SplitMapControl exists on map
- **WHEN** layer mode changes
- **THEN** existing SplitMapControl is removed first using the global reference
- **AND** new SplitMapControl is created with new layers
- **AND** no ghost controls remain on map

#### Scenario: Track control reference
- **GIVEN** module-level `_current_split_control` variable
- **WHEN** creating new SplitMapControl
- **THEN** reference is stored using `global` keyword for proper module-level update
- **AND** subsequent layer mode changes can access the correct reference

#### Scenario: Display layers correctly in both modes
- **GIVEN** user toggles between Flood Classification and Uncertainty modes
- **WHEN** SplitMapControl is recreated
- **THEN** left and right layers each occupy 100% width without breaking
- **AND** images display correctly in both modes
