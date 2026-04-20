# 🌿 MEMOIR: 專案情境與狀態管理 🌿

## 🌍 專案概覽
- **名稱**: weathertools
- **版本**: 0.2.0
- **描述**: 中央氣象署天氣資料抓取工具與監視器畫面天氣分析工具
- **環境**: Python (透過 .py 檔案和 pyproject.toml 偵測)
- **狀態**: 已初始化 ✅
- **目標**: 維護任務定義的單一來源真相，追蹤任務與語言情境的連結 (`[PY]`、`[JS]` 等)

## 📁 偵測到的模組與技術堆疊
- **核心邏輯**: `weather.py` (Python) - 中央氣象署 API
- **視覺/圖片處理**: `weather_vision.py` (Python) - Playwright + Ollama Vision
- **測試**: `tests/` 目錄 (Python) - 包含 `weather.py` 和 `weather_analyzer.py`
- **設定**: `pyproject.toml`

## ✅ 已完成的任務

### [x] [PY] 整合 viewpoints API 登入認證機制
- **狀態**: 已完成 ✅ (2025-04-20 行為驗證通過)
- **說明**: 更新 `weather_vision.py` 以支援 JWT 登入流程，能夠從 render.com 上的 viewpoints 服務取得授權
- **驗證**: 執行 `uv run weather_vision.py` → ✅ 登入成功，已取得 Token / ✅ 成功獲取 9 個可分析的監視器設定

### [x] [PY] 改善 Playwright 截圖失敗處理
- **狀態**: 已完成 ✅ (2025-04-20 行為驗證通過)
- **說明**: 更新 Playwright 邏輯，使用多重備用選擇器 (`.player-container` → `video` → `iframe` → `body`)，確保 YouTube/HLS 串流的截圖穩定性
- **驗證**: YouTube 串流截圖成功 (8/8 cameras)

### [x] [PY] 專案文件更新
- **狀態**: 已完成 ✅ (2025-04-20 驗證通過)
- **說明**: 更新 `README.md` 和 `MEMOIR.md`，使用繁體中文
- **驗證**: 檔案存在且語法正確

## 📝 待辦任務格式範例
```
- [ ] [PY] 新增功能到 `weather.py` ...
- [ ] [TEST/PY] 為 `weather_analyzer.py` 撰寫單元測試 ...
```

## 📚 使用指南
- 定義新任務時，請遵循格式：任務描述與明確的語言情境 (例如：`[PY]`、`[JS]`)
- 使用狀態指示器：
  - `[ ]`: 任務已定義但尚未開始
  - `[/]`: 程式碼已撰寫並通過語法檢查
  - `[x]`: 任務已完成並通過驗證