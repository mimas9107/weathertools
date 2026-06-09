---
name:              "README-tdx.md"
description:       "TDX 交通監視器查詢工具說明文件"
created_date:      "2026/06/09"
modified_date:     "2026/06/09"
project_version:   "0.3.1"
document_version:  "1.0.0"
agent_sign:        ['human/justin', 'opencode/deepseek-v4-flash-free']
---

# TDX 交通監視器查詢工具 — `weather_tdx.py`

串接 TDX (Transport Data eXchange) 運輸資料平台，查詢全台交通監視器 GPS 座標，
並結合 `weather_gps.py` 取得最近測站天氣觀測。

---

## 使用方式

### CLI

```bash
# 依 CCTVID 查單一監視器 GPS
uv run weather_tdx.py id T000029

# 查臺北市前 5 支監視器
uv run weather_tdx.py city Taipei 5

# 依路名查詢
uv run weather_tdx.py road 敦化南路

# 查附近 0.5km 範圍監視器
uv run weather_tdx.py nearby 25.04497 121.54888 0.5

# 監視器 GPS + 附近天氣
uv run weather_tdx.py weather T000029

# 顯示說明
uv run weather_tdx.py --help
```

### Python API

```python
from weather_tdx import (
    query_cctv_by_id,
    query_cctv_by_city,
    query_cctv_by_road,
    query_cctv_nearby,
    get_camera_weather,
)

# 單一監視器
cam = query_cctv_by_id("T000029")
print(cam["RoadName"], cam["PositionLat"], cam["PositionLon"])

# 縣市所有監視器
cams = query_cctv_by_city("Taipei", top=10)

# 路名查詢
cams = query_cctv_by_road("敦化南路", city="Taipei")

# 附近範圍查詢
cams = query_cctv_nearby(25.04497, 121.54888, radius_km=0.5)

# 整合天氣
result = get_camera_weather("T000029")
print(result["cctv_gps"])    # (25.04497, 121.54888)
print(result["weather"]["avg_temperature"])
```

---

## API 參考

### `query_cctv_by_id(cctv_id, city=None) -> dict | None`

依 CCTVID 查詢單一監視器 GPS。

優先使用精準端點 `City/{city}/{id}`（單次 API 呼叫），
退路為依 ID 首碼推測縣市後搜尋，或逐一掃描所有縣市。

回傳欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `CCTVID` | `str` | 攝影機代碼 |
| `RoadName` | `str` | 所在道路 |
| `PositionLat` | `float` | 緯度 (WGS84) |
| `PositionLon` | `float` | 經度 (WGS84) |
| `VideoStreamURL` | `str` | 串流網址 |

### `query_cctv_by_city(city, top=300) -> list[dict]`

查詢指定縣市所有監視器（含快取）。

### `query_cctv_by_road(road_keyword, city=None, top=30) -> list[dict]`

依路名關鍵字查詢（全縣市或全國）。

### `query_cctv_nearby(lat, lon, radius_km=1.0, city=None, top=20) -> list[dict]`

查詢指定座標附近 `radius_km` 公里範圍內的監視器，依距離排序。

### `get_camera_weather(cctv_id, n_stations=3) -> dict`

查詢監視器 GPS 並自動代入 `weather_gps.py` 取得最近 `n_stations` 個測站天氣。

回傳結構：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `cctv_id` | `str` | 攝影機代碼 |
| `cctv_name` | `str` | 道路名稱 |
| `cctv_gps` | `(float, float)` | 監視器座標 |
| `weather` | `dict` | `get_nearby_observations()` 回傳（見 README-gps.md） |
| `error` | `str | None` | 錯誤訊息 |

---

## 查詢策略

```
CCTVID → _city_from_id() 首碼推測縣市
    │
    ├─ 精準端點: City/{city}/{id}  ← 優先，單次 API
    │
    └─ 退路: City/{city}?$top=300 → 逐筆過濾
```

全國性查詢（road / nearby 無指定 city）會逐一查詢 20 個縣市。
`_city_cache` 會快取每個縣市結果，避免重複請求。

---

## Rate Limit 處理

TDX API 有 rate limit（HTTP 429 回應）。
- `_tdx_get()` 收到 429 時回傳 `None`，不噴例外
- City cache 減少重複查詢
- 精準端點 `City/{city}/{id}` 大幅降低請求量

---

## 環境變數

```
TDX_CLIENT_ID=您的用戶端ID
TDX_CLIENT_SECRET=您的用戶端密鑰
```

申請 TDX 帳號：https://tdx.transportdata.tw/

---

## 需求

- Python 3.11+
- `requests`
- `python-dotenv`
- TDX Client ID / Secret
