# Change: Refactor Step 2 to Event-Driven File Loading

## Why

原本 Step 2 使用固定的 `input_path` 和 `output_path` 從 config.yaml 載入檔案。這種方式不靈活，無法支援多個事件日期的資料切換。

需要改為根據 `event_date` 動態查找對應的輸入輸出檔案。

## What Changes

1. **Config 新增函數**
   - `get_model_config()`: 讀取 event_date, input_folder, output_folder

2. **新增 Step 2 工具模組**
   - `src/step2/utils.py`: 檔案查找函數
   - `find_event_input(event_date, input_folder)`: 根據 event_date 查找 S2 輸入檔
   - `find_event_output(event_date, output_folder)`: 根據 event_date 查找 EDL 輸出檔

3. **Step 2 主邏輯更新**
   - 改用 event_date 驅動檔案載入
   - 動態查找對應檔案，而非固定路徑
   - Sidebar 新增 Event Information 卡片顯示 Event Date 和 Return Period

4. **SplitMapControl 修復**
   - 修復切換模式時 SplitMapControl 重複的問題
   - 使用模組級別 `_current_split_control` 追蹤當前控制項
   - 在更新圖層前先移除舊的 SplitMapControl

5. **Legend 格式修復**
   - 修正 Classification Legend 和 Uncertainty Legend 的 markdown 格式問題

## Impact

- 新增: `src/step2/utils.py`
- 修改: `src/config.py` - 新增 `get_model_config()`, `get_analog_df_config()`
- 修改: `src/step2/app.py` - 事件驅動載入、SplitMapControl 修復、Legend 格式
- 修改: `dataset/config.yaml` - 新增 `event_date`, `input_folder`, `output_folder` 欄位
