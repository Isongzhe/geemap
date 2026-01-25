"""
Centralized configuration for the Geemap Flood Visualization Application.

This module contains all application constants and provides functions
to load user-configurable settings from dataset/config.yaml.
"""

import yaml
import os

# =============================================================================
# Application Info
# =============================================================================

APP_TITLE = "Flood Visualization"
STEP1_TITLE = "Step 1: Watershed Explorer"
STEP2_TITLE = "Step 2: Flood Visualization"
STEP1_NAV_LABEL = "Watershed"
STEP2_NAV_LABEL = "Visualization"

# =============================================================================
# Port Configuration
# =============================================================================
# SSH forwarding: ssh -L 8765:localhost:8765 -L 9100:localhost:9100 -L 9101:localhost:9101 user@server

SOLARA_PORT = 8765
INPUT_TILE_PORT = 9100
OUTPUT_TILE_PORT = 9101

# =============================================================================
# Map Defaults
# =============================================================================

DEFAULT_CENTER = (20.0, 0.0)  # (lat, lon)
DEFAULT_ZOOM = 2
WATERSHED_ZOOM = 11

# =============================================================================
# Visualization
# =============================================================================

CLASSIFICATION_COLORMAP = 'viridis'
UNCERTAINTY_COLORMAP = 'rdylgn_r'
WATERSHED_COLOR = '#FFD700'
WATERSHED_LINE_WIDTH = 4

# =============================================================================
# Earth Engine
# =============================================================================

EE_PROJECT = "geemap-484609"

# =============================================================================
# File Paths
# =============================================================================

CONFIG_YAML_PATH = "dataset/config.yaml"

# =============================================================================
# Functions
# =============================================================================

def load_yaml_config() -> dict:
    """
    Load configuration from dataset/config.yaml.

    Returns:
        dict: Configuration dictionary with model and watershed settings.
    """
    with open(CONFIG_YAML_PATH, "r") as f:
        return yaml.safe_load(f)


def get_model_paths() -> tuple:
    """
    Get input and output paths from config.yaml.

    Returns:
        tuple: (input_path, output_path)
    """
    config = load_yaml_config()
    model = config.get("model", {})
    return model.get("input_path"), model.get("output_path")


def get_watershed_config() -> dict:
    """
    Get watershed configuration from config.yaml.

    Returns:
        dict: Watershed configuration with root_path, region, level, default_id
    """
    config = load_yaml_config()
    return config.get("watershed", {})


def save_yaml_config(config: dict):
    """
    Save configuration to dataset/config.yaml.

    Args:
        config: Configuration dictionary to save.
    """
    with open(CONFIG_YAML_PATH, "w") as f:
        yaml.safe_dump(config, f)


def get_return_period_config() -> dict:
    """
    Get return period configuration from config.yaml.
    
    Returns:
        dict: Return period configuration with intake_catalogs_path, source, variable
    """
    config = load_yaml_config()
    return config.get("return_period_ds", {})


# =============================================================================
# Return Period Options
# =============================================================================

# Available return period options (only <= 200 years)
AVAILABLE_RETURN_PERIODS = ["T_2", "T_5", "T_10", "T_20", "T_50", "T_100", "T_200"]
DEFAULT_RETURN_PERIOD = "T_200"


def parse_return_period_variables(variables_str: str) -> list[str]:
    """
    Get available return period options.
    
    Note: We use a predefined list (AVAILABLE_RETURN_PERIODS) instead of parsing
    the config string. This is simpler and more maintainable.
    
    Args:
        variables_str: Not used, kept for compatibility
    
    Returns:
        list: Predefined list of return periods
    """
    return AVAILABLE_RETURN_PERIODS


def get_model_config() -> dict:
    """
    Get model configuration including event_date and file patterns.
    
    Returns:
        dict: Model config with input_folder, output_folder, event_date, patterns
    """
    config = load_yaml_config()
    return config.get("model", {})


def get_analog_df_config() -> dict:
    """
    Get analog results dataframe configuration.
    
    Returns:
        dict: Analog df config with path and top_n
    """
    config = load_yaml_config()
    return config.get("analog_df", {})
