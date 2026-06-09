#!/usr/bin/env python3
"""
天氣觀測 GPS 定位工具

給定 GPS 座標，自動判別格式後，從中央氣象署 API (O-A0001-001)
找出最近 2~3 個測站的即時觀測資料並平均回傳。
若目標點位 3km 內有測站，則直接以該站為準。
"""

import os
import re
import math
import sys
from datetime import datetime
from typing import Optional, Union

import requests
from dotenv import load_dotenv

CWB_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
OBS_DATASET_ID = "O-A0001-001"
NEARBY_THRESHOLD_KM = 3.0

load_dotenv()


def get_cwb_api_key() -> str:
    return os.getenv("CWB_API_KEY", "")


# ─── GPS 格式判別 ────────────────────────────────────────────────


def _dd_from_parts(degrees: float, minutes: float, seconds: float, direction: str) -> float:
    dd = degrees + minutes / 60 + seconds / 3600
    if direction.upper() in ("S", "W"):
        dd = -dd
    return dd


def parse_coordinate(input_data: Union[str, tuple, list]) -> Optional[tuple[float, float]]:
    """
    自動判別 GPS 格式並轉換為 WGS84 十進位度數 (lat, lon)。

    支援格式：
      - DMS:   "24°59'32.1"N 121°25'03.4"E"
      - DDM:   "24°59.535'N 121°25.057'E"
      - DD:    "24.992301, 121.417556" | "24.992301 121.417556"
      - tuple: (24.992301, 121.417556) | [24.992301, 121.417556]
    """
    if isinstance(input_data, (tuple, list)):
        if len(input_data) != 2:
            return None
        try:
            return (float(input_data[0]), float(input_data[1]))
        except (ValueError, TypeError):
            return None

    if not isinstance(input_data, str):
        return None

    s = input_data.strip()

    # ── DMS: 24°59'32.1"N 121°25'03.4"E ──
    m = re.search(
        r"(\d+)[°º]\s*(\d+)['′]\s*([\d.]+)[\"″]?\s*([NnSs])"
        r"\s+"
        r"(\d+)[°º]\s*(\d+)['′]\s*([\d.]+)[\"″]?\s*([EeWw])",
        s,
    )
    if m:
        lat = _dd_from_parts(float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4))
        lon = _dd_from_parts(float(m.group(5)), float(m.group(6)), float(m.group(7)), m.group(8))
        return (lat, lon)

    # ── DDM: 24°59.535'N 121°25.057'E ──
    m = re.search(
        r"(\d+)[°º]\s*([\d.]+)['′]?\s*([NnSs])"
        r"\s+"
        r"(\d+)[°º]\s*([\d.]+)['′]?\s*([EeWw])",
        s,
    )
    if m:
        lat = _dd_from_parts(float(m.group(1)), float(m.group(2)), 0, m.group(3))
        lon = _dd_from_parts(float(m.group(4)), float(m.group(5)), 0, m.group(6))
        return (lat, lon)

    # ── DD: "24.992301, 121.417556" or "24.992301 121.417556" ──
    nums = re.findall(r"-?\d+\.?\d*", s)
    if len(nums) >= 2:
        try:
            return (float(nums[0]), float(nums[1]))
        except ValueError:
            pass

    return None


# ─── 距離計算 ────────────────────────────────────────────────────


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """計算兩 WGS84 座標的大圓距離（公里）。"""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── CWA API ─────────────────────────────────────────────────────


def _get_wgs84(station: dict) -> Optional[tuple[float, float]]:
    coords = station.get("GeoInfo", {}).get("Coordinates", [])
    for c in coords:
        if c.get("CoordinateName") == "WGS84":
            try:
                return (float(c["StationLatitude"]), float(c["StationLongitude"]))
            except (KeyError, ValueError, TypeError):
                return None
    return None


def _is_valid(value: str) -> bool:
    """CWA 觀測值是否有效（排除 -99 與空值）。"""
    if not value or value.strip() == "":
        return False
    try:
        return abs(float(value) + 99) > 0.001
    except ValueError:
        return False


