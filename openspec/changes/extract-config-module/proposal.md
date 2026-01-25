# Change: Extract Configuration Module

## Why

目前配置散落在多個檔案中：

| 檔案 | 配置項目 |
|------|----------|
| `src/step2/app.py` | 端口 (9100, 9101), colormap, zoom, EE_PROJECT |
| `src/step1/app.py` | 預設 map center, zoom |
| `src/step1/utils.py` | config.yaml 路徑硬編碼 |
| `start.sh` | 端口 (8765, 9000, 9001) - 與程式碼不一致！ |
| `dataset/config.yaml` | 資料路徑配置 |

問題：
1. 端口配置在 start.sh (9000/9001) 和 step2/app.py (9100/9101) 不一致
2. 修改配置需要改多個檔案
3. 難以維護

## What Changes

創建 `src/config.py` 集中管理所有配置：

```
src/config.py          ← 新增：所有 Python 配置
dataset/config.yaml    ← 保留：資料路徑（用戶可編輯）
start.sh / stop.sh     ← 更新：從 config 讀取端口
```

## 配置分類

### 1. 應用程式配置 (src/config.py)
```python
# Ports
SOLARA_PORT = 8765
INPUT_TILE_PORT = 9100
OUTPUT_TILE_PORT = 9101

# Map Defaults
DEFAULT_CENTER = (20.0, 0.0)
DEFAULT_ZOOM = 2
WATERSHED_ZOOM = 11

# Visualization
CLASSIFICATION_COLORMAP = 'viridis'
UNCERTAINTY_COLORMAP = 'rdylgn_r'
WATERSHED_COLOR = '#FFD700'

# Earth Engine
EE_PROJECT = "geemap-484609"

# Config file path
CONFIG_YAML_PATH = "dataset/config.yaml"
```

### 2. 資料路徑配置 (dataset/config.yaml)
- `model.input_path`
- `model.output_path`
- `watershed.root_path`
- `watershed.region`
- `watershed.level`
- `watershed.default_id`

## Impact

- 新增: `src/config.py`
- 修改: `src/step1/app.py` - import from config
- 修改: `src/step1/utils.py` - import from config
- 修改: `src/step2/app.py` - import from config
- 修改: `start.sh` - 更新端口為 9100/9101
- 保留: `dataset/config.yaml`
