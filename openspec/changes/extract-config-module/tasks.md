# Tasks: Extract Configuration Module

## 1. 創建配置模組

- [x] 1.1 創建 `src/config.py` 包含所有常數
- [x] 1.2 添加 `load_yaml_config()` 函式讀取 dataset/config.yaml
- [x] 1.3 添加標題配置 (APP_TITLE, STEP1_TITLE, STEP2_TITLE)

## 2. 更新 Step 1

- [x] 2.1 修改 `src/step1/utils.py` - 使用 config 模組
- [x] 2.2 修改 `src/step1/app.py` - 使用 config 模組

## 3. 更新 Step 2

- [x] 3.1 修改 `src/step2/app.py` - 移除本地常數，使用 config 模組

## 4. 更新 Main

- [x] 4.1 修改 `src/main.py` - 使用標題配置

## 5. 更新啟動腳本

- [x] 5.1 修改 `start.sh` - 更新端口為 9100/9101

## 6. 驗證

- [x] 6.1 測試 config 模組 import
- [x] 6.2 測試 Step 1 import
- [x] 6.3 測試 Step 2 import
- [x] 6.4 測試 main import
