import solara
import geemap
import os
import geopandas as gpd
from ipyleaflet import GeoJSON
from src.step1.utils import get_candidate_watersheds, save_selected_watershed
import src.state as state

# Shared State
selected_watershed_id = solara.reactive(None)
candidates_gdf = solara.reactive(None)
map_center = solara.reactive((20, 0, 2)) # Default

def load_data():
    if candidates_gdf.value is None:
        print("Loading Initial Data for Step 1...")
        gdf, bounds = get_candidate_watersheds()
        candidates_gdf.set(gdf)
        
        # Calculate center from bounds
        minx, miny, maxx, maxy = bounds
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        map_center.set((cx, cy, 10)) # Zoom 10 for ROI
        
        # Auto-select if only one
        if len(gdf) == 1:
            selected_watershed_id.set(gdf.iloc[0]['HYBAS_ID'])

@solara.component
def Page():
    # Load data once
    solara.use_memo(load_data, dependencies=[])
    
    current_id = selected_watershed_id.value
    gdf = candidates_gdf.value
    cx, cy, zoom = map_center.value
    
    def on_map_interaction(**kwargs):
        # Geemap click handling is tricky in Solara.
        # We use a widget callback or FeatureLayer "on_click" if possible.
        # Alternative: Dropdown list for selection since N is small (3-5).
        pass

    with solara.Column(style={"height": "100vh"}):
        solara.Title("Step 1: Select Watershed")
        
        with solara.Sidebar():
            solara.Markdown("### 1. Select Watershed")
            solara.Markdown("Choose the watershed that covers your ROI.")
            
            if gdf is not None:
                # Create options list
                options = list(gdf['HYBAS_ID'].astype(str))
                if not options:
                    solara.Error("No watersheds found intersecting the image!")
                else:
                    solara.Select(label="Watershed ID", value=str(current_id) if current_id else None, values=options, 
                                  on_value=lambda v: selected_watershed_id.set(int(v)))
            
            if current_id:
                solara.Success(f"Selected: {current_id}")
                def save():
                    save_selected_watershed(current_id)
                    state.current_step.set(2)
                
                solara.Button("Save & Next", on_click=save, color="primary")
            
            solara.Markdown("---")
            solara.Markdown("**Debug Info**")
            if gdf is not None:
                solara.Text(f"Candidates Found: {len(gdf)}")

        # Map
        m = geemap.Map(center=[cy, cx], zoom=zoom,
                       toolbar_ctrl=False,
                       draw_ctrl=False,
                       data_ctrl=False,
                       search_control=False)
        m.add_basemap("OpenStreetMap")
        
        if gdf is not None:
            # 1. Overlay All Candidates (Blue Outline)
            style_candidates = {'color': 'blue', 'fillOpacity': 0.1, 'weight': 2}
            json_candidates = GeoJSON(data=gdf.__geo_interface__, style=style_candidates, name="Candidates")
            
            # Click Handler
            def handle_click(event=None, feature=None, **kwargs):
                if feature:
                   props = feature.get("properties", {})
                   hid = props.get("HYBAS_ID")
                   if hid:
                       print(f"Clicked Watershed: {hid}")
                       selected_watershed_id.set(int(hid))

            json_candidates.on_click(handle_click)
            m.add_layer(json_candidates)
            
            # 2. Overlay Selected (Yellow Fill)
            if current_id:
                selected_row = gdf[gdf['HYBAS_ID'] == int(current_id)]
                if not selected_row.empty:
                    style_selected = {'color': 'red', 'fillColor': 'yellow', 'fillOpacity': 0.5, 'weight': 3}
                    json_selected = GeoJSON(data=selected_row.__geo_interface__, style=style_selected, name="Selected")
                    m.add_layer(json_selected)
        
        solara.display(m)

if __name__ == "__main__":
    Page()
