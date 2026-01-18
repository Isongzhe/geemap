# Geemap Flood Visualization App

這是一個基於 Solara 的互動式 Web 應用，用於選擇流域（watershed）並可視化洪水模型輸出結果（Sentinel-2 輸入影像、洪水分類、不確定性分析）。

## 📋 目錄

- [系統架構](#系統架構)
- [環境需求](#環境需求)
- [安裝步驟](#安裝步驟)
- [配置說明](#配置說明)
- [使用流程](#使用流程)
- [詳細說明](#詳細說明)
- [故障排除](#故障排除)
- [文件結構](#文件結構)

---

## 🏗️ 系統架構

### 單一服務架構（簡化版）

本系統採用簡化的單一服務架構，直接讀取 COG (Cloud Optimized GeoTIFF) 格式的數據：

```
┌─────────────────────────────────────────────────────────┐
│                     用戶瀏覽器                            │
│                  http://localhost:8765                  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │   Solara App (8765)  │
         │   Frontend + Tiles   │
         │   src/main.py        │
         │   + localtileserver  │
         └───────────┬──────────┘
                     │
         ┌───────────▼──────────┐
         │   COG Files          │
         │   input.tif          │
         │   output.tif         │
         └──────────────────────┘
```

**關鍵技術**:
- **Solara**: Reactive Web 框架
- **localtileserver**: 直接從 COG 提供地圖瓦片（內建於 Solara 應用）
- **ipyleaflet**: 互動式地圖組件
- **geemap**: 地理空間地圖庫

### 兩階段工作流程

#### Step 1: 流域選擇 (`src/step1/`)
1. 讀取 Sentinel-2 影像邊界
2. 從 HydroBASINS shapefile 中找出相交的流域
3. 在地圖上顯示候選流域（藍色邊框）
4. 用戶選擇流域（點擊或下拉選單）
5. 保存選擇到 `dataset/config.yaml`

#### Step 2: 洪水可視化 (`src/step2/`)
1. 載入 COG 格式的 GeoTIFF 數據
2. 使用 `localtileserver.TileClient` 生成地圖瓦片
3. 顯示三種圖層：
   - **Input**: Sentinel-2 原始影像
   - **Flood Classification**: 洪水分類結果（使用 OUTPUT_PATH Band 1）
   - **Uncertainty**: 不確定性熱圖（使用 OUTPUT_PATH Band 2）
4. 提供分析工具：
   - 分割視圖（Split View）：左右對比
   - 信心度滑桿：過濾低置信度區域

---

## 💻 環境需求

### 系統需求
- Python 3.13+
- Linux/macOS (Windows 需要 WSL)
- tmux (用於多進程管理)

### Python 依賴
主要依賴（定義於 `pyproject.toml`）：

```toml
geemap>=0.36.6          # 地理空間地圖庫
geopandas>=1.1.2        # 向量數據處理
localtileserver>=0.10.7 # COG 瓦片服務（內建）
pyproj>=3.7.2           # 坐標轉換
rasterio>=1.5.0         # 柵格 I/O
rioxarray>=0.20.0       # 柵格數據處理
solara>=1.56.0          # Reactive Web 框架
```

---

## 🚀 安裝步驟

### 1. Clone 專案
```bash
cd /path/to/your/workspace
git clone <your-repo-url>
cd geemap
```

### 2. 安裝 uv (如果還沒安裝)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. 創建虛擬環境並安裝依賴
```bash
uv sync
```

這會根據 `pyproject.toml` 和 `uv.lock` 安裝所有依賴到 `.venv/`。

### 4. 準備數據
確保以下數據文件存在並且是 **COG 格式**：
- **Sentinel-2 GeoTIFF** (`input_path`): COG 格式，至少 3 個波段（RGB）
- **洪水模型輸出 GeoTIFF** (`output_path`): COG 格式，2 個波段：
  - Band 1: 分類 (0-4, uint8)
  - Band 2: 不確定性 (0.0-1.0, float32)
- **HydroBASINS Shapefile**: 包含 `HYBAS_ID` 欄位

### 5. 配置 `dataset/config.yaml`
```yaml
model:
  input_path: /path/to/sentinel2.tif      # COG 格式
  output_path: /path/to/model_output.tif  # COG 格式，2 bands
watershed:
  default_id: null  # 第一次運行時為 null
  path: /path/to/hybas_shapefile.shp
```

---

## ⚙️ 配置說明

### `dataset/config.yaml` 結構

```yaml
model:
  # Sentinel-2 影像路徑（必須是 COG 格式）
  input_path: /path/to/input.tif

  # 模型輸出路徑（必須是 COG 格式，2 個波段）
  # Band 1: 分類 (0-4, uint8)
  # Band 2: 不確定性 (0.0-1.0, float32)
  output_path: /path/to/output.tif

watershed:
  # 當前選擇的流域 ID (由 Step 1 寫入)
  default_id: 5120274420

  # HydroBASINS Shapefile 路徑
  path: /path/to/hybas.shp
```

### 模型輸出格式要求

**Band 1 - 洪水分類** (uint8):
- 0: 無效/透明
- 1: 陸地 (灰色)
- 2: 水體 (藍色)
- 3: 雲 (白色)
- 4: 洪水 (紅色)

**Band 2 - 不確定性** (float32):
- 範圍: 0.0 ~ 1.0
- 0.0 = 高信心
- 1.0 = 低信心

---

## 📖 使用流程

### 方法 1: 使用腳本 (推薦)

#### 啟動服務
```bash
./start.sh
```

這會在 tmux session 中啟動 Solara 應用（port 8765）。

#### 查看日誌
```bash
tmux attach -t geemap
```

- `Ctrl+B, D` - Detach (不關閉服務)

#### 停止服務
```bash
./stop.sh
```

### 方法 2: 手動啟動（調試用）

```bash
uv run solara run src/main.py --host=0.0.0.0 --port=8765
```

### 遠端服務器配置

如果在遠端服務器（如 NAS）上運行，**必須**設置 SSH 端口轉發：

```bash
ssh -L 8765:localhost:8765 user@remote-server
```

或在 `~/.ssh/config` 中配置：
```
Host nas
    HostName your-nas-ip
    User your-username
    LocalForward 8765 localhost:8765
```

### 訪問應用
在瀏覽器中打開：
```
http://localhost:8765
```

---

## 🔍 詳細說明

### 數據流程

```
原始 COG 數據 (config.yaml)
    ├─ input_path: Sentinel-2.tif (COG, RGB bands)
    └─ output_path: model_output.tif (COG, 2 bands)

         ↓ (localtileserver.TileClient)

地圖瓦片 (XYZ Tiles, EPSG:3857)
    ├─ Input tiles (from input_path)
    ├─ Classification tiles (from output_path, band=1)
    └─ Uncertainty tiles (from output_path, band=2)

         ↓ (ipyleaflet)

互動式地圖 (Solara Frontend)
```

### 組件說明

#### `src/main.py`
- 主入口，路由 Step 1 和 Step 2
- 根據 `src/state.py` 中的 `current_step` 值切換頁面

#### `src/state.py`
- 全局狀態管理
- `current_step = solara.reactive(1)` - 當前步驟（1 或 2）

#### `src/step1/app.py`
- Step 1 主組件
- 響應式狀態：
  - `selected_watershed_id` - 當前選擇的流域 ID
  - `candidates_gdf` - 候選流域 GeoDataFrame
  - `map_center` - 地圖中心坐標

#### `src/step1/utils.py`
- `get_candidate_watersheds()`: 計算影像與流域的交集
- `save_selected_watershed()`: 保存選擇到 config.yaml

#### `src/step2/app.py`
- Step 2 主組件
- 使用 `localtileserver.TileClient` 直接從 COG 生成瓦片
- 響應式狀態：
  - `uncertainty_threshold` - 不確定性閾值滑桿
  - `show_split_map` - 是否啟用分割視圖
  - `map_layer_mode` - 圖層模式（分類/不確定性）

#### `src/step2/optimize_data.py` (可選)
- 數據預處理腳本（保留以備未來需要）
- 功能：下採樣、預渲染顏色、生成 cache
- **當前架構不使用**，直接讀取原始 COG

### 坐標系統

- **向量數據** (Shapefile): EPSG:4326 (WGS84)
- **地圖顯示** (Leaflet): EPSG:4326
- **瓦片服務**: EPSG:3857 (Web Mercator, localtileserver 自動處理)
- **柵格數據**: 任意 CRS（自動轉換）

### Solara 響應式模式

```python
# 創建響應式變量
my_var = solara.reactive(initial_value)

# 讀取值
value = my_var.value

# 設置值
my_var.set(new_value)

# 監聽變化
@solara.component
def MyComponent():
    value = my_var.value  # 當 my_var 改變時，組件重新渲染

# 副作用
solara.use_effect(callback, dependencies=[my_var.value])
```

---

## 🐛 故障排除

### 1. 地圖空白 / 瓦片無法載入

**症狀**: 地圖顯示但無影像圖層

**檢查步驟**:
```bash
# 1. 檢查 config.yaml 路徑是否正確
cat dataset/config.yaml

# 2. 檢查文件是否存在
ls -lh /path/to/input.tif
ls -lh /path/to/output.tif

# 3. 驗證是否為 COG 格式
uv run rio info /path/to/input.tif | grep -i "tiled\|overview"
# 應該看到 "Tiled: Yes" 和 overviews 資訊

# 4. 檢查 tmux 日誌
tmux attach -t geemap
# 查看錯誤訊息
```

**可能原因**:
- 文件路徑錯誤或不存在
- 文件不是 COG 格式
- 文件權限問題
- 遠端服務器未設置端口轉發

### 2. COG 格式驗證失敗

**症狀**: `TileClient` 報錯或瓦片渲染緩慢

**解決方案**:
```bash
# 驗證 COG 格式
uv run rio cogeo validate /path/to/your_file.tif

# 如果不是 COG，轉換為 COG
uv run rio cogeo create /path/to/input.tif /path/to/output_cog.tif
```

### 3. 流域選擇沒有候選項

**症狀**: Step 1 顯示 "No watersheds found"

**檢查步驟**:
```python
# 在 Python 中手動測試
import geopandas as gpd
import rioxarray

# 讀取影像邊界
with rioxarray.open_rasterio("path/to/input.tif") as src:
    bounds = src.rio.bounds()
    print(f"Image bounds: {bounds}")
    print(f"Image CRS: {src.rio.crs}")

# 讀取 shapefile
gdf = gpd.read_file("path/to/hybas.shp")
print(f"Shapefile CRS: {gdf.crs}")
print(f"Shapefile bounds: {gdf.total_bounds}")
```

**可能原因**:
- Shapefile 和影像沒有地理重疊
- CRS 不匹配導致坐標轉換錯誤
- Shapefile 路徑錯誤

### 4. Earth Engine 認證錯誤

**症狀**: Step 2 啟動時出現 EE 錯誤

**解決**:
```bash
# 認證 Earth Engine (可選，當前版本不需要)
earthengine authenticate
```

或忽略（當前實現使用 try/except 包裹 EE 初始化）。

### 5. tmux session 已存在

**症狀**: `./start.sh` 報錯 "session already exists"

**解決**:
```bash
# 方法 1: 先停止
./stop.sh

# 方法 2: 手動殺死 session
tmux kill-session -t geemap
```

### 6. 端口已被佔用

**症狀**: "Address already in use" 錯誤

**解決**:
```bash
# 查找佔用端口的進程
lsof -ti:8765

# 殺死進程
kill -9 <PID>

# 或使用 start.sh (會自動清理端口)
./start.sh
```

### 7. Solara 地圖不顯示

**症狀**: 頁面載入但地圖區域空白

**可能原因**:
- ipyleaflet widget 未正確初始化
- Jupyter widget 擴展未安裝

**解決**:
```bash
# 重新安裝 ipyleaflet
uv pip install --force-reinstall ipyleaflet
```

### 8. 分割視圖 (Split Map) 不工作

**症狀**: 勾選 "Enable Split View" 但地圖未分割

**調試步驟**:
1. 查看瀏覽器 console 是否有 JavaScript 錯誤
2. 確認 `geemap.Map.split_map()` 方法接收到正確的圖層
3. 檢查 `update_layers()` 是否被觸發（在 tmux 窗口查看 print 輸出）

---

## 📁 文件結構

```
geemap/
├── dataset/
│   ├── cache/                    # (可選) 優化後的 GeoTIFF
│   │   └── ...                   # 當前架構不使用，保留以備未來需要
│   ├── config.yaml               # 主配置文件
│   └── README.md                 # 數據說明
│
├── src/
│   ├── main.py                   # Solara 主入口
│   ├── state.py                  # 全局響應式狀態
│   ├── validator.py              # 數據驗證工具
│   │
│   ├── step1/                    # 流域選擇模組
│   │   ├── app.py                # Step 1 UI 組件
│   │   └── utils.py              # 流域查詢與保存
│   │
│   └── step2/                    # 洪水可視化模組
│       ├── app.py                # Step 2 UI 組件 (使用 localtileserver)
│       ├── optimize_data.py      # (可選) 數據優化腳本
│       └── debug/                # 調試工具
│           ├── check_data.py
│           ├── inspect_data.py
│           └── debug_plot.py
│
├── .venv/                        # Python 虛擬環境 (uv 管理)
├── pyproject.toml                # 專案配置與依賴
├── uv.lock                       # 依賴鎖定文件
├── start.sh                      # 啟動腳本
├── stop.sh                       # 停止腳本
├── README.md                     # 本文件
└── CLAUDE.md                     # Claude Code 指南
```

### 關鍵文件說明

| 文件 | 用途 | 何時修改 |
|------|------|----------|
| `dataset/config.yaml` | 數據路徑配置 | 每次更換數據集 |
| `src/state.py` | 全局狀態 | 添加新的跨步驟狀態 |
| `src/step1/utils.py` | 流域查詢邏輯 | 修改流域選擇算法 |
| `src/step2/app.py` | 主可視化邏輯 | 調整圖層、colormap |
| `src/step2/optimize_data.py` | (可選) 數據預處理 | 當需要下採樣或預渲染時 |
| `start.sh` | 啟動腳本 | 修改端口、環境變量 |

---

## 🔧 開發指南

### 調試技巧

#### 1. 測試單個組件
```bash
# 只運行 Step 1
uv run solara run src/step1/app.py

# 只運行 Step 2
uv run solara run src/step2/app.py
```

#### 2. 檢查 GeoTIFF 元數據
```bash
# 使用 rio CLI
uv run rio info dataset/cache/optimized_input.tif

# 驗證 COG 格式
uv run rio cogeo validate /path/to/file.tif

# 使用 gdalinfo
gdalinfo /path/to/file.tif
```

#### 3. 查看瓦片服務日誌
在 tmux 窗口中查看 localtileserver 的輸出：
```bash
tmux attach -t geemap
# localtileserver 會在 Solara 日誌中輸出瓦片請求
```

### 性能優化建議

1. **確保 COG 格式**: 使用 `rio cogeo create` 轉換
2. **添加 Overviews**: COG 應包含金字塔層級
3. **適當壓縮**: 使用 LZW 或 DEFLATE 壓縮
4. **文件大小**: 如果文件過大（>100MB），考慮使用 `optimize_data.py` 下採樣

### 添加新的 Colormap

修改 `src/step2/app.py`：

```python
# 在 update_layers() 函數中
l_right = get_leaflet_tile_layer(
    tile_clients['classification'],
    name="Flood Classification",
    opacity=0.7,
    colormap='RdYlBu_r'  # 改為其他 matplotlib colormap
)
```

可用的 colormap: `viridis`, `plasma`, `RdYlGn`, `RdYlBu`, `Spectral` 等。

---

## 📝 已知問題

1. **Earth Engine 初始化**: Step 2 嘗試初始化 EE 但未使用，可安全忽略錯誤
2. **Split Map 穩定性**: 頻繁切換 split view 可能導致圖層重疊，需刷新頁面
3. **Large COG Files**: 非常大的 COG 文件（>1GB）可能需要預處理以提升性能

---

## 📧 聯絡與支持

如有問題或需要協助，請檢查：
1. 本 README 的故障排除章節
2. `CLAUDE.md` 中的技術細節
3. tmux 日誌 (`tmux attach -t geemap`)

---

## 📜 授權

(根據您的專案添加授權訊息)
