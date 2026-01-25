# Design: TileServer Port Configuration

## 架構

```
Browser (localhost)
    │
    ├── :8765 → Solara App
    │
    ├── :9000 → TileServer (Input - Sentinel-2)
    │
    └── :9001 → TileServer (Output - Model)
```

## Singleton Pattern

```python
# Module-level cache (在 import 時初始化)
_tile_clients_cache = {}

def _create_tile_clients():
    global _tile_clients_cache

    # 已存在則直接返回
    if _tile_clients_cache:
        return _tile_clients_cache

    # 首次創建
    _tile_clients_cache['input'] = TileClient(
        INPUT_PATH,
        port=9000,
        host='0.0.0.0',
        client_port=9000,
        client_host='localhost'
    )

    _tile_clients_cache['output'] = TileClient(
        OUTPUT_PATH,
        port=9001,
        host='0.0.0.0',
        client_port=9001,
        client_host='localhost'
    )

    return _tile_clients_cache
```

## 為何需要 Singleton

1. **Solara 熱重載**: 組件重新渲染時會再次調用 `use_memo`
2. **TileClient 生命週期**: 每個 TileClient 啟動一個 Flask server
3. **端口衝突**: 同一端口不能重複綁定

## 端口分配

| 端口 | 服務 | Host | Client Host |
|------|------|------|-------------|
| 8765 | Solara | 0.0.0.0 | localhost |
| 9000 | Input Tiles | 0.0.0.0 | localhost |
| 9001 | Output Tiles | 0.0.0.0 | localhost |

## SSH Port Forwarding

```bash
ssh -L 8765:localhost:8765 \
    -L 9000:localhost:9000 \
    -L 9001:localhost:9001 \
    user@remote-server
```
