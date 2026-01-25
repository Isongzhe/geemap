# Configuration Management

## ADDED Requirements

### Requirement: Centralized Configuration Module
The system SHALL provide a centralized configuration module at `src/config.py`.

#### Scenario: Import configuration constants
- **WHEN** any module needs configuration values
- **THEN** it imports from `src.config`
- **AND** configuration is consistent across all modules

#### Scenario: Load YAML configuration
- **WHEN** application starts
- **THEN** `load_yaml_config()` reads `dataset/config.yaml`
- **AND** returns data paths and watershed settings

### Requirement: Configuration Categories
The system SHALL separate configuration into two categories.

#### Scenario: Application constants in config.py
- **WHEN** configuration is application-specific (ports, colors, zoom levels)
- **THEN** it is defined in `src/config.py`
- **AND** does not require user modification for normal use

#### Scenario: Data paths in config.yaml
- **WHEN** configuration is environment-specific (file paths, watershed ID)
- **THEN** it is defined in `dataset/config.yaml`
- **AND** users can modify without touching Python code
