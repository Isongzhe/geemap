import solara
import geemap
import rioxarray
import yaml
import os
import ee
import geopandas as gpd
from ipyleaflet import GeoJSON, TileLayer, ZoomControl, ScaleControl, AttributionControl

# Initialize Earth Engine
try:
    ee.Initialize()
except Exception:
    try:
        ee.Authenticate()
        ee.Initialize(project="geemap-484609")
    except Exception:
        pass

# Load Config
try:
    with open("dataset/config.yaml", "r") as f:
        config_data = yaml.safe_load(f)
        WATERSHED_CFG = config_data.get("watershed", {})
        WATERSHED_PATH = WATERSHED_CFG.get("path")
        WATERSHED_ID = WATERSHED_CFG.get("default_id")
        INPUT_PATH = config_data["model"]["input_path"]
except Exception as e:
    print(f"Config Error: {e}")
    WATERSHED_PATH = None
    WATERSHED_ID = None
    INPUT_PATH = None

CACHE_DIR = "dataset/cache"
OPT_INPUT = os.path.join(CACHE_DIR, "optimized_input.tif")

# State
uncertainty_threshold = solara.reactive(0.5)
show_split_map = solara.reactive(True)
map_layer_mode = solara.reactive("Flood Classification") 

import functools

@functools.lru_cache(maxsize=1)
def get_map_center():
    try:
        path = OPT_INPUT if os.path.exists(OPT_INPUT) else INPUT_PATH
        if not path: return 20, 0, 2
        with rioxarray.open_rasterio(path) as src:
            bounds = src.rio.bounds()
            crs = src.rio.crs
            cx = (bounds[0] + bounds[2]) / 2
            cy = (bounds[1] + bounds[3]) / 2
            if crs and crs != "EPSG:4326":
                from pyproj import Transformer
                t = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                cx, cy = t.transform(cx, cy)
            return cx, cy, 11
    except Exception:
        return 20, 0, 2

def _create_base_map():
    cx, cy, zoom = get_map_center()
    m = geemap.Map(center=[cy, cx], zoom=zoom, 
                   lite_mode=False, 
                   toolbar_ctrl=False,
                   draw_ctrl=False,
                   search_control=False,
                   data_ctrl=False)
    return m

@solara.component
def Page():
    threshold = uncertainty_threshold.value
    is_split = show_split_map.value
    layer_mode = map_layer_mode.value
    
    map_widget = solara.use_memo(_create_base_map, dependencies=[])

    # Tile Layer Helper - Unified Server on 7777
    def create_tile_layer(key, name, palette=None, vmin=None, vmax=None, opacity=1.0):
        # Uses single port 7777 with /<key>/...
        url = f"http://localhost:7777/{key}/tiles/{{z}}/{{x}}/{{y}}.png?projection=EPSG:3857"
        params = []
        if palette: params.append(f"colormap={palette}")
        if vmin is not None: params.append(f"min={vmin}")
        if vmax is not None: params.append(f"max={vmax}")
        if params:
            url += "&" + "&".join(params)
        return TileLayer(url=url, name=name, opacity=opacity)

    def _get_watershed_layer():
        if not WATERSHED_PATH or not WATERSHED_ID: return None
        try:
            gdf = gpd.read_file(WATERSHED_PATH)
            target = gdf[gdf['HYBAS_ID'] == WATERSHED_ID]
            if not target.empty:
                return GeoJSON(
                    data=target.__geo_interface__, 
                    style={'color': '#FFD700', 'fillOpacity': 0.0, 'weight': 4}, 
                    name=f"Watershed {WATERSHED_ID}"
                )
        except Exception: pass
        return None
        
    watershed_layer = solara.use_memo(_get_watershed_layer, dependencies=[])

    def update_layers():
        m = map_widget
        try:
            m.clear_layers()
            m.clear_controls()
            m.add_control(ZoomControl(position='topleft'))
            m.add_control(ScaleControl(position='bottomleft'))
            m.add_control(AttributionControl(position='bottomright', prefix='Geemap'))
            m.add_basemap("OpenStreetMap")
            
            # Layers - use Keys
            l_input = create_tile_layer("input", name="Input")
            
            l_right = None
            if layer_mode == "Flood Classification":
                l_right = create_tile_layer("class", name="Flood Classification", opacity=0.7)
            elif layer_mode == "Uncertainty":
                l_right = create_tile_layer("unc", name="Confidence", palette='Greens_r', vmin=0.0, vmax=threshold, opacity=0.7)

            if is_split:
                if l_input and l_right:
                    m.split_map(left_layer=l_input, right_layer=l_right)
                elif l_input: m.add_layer(l_input)
            else:
                if l_input: m.add_layer(l_input)
                if l_right: m.add_layer(l_right)
            
            if watershed_layer:
                m.add_layer(watershed_layer)
                
        except Exception as e:
            print(f"Layer Error: {e}")

    solara.use_effect(update_layers, dependencies=[is_split, layer_mode, threshold])

    with solara.Column(style={"height": "100vh"}):
        solara.Title("Step 2: Flood Visualization")
        with solara.Sidebar():
            solara.Markdown("### Configuration")
            solara.Checkbox(label="Enable Split View", value=show_split_map)
            solara.ToggleButtonsSingle(value=map_layer_mode, values=["Flood Classification", "Uncertainty"])
            
            if layer_mode == "Uncertainty":
                solara.Markdown("#### Confidence Filter")
                solara.SliderFloat(label="Max Uncertainty Tolerance", value=uncertainty_threshold, min=0.0, max=1.0, step=0.05)
                solara.Info(f"Uncertainty <= {threshold:.2f} shown. Dark Green = High Confidence.")

            solara.Markdown("---")
            solara.Warning("Note: Ensure Port 7777 is forwarded to localhost!")
            
        solara.display(map_widget)

if __name__ == "__main__":
    Page()
