# Step 2: Flood Model Visualization

This module (`src/step2/app.py`) provides an interactive interface to visualize Sentinel-2 imagery and Flood Model predictions. It is designed to work in a **Remote Server Environment** where direct port access is limited.

## 🏗 System Architecture

### 1. Data Pipeline & Optimization
Due to the large size of Sentinel-2 Satellite imagery (~GBs), serving raw files directly results in severe lag. We implemented an **Optimization Pipeline**:

*   **Script**: `src/step2/optimize_data.py`
*   **Process**:
    1.  **Downsampling**: Reduces resolution by 4x.
    2.  **Color Baking**: Converts the categorical "Flood Classification" (0-4) into a visual **RGB GeoTIFF** (Pastel Colors). This avoids browser-side palette rendering issues.
    3.  **Uncertainty Masking**: Generates a smart **RGBA Mask** where "High Uncertainty" areas are tinted yellow/opaque, and "Reliable" areas are transparent.
*   **Cache**: Optimized files are stored in `dataset/cache/`.

### 2. Remote Tile Serving (localtileserver)
The visualization uses `localtileserver` to serve these optimized rasters as XYZ tiles.
Crucially, **Fixed Ports** are used to allow SSH Tunneling:

| Port | Content | Source File | Description |
| :--- | :--- | :--- | :--- |
| **7777** | Input Image | `optimized_input.tif` | Sentinel-2 RGB (True Color) |
| **7778** | Flood Map | `optimized_class_rgb.tif` | Pre-rendered Classification Map |
| **7779** | Uncertainty | `optimized_uncertainty_mask.tif` | Reliability Overlay (RGBA) |

### 3. Frontend (Solara + Geemap)
*   **Framework**: `solara` (React-like Python UI) + `geemap` (Leaflet wrapper).
*   **State Management**: Uses `solara.reactive` and `use_effect` to handle Map Layer switching and Split View logic.
*   **Features**:
    *   **Split Map**: Compare Input vs. Output side-by-side.
    *   **Layer Switching**: Toggle between "Flood Classification" and "Uncertainty" modes.
    *   **Static Preview**: Hardcoded static image (`debug_raster_plot.png`) for quick verification.

## 🚀 How to Run

1.  **Generate Cache** (First time only):
    ```bash
    uv run python optimize_data.py
    ```

2.  **Start Application**:
    ```bash
    ./start.sh
    ```
    *This script handles cleanup, port checking, and tmux session management.*

3.  **Configure Port Forwarding** (Local Machine):
    Forward the following ports via VSCode or SSH:
    *   `8765` (App)
    *   `7777`, `7778`, `7779` (Tile Servers)

## 🎨 Visualization Logic

### Flood Classification (Port 7778)
Displayed using a **Pastel Palette** for clarity:
*   ⬛ **Transparent**: Invalid Data (無效值)
*   ⬜ **Gray**: Land (陸地)
*   🟦 **Cornflower Blue**: **Permanent Water** (常態水體) - 例如河流、湖泊，平時就存在的水域。
*   ⬜ **White**: Clouds (雲層)
*   🟥 **Salmon Red**: **Predicted Flood** (預測淹水) - 模型判斷為異常水體或淹水痕跡的區域 (原本應該是陸地的地方)。

> **Note**: 藍色 vs 紅色的差別在於：**藍色**是模型認為「這本來就是水 (河流/湖泊)」，而**紅色**是模型警告「這里被水淹了 (災情)」。


### Uncertainty Mask (Port 7779)
Used to filter or warn about unreliable predictions:
*   **Transparent**: Highly Reliable (Uncertainty < 0.2)
*   **Yellow Tint**: Warning (0.2 < Uncertainty < 0.8)
*   **Dark Mask**: Unreliable (Uncertainty > 0.8)

## 🛠 Troubleshooting
*   **Blank Map?** Check if Ports 7777-7779 are forwarded.
*   **Zoom Control Missing?** Ensure `ipyleaflet` is installed.
*   **Changes not showing?** Run `./start.sh` to hard-restart the process (Step 2 needs fresh ports).