def fetch_all_stations() -> list[dict]:
    """取得所有測站的即時觀測資料。"""
    auth_key = get_cwb_api_key()
    if not auth_key:
        return []

    params = {"Authorization": auth_key, "format": "JSON", "limit": 1000}

    try:
        resp = requests.get(f"{CWB_API_URL}/{OBS_DATASET_ID}", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("records", {}).get("Station", [])
    except requests.exceptions.RequestException:
        return []


# ─── 平均邏輯 ────────────────────────────────────────────────────


def _average_wind_direction(degrees_list: list[float]) -> Optional[float]:
    """風向向量平均，避免 359° + 1° = 180° 問題。"""
    sin_sum = sum(math.sin(math.radians(d)) for d in degrees_list)
    cos_sum = sum(math.cos(math.radians(d)) for d in degrees_list)
    avg = math.degrees(math.atan2(sin_sum, cos_sum))
    return avg + 360 if avg < 0 else avg


def _percentile(data: list[float], p: int) -> float:
    """線性內插計算百分位數（同 numpy 預設方法）。"""
    if not data:
        return 0.0
    s = sorted(data)
    n = len(s)
    if n == 1:
        return s[0]
    idx = (n - 1) * p / 100
    lower = int(idx)
    upper = min(lower + 1, n - 1)
    weight = idx - lower
    return s[lower] * (1 - weight) + s[upper] * weight


def _quartile_deviation(data: list[float]) -> float:
    """計算半四分位距 (Q3 - Q1) / 2。"""
    q1 = _percentile(data, 25)
    q3 = _percentile(data, 75)
    return (q3 - q1) / 2


def _average_obs(stations: list[dict]) -> dict:
    """
    平均多站觀測資料。

    - 數值欄位：排除 -99 後算術平均，附半四分位距
    - 風向：向量平均
    - 天氣文字：取最近測站
    """
    if not stations:
        return {}

    temps, hums, press, winds, rains, wind_dirs = ([] for _ in range(6))

    for s in stations:
        we = s.get("WeatherElement", {})

        if _is_valid(we.get("AirTemperature")):
            temps.append(float(we["AirTemperature"]))
        if _is_valid(we.get("RelativeHumidity")):
            hums.append(float(we["RelativeHumidity"]))
        if _is_valid(we.get("AirPressure")):
            press.append(float(we["AirPressure"]))
        if _is_valid(we.get("WindSpeed")):
            winds.append(float(we["WindSpeed"]))
        if _is_valid(we.get("WindDirection")):
            wind_dirs.append(float(we["WindDirection"]))
        if _is_valid(we.get("Now", {}).get("Precipitation")):
            rains.append(float(we["Now"]["Precipitation"]))

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    def avg_and_q(lst):
        if not lst:
            return (None, None)
        return (avg(lst), round(_quartile_deviation(lst), 1))

    at, qt = avg_and_q(temps)
    ah, qh = avg_and_q(hums)
    ap, qp = avg_and_q(press)
    aws, qws = avg_and_q(winds)
    ar, qr = avg_and_q(rains)

    avg_wd = round(_average_wind_direction(wind_dirs), 1) if wind_dirs else None
    q_wd = round(_quartile_deviation(wind_dirs), 1) if wind_dirs else None

    return {
        "avg_temperature": at,
        "q_temperature": qt,
        "avg_humidity": ah,
        "q_humidity": qh,
        "avg_pressure": ap,
        "q_pressure": qp,
        "avg_wind_speed": aws,
        "q_wind_speed": qws,
        "avg_precipitation": ar,
        "q_precipitation": qr,
        "avg_wind_direction": avg_wd,
        "q_wind_direction": q_wd,
        "weather": stations[0].get("WeatherElement", {}).get("Weather"),
    }


# ─── 主功能 ──────────────────────────────────────────────────────


def get_nearby_observations(gps_input: Union[str, tuple, list], n: int = 3) -> dict:
    """
    給定 GPS 座標，找出最近 n 個測站並回傳平均觀測資料。

    若最近測站距離 < 3km，則直接以該站資料為準（不強制湊 n 站）。
    """
    result: dict = {
        "source": "中央氣象署即時觀測",
        "gps_input": gps_input,
        "gps_parsed": None,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": None,
        "stations_used": [],
        "avg_temperature": None,
        "q_temperature": None,
        "avg_humidity": None,
        "q_humidity": None,
        "avg_pressure": None,
        "q_pressure": None,
        "avg_wind_speed": None,
        "q_wind_speed": None,
        "avg_wind_direction": None,
        "q_wind_direction": None,
        "avg_precipitation": None,
        "q_precipitation": None,
        "weather": None,
        "error": None,
    }

    # 1. 解析 GPS
    coords = parse_coordinate(gps_input)
    if coords is None:
        result["error"] = f"無法解析 GPS 座標: {gps_input}"
        return result
    target_lat, target_lon = coords
    result["gps_parsed"] = coords

    # 2. 取得所有測站
    stations = fetch_all_stations()
    if not stations:
        result["error"] = "無法取得測站觀測資料"
        return result

    # 3. 算距離並排序
    scored: list[dict] = []
    for s in stations:
        wgs84 = _get_wgs84(s)
        if wgs84 is None:
            continue
        scored.append(
            {
                "station": s,
                "distance_km": haversine(target_lat, target_lon, wgs84[0], wgs84[1]),
                "wgs84": wgs84,
            }
        )
    scored.sort(key=lambda x: x["distance_km"])

    if not scored:
        result["error"] = "沒有可用的測站"
        return result

    # 4. 3km 閾值判斷
    closest = scored[0]
    if closest["distance_km"] < NEARBY_THRESHOLD_KM:
        selected = [closest]
        result["mode"] = "single_station"
    else:
        selected = scored[:n]
        result["mode"] = "averaged"

    # 5. 記錄測站資訊
    for item in selected:
        s = item["station"]
        geo = s.get("GeoInfo", {})
        result["stations_used"].append(
            {
                "id": s.get("StationId"),
                "name": s.get("StationName"),
                "county": geo.get("CountyName"),
                "town": geo.get("TownName"),
                "distance_km": round(item["distance_km"], 2),
                "lat": item["wgs84"][0],
                "lon": item["wgs84"][1],
            }
        )

    # 6. 平均
    averaged = _average_obs([item["station"] for item in selected])
    result.update(averaged)

    return result


# ─── 輸出 ────────────────────────────────────────────────────────


_DIRECTION_LABELS = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]


