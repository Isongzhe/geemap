import solara

# ============================================================================
# Global State (Shared Across Steps)
# ============================================================================

# Watershed selection from Step 1
selected_watershed_id = solara.reactive(None)

# Return period selection from Step 1
selected_return_period = solara.reactive("T_200")  # Default: 200-year return period (only T_200+ available)

# Global Navigation State
# Temporarily focus on Step 2 only
current_step = solara.reactive(1)
