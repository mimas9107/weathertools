# 🌤️ 天氣工具 (Weather Tools)

中央氣象署天氣資料抓取工具與監視器畫面天氣分析工具。

## 📦 安裝

```bash
# 使用 uv 安裝依賴
uv sync

# 安裝 Playwright 瀏覽器
uv run playwright install chromium
```

## ⚙️ 環境變數設定

複製 `.env.example` 為 `.env` 並填入您的 API Key：

```bash
cp .env.example .env
```

編輯 `.env` 檔案：

```
# 中央氣象署 API Key
CWB_API_KEY=您的API Key

# Viewpoints API 帳號密碼
VIEWPOINTS_USERNAME=您的帳號
VIEWPOINTS_PASSWORD=您的密碼
```

## 🚀 使用方式

### 天氣資料抓取

```bash
uv run weather.py
```

### GPS 測站定位

根據 GPS 座標自動找出最近測站，取得即時觀測資料。支援 DD / DMS / DDM 多種格式輸入，3km 內單站直出、以外多站平均。

→ 詳細說明請見 [`README-gps.md`](README-gps.md)

```bash
uv run weather_gps.py "24.992301, 121.417556"
```

### 監視器畫面分析

```bash
uv run weather_vision.py
```

執行程式後，輸入選項：
- `1`: 分析特定監視器畫面
- `2`: 分析所有監視器畫面
- `q`: 離開

## 📁 目錄結構

```
weathertools/
├── weather.py          # 中央氣象署天氣資料抓取
├── weather_vision.py  # 監視器畫面天氣分析 (Ollama Vision)
├── weather_gps.py     # GPS 測站定位工具（本文件）
├── README-gps.md      # GPS 工具說明文件
├── pyproject.toml      # 專案設定
├── .env               # 環境變數 (請勿提交至 Git)
├── .env.example       # 環境變數範本
├── screenshots/       # 擷取的監視器畫面
└── tests/             # 測試檔案
```

## 📝 支援的監視器類型

| 類型 | 描述 | 擷取方式 |
|------|------|----------|
| `image` | 靜態圖片/MJPEG 串流 | 直接下載 |
| `youtube` | YouTube 串流 | Playwright 截圖 |
| `hls` | HLS 串流 | Playwright 截圖 |

## 🔑 功能特色

### weather.py
- 取得中央氣象署天氣資料
- 取得即時觀測資料
- 取得紫外線指數 (UVI)
- 天氣代碼翻譯

### weather_vision.py
- 從 viewpoints API 取得監視器列表, 參考專案: [https://github.com/mimas9107/viewpoints](https://github.com/mimas9107/viewpoints)
- 支援 JWT 登入認證
- 使用 Ollama Vision Model 分析天氣
- 顯示天氣、能見度、光線、天空狀態

### weather_gps.py
- 給定 GPS 座標，自動判別 DD / DMS / DDM 格式
- 找出最近 2~3 個測站的即時觀測資料並平均
- 目標 3km 內有測站時直接以該站為準（不強制湊數）
- 風向採用向量平均，避免角度繞圈錯誤

## 📋 需求

- Python 3.11+
- [Ollama](https://ollama.com/) (本機執行用於圖片分析)
- 中央氣象署 API Key
- Viewpoints 帳號密碼
