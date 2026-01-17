from flask import Flask, send_file, request, Response
from rio_tiler.io import Reader
from rio_tiler.colormap import cmap
from io import BytesIO
import os

app = Flask(__name__)

# Cache Paths
CACHE_DIR = "dataset/cache"
IMAGES = {
    "input": os.path.join(CACHE_DIR, "optimized_input.tif"),
    "class": os.path.join(CACHE_DIR, "optimized_class_rgb.tif"),
    "unc": os.path.join(CACHE_DIR, "optimized_uncertainty.tif")
}

@app.route('/health')
def health():
    return "OK"

@app.route('/<key>/tiles/<int:z>/<int:x>/<int:y>.png')
def tile(key, z, x, y):
    path = IMAGES.get(key)
    if not path or not os.path.exists(path):
        return "Image not found", 404

    try:
        with Reader(path) as cog:
            # Handle Colormap for Uncertainty (Float)
            # Input request might have arguments like ?colormap=Greens_r&min=0&max=1
            # But rio_tiler handles rendering differently depending on method.
            
            # 1. Read Tile
            img = cog.tile(x, y, z)
            
            # 2. Rendering
            # URL params
            colormap_name = request.args.get('colormap')
            vmin = request.args.get('min', type=float)
            vmax = request.args.get('max', type=float)
            
            if key == "unc" and colormap_name:
                # Apply colormap to single band float
                # Rescale first if needed? rio_tiler 'render' handles basic rescaling if we pass stats?
                # Actually, standard way:
                # img.post_process(color_formula=...) or just render with colormap
                
                # Simple approach for float data (Uncertainty):
                # We need to normalize to 0-255 for colormap application or let rio_tiler do it.
                # img.render(colormap=...) works if data is uint8 usually, or we use scales.
                
                # Explicit rescale for float 0..1 to 0..255?
                # Let's trust render's 'colormap' argument which applies to valid data.
                
                # Wait, if we use 'min/max' from slider (e.g. 0 to threshold), we might want to mask?
                # For now, just render.
                output = img.render(img_format="PNG", colormap=cmap.get(colormap_name))
                
            elif key == "class":
                # It is already RGB (Baked), just render.
                output = img.render(img_format="PNG")
                
            else:
                # Input (RGB), just render.
                output = img.render(img_format="PNG")

            return send_file(BytesIO(output), mimetype='image/png')
            
    except Exception as e:
        print(f"Error serving tile {key} {z}/{x}/{y}: {e}")
        return str(e), 500

if __name__ == '__main__':
    print("Starting Unified Tile Server on 7777...")
    # Threaded for concurrent tile requests
    app.run(host='0.0.0.0', port=7777, threaded=True)
