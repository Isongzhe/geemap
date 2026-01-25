# Step 2: Flood Visualization

## MODIFIED Requirements

### Requirement: TileServer Configuration
The system SHALL use two fixed-port TileServers for raster visualization.

#### Scenario: Dual TileServer startup
- **WHEN** Step 2 initializes
- **THEN** Input TileClient starts on port 9000
- **AND** Output TileClient starts on port 9001
- **AND** both use host 0.0.0.0 for remote access

#### Scenario: Hot reload handling
- **WHEN** Solara hot-reloads the application
- **THEN** existing TileClients are reused from cache
- **AND** no port conflict errors occur

#### Scenario: Port forwarding
- **WHEN** user accesses via SSH tunnel
- **THEN** ports 8765, 9000, 9001 must be forwarded
- **AND** tile requests work correctly through forwarded ports
