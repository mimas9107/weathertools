# 🛰️ GPS 測站定位工具 — `weather_gps.py`

給定 GPS 座標，自動判別格式後，從中央氣象署 API (O-A0001-001) 找出最近 2~3 個測站的即時觀測資料並平均回傳。若目標點位 3km 內有測站，則直接以該站為準。

---

## 🚀 使用方式

### CLI

```bash
# DD 格式（OpenStreetMap / 多數地圖）
uv run weather_gps.py "24.992301, 121.417556"

# DMS 格式（Google Maps）
uv run weather_gps.py "24°59'32.1\"N 121°25'03.4\"E"

# DDM 格式
uv run weather_gps.py "24°59.535'N 121°25.057'E"

# 指定取 5 站平均（預設 3 站）
uv run weather_gps.py "23.5, 119.5" 5

# 顯示說明
uv run weather_gps.py --help
```

### Python API

```python
from weather_gps import get_nearby_observations

result = get_nearby_observations("24.992301, 121.417556")
# 或 result = get_nearby_observations((24.992301, 121.417556))

print(result["avg_temperature"])    # 平均溫度
print(result["avg_humidity"])       # 平均濕度
print(result["avg_wind_speed"])     # 平均風速
print(result["weather"])            # 天氣現象（取最近站）
print(result["stations_used"])      # 使用的測站清單
```

---

## 📡 演算法邏輯

```
GPS 輸入 → parse_coordinate() → (lat, lon) WGS84 DD
    │
    ├─ fetch_all_stations() → O-A0001-001 全部測站
    │
    ├─ haversine() 算每站距離 → 排序
    │
    ├─ 最近站 < 3km → 單站模式（不強制湊 n 站）
    │
    └─ 最近站 ≥ 3km → 取 top n 站 → 平均
```

### 平均邏輯 (`_average_obs`)
- **數值欄位**（溫度、濕度、氣壓、風速、雨量）：排除 `-99`（CWA 無效值記號）後算術平均
- **風向**：向量平均（sin/cos 合成），避免 `359° + 1° = 180°` 經典錯誤
- **天氣文字**：取最近測站的值，不平均

---

## 🔤 GPS 格式支援

| 格式 | 範例 | 判別方式 |
|------|------|----------|
| **DD** (十進位度數) | `24.992301, 121.417556` | 純數字 + 逗號/空格 |
| **DMS** (度分秒) | `24°59'32.1"N 121°25'03.4"E` | ° ' " + N/S, E/W |
| **DDM** (度分) | `24°59.535'N 121°25.057'E` | ° + 小數分 + N/S, E/W |
| **tuple/list** | `(24.992301, 121.417556)` | Python 型別判斷 |

內部統一轉為 WGS84 十進位度數（DD）後再進行距離計算。

---

## 📁 API 參考

### `parse_coordinate(input) → (lat, lon) | None`

自動判別 GPS 格式並轉為 WGS84 DD。

### `haversine(lat1, lon1, lat2, lon2) → float`

兩點大圓距離（公里）。使用 WGS84 赤道半徑 6371km。

### `get_nearby_observations(gps_input, n=3) → dict`

主功能。回傳結構：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `gps_parsed` | `(float, float)` | 解析後的 WGS84 座標 |
| `mode` | `str` | `"single_station"` 或 `"averaged"` |
| `stations_used` | `list[dict]` | 測站 ID、名稱、縣市、距離 |
| `avg_temperature` | `float` | 平均溫度 (°C) |
| `avg_humidity` | `float` | 平均濕度 (%) |
| `avg_pressure` | `float` | 平均氣壓 (hPa) |
| `avg_wind_speed` | `float` | 平均風速 (m/s) |
| `avg_wind_direction` | `float` | 平均風向 (度) |
| `avg_precipitation` | `float` | 平均雨量 (mm) |
| `weather` | `str` | 天氣現象（最近測站） |

### `print_nearby_weather(result)`

格式化輸出結果至 stdout。

### `fetch_all_stations() → list[dict]`

直接呼叫 CWA O-A0001-001，回傳原始測站列表。

---

## ⚙️ 環境變數

僅需 `CWB_API_KEY`（與 `weather.py` 共用）。

```
CWB_API_KEY=您的API金鑰
```

---

## 📋 需求

- Python 3.11+
- `requests`
- `python-dotenv`
- 中央氣象署 API Key（[申請](https://opendata.cwa.gov.tw/)）

以上套件已包含在 `pyproject.toml` 中，`uv sync` 後即可使用。