def print_nearby_weather(result: dict) -> None:
    """格式化輸出附近測站天氣資訊。"""
    print(f"\n{'=' * 55}")
    print(f"天氣觀測 — {result.get('source', '')}")
    print(f"{'=' * 55}")

    if result.get("error"):
        print(f"錯誤: {result['error']}")
        return

    lat, lon = result["gps_parsed"]
    print(f"位置: {lat:.6f}, {lon:.6f}")
    print(f"時間: {result.get('time', '')}")

    if result["mode"] == "single_station":
        print("模式: 單站（目標 3km 內有測站）")
    else:
        print(f"模式: {len(result['stations_used'])} 站平均")

    print()
    print(f"{'─' * 55}")
    for st in result.get("stations_used", []):
        print(f"  {st['name']} ({st['id']}) — {st['county']}{st['town']}  │ {st['distance_km']}km")
    print(f"{'─' * 55}")

    def fmt_avgq(avg_key, q_key, label, unit):
        avg = result.get(avg_key)
        q = result.get(q_key)
        if avg is not None:
            if q is not None and q > 0:
                print(f"{label}: {avg} ± {q}{unit}")
            else:
                print(f"{label}: {avg}{unit}")

    fmt_avgq("avg_temperature", "q_temperature", "溫度", "°C")
    fmt_avgq("avg_humidity", "q_humidity", "濕度", "%")
    fmt_avgq("avg_pressure", "q_pressure", "氣壓", "hPa")
    fmt_avgq("avg_wind_speed", "q_wind_speed", "風速", "m/s")

    wdir = result.get("avg_wind_direction")
    if wdir is not None:
        q_wdir = result.get("q_wind_direction")
        idx = round(wdir / 45) % 8
        if q_wdir and q_wdir > 0:
            print(f"風向: {wdir} ± {q_wdir}° ({_DIRECTION_LABELS[idx]})")
        else:
            print(f"風向: {wdir}° ({_DIRECTION_LABELS[idx]})")

    fmt_avgq("avg_precipitation", "q_precipitation", "雨量", "mm")

    weather = result.get("weather")
    if weather:
        print(f"天氣: {weather}")

    print()


# ─── CLI ─────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法: uv run weather_gps.py \"<GPS 座標>\" [測站數]")
        print()
        print("範例:")
        print('  uv run weather_gps.py "24.992301, 121.417556"')
        print('  uv run weather_gps.py "24.992301, 121.417556" 5')
        print('  uv run weather_gps.py "24°59\'32.1\\"N 121°25\'03.4\\"E"')
        return

    gps_input = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    result = get_nearby_observations(gps_input, n=n)
    print_nearby_weather(result)


if __name__ == "__main__":
    main()
