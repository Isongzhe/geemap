# Tasks: Fix TileServer Port Configuration

## 1. 修復 TileClient Singleton

- [x] 1.1 修改 `_create_tile_clients()` 使用正確的 singleton pattern
- [x] 1.2 Input TileClient 使用 port 9100
- [x] 1.3 Output TileClient 使用 port 9101
- [x] 1.4 確保熱重載時重用已存在的 TileClient
- [x] 1.5 移除 try-except fallback，直接報錯

## 2. 驗證

- [x] 2.1 測試首次啟動正常創建兩個 TileClient
- [x] 2.2 測試 singleton cache 正常運作
- [ ] 2.3 測試 Split view 功能正常（需啟動完整應用測試）

## 3. 文檔更新

- [x] 3.1 更新 CLAUDE.md 端口說明
