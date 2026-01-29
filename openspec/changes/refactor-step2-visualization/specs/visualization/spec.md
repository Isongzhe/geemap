# Visualization Update Specs

## MODIFIED Requirements

#### Scenario: Switching Events
- **Given** the user selects a new event date
- **When** the event files load
- **Then** the map should clear all previous `SplitMapControl` instances
- **And** the map should update layers with the new event date
- **And** the layer names should be unique to prevent caching old event tiles
- **And** no duplicate initialization logic should run

#### Scenario: Switching Layer Modes
- **Given** the user switches between "Flood Classification" and "Uncertainty"
- **Then** the map should smoothly transition without flickering
- **And** correct layers (Classification vs Uncertainty) should be shown
- **And** Permanent Water layer should persist correctly

#### Scenario: Code Structure
- **Given** `Page()` component
- **Then** `load_files_for_event` should be defined exactly once
- **And** `update_layers` should not rely on stale closure variables
