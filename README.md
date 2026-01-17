「在開始開發 Step 2 的 UI 組件之前，請先幫我定義一套數據驗證邏輯。因為 Step 2 的輸入來自於 CLI Model 的輸出，我們需要確保以下資料狀態正確，才能進行視覺化：
請在 Step2Viewer 中加入一個 validate_inputs 方法，檢查以下項目：
坐標系統一致性 (CRS Check)：確認 input、output 與 uncertainty 三個 Raster 的 CRS 是否一致（通常應為 EPSG:4326 或與地圖一致）。空間對齊 (Spatial Alignment)：檢查三者的 Extent (Bbox) 是否完全重疊。檢查 Resolution (Pixel Size) 是否相同。如果不相同，請提供一個自動重採樣（Resampling）至 Output 解析度的建議做法。數值範圍驗證 (Value Range)：驗證 uncertainty_raster 的數值是否嚴格落在 \([0,1]\) 區間。如果數值超出範圍，應提供 Normalization（歸一化）功能。數據格式支援：支援讀取 Cloud Optimized GeoTIFF (COG) 或 NetCDF 格式。請先產出這個驗證邏輯的代碼框架，並說明如果資料不符合規範時，你會如何處理（例如報錯或自動對齊）。」
💡 為什麼要這樣要求？（與你討論）
避免地圖偏移：如果 CLI Model 輸出的座標系（例如 TWD97）跟 geemap 預設的（Web Mercator）不同，地圖會顯示不出來或位置對不上。遮罩邏輯的前提：你的 Step 2 核心功能是「根據不確定性遮罩 Output」，這代表這兩張圖的 Pixel 必須一對一對齊。如果解析度不同，numpy 或 xarray 在做 where 遮罩時會報錯。效能考量：如果你叫 Agent 先寫驗證，它可以先幫你決定要用 rioxarray 還是 gdal 來處理這些重度的矩陣運算。你目前的 CLI Model 產出的格式是哪一種？ (例如：一個資料夾裡放三張 .tif 檔？還是一個 .nc 檔包含多個變數？) 告訴 Agent 格式，它寫出來的驗證代碼會更精準。」



請多使用 @mcp deepwiki 來確定這個 geemap 套件如何使用