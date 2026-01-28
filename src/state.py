import solara

# ============================================================================
# Global State (Shared Across Steps)
# ============================================================================

# Watershed selection from Step 1
selected_watershed_id = solara.reactive(None)

# Watershed GeoJSON for Step 2 visualization
selected_watershed_geojson = solara.reactive(None)

# Return period selection from Step 1
selected_return_period = solara.reactive("T_200")  # Default: 200-year return period (only T_200+ available)

# Global Navigation State
current_step = solara.reactive(1)

# Page transition loading state
is_transitioning = solara.reactive(False)
