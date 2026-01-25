# Change: Fix TileServer Port Configuration

## 問題

Step 2 使用 `localtileserver` 顯示 COG 影像時，熱重載會導致端口衝突錯誤：
```
Address already in use
Port 9000 is in use by another program
```

## 決策

使用 **三個固定端口**，簡單明確：

| 端口 | 用途 |
|------|------|
| 8765 | Solara Web UI |
| 9100 | TileServer - Input (Sentinel-2) |
| 9101 | TileServer - Output (Model) |

**注意**: 原本計劃使用 9000/9001，但這些端口被系統其他服務占用，改用 9100/9101。

## 解決方案

1. 使用 module-level singleton 確保 TileClient 只創建一次
2. 熱重載時重用已存在的 TileClient
3. 移除 try-except fallback，直接報錯便於除錯

## Port Forwarding

```bash
ssh -L 8765:localhost:8765 -L 9100:localhost:9100 -L 9101:localhost:9101 user@server
```

## Impact

- 修改: `src/step2/app.py` - singleton pattern for TileClients
- 修改: `CLAUDE.md` - 更新端口說明
