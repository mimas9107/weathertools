#!/usr/bin/env python3
"""
TDX 交通資料平台 — CCTV 監視器 GPS 查詢與天氣整合工具

使用 TDX (Transport Data eXchange) API 查詢台灣交通監視器座標，
並結合 weather_gps.py 取得最近測站天氣觀測資料。
"""

import os
import sys
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from weather_gps import get_nearby_observations, haversine, print_nearby_weather

TDX_API_URL = "https://tdx.transportdata.tw/api/basic/v2"
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"

load_dotenv()

# ─── Token 管理 ──────────────────────────────────────────────────

_token: Optional[str] = None
_token_expiry: float = 0


def _load_credentials() -> tuple[str, str]:
    return os.getenv("TDX_CLIENT_ID", ""), os.getenv("TDX_CLIENT_SECRET", "")


def get_tdx_token() -> Optional[str]:
    global _token, _token_expiry

    if _token and time.time() < _token_expiry:
        return _token

    client_id, client_secret = _load_credentials()
    if not client_id or not client_secret:
        return None

    try:
        resp = requests.post(
            TDX_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _token = data["access_token"]
        _token_expiry = time.time() + data.get("expires_in", 86400) - 60
        return _token
    except requests.exceptions.RequestException:
        return None


# ─── API 請求 ────────────────────────────────────────────────────


def _tdx_get(path: str, params: dict = None) -> Optional[dict]:
    token = get_tdx_token()
    if not token:
        return None
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        resp = requests.get(f"{TDX_API_URL}{path}", headers=headers, params=params, timeout=15)
        if resp.status_code == 429:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return None


# ─── CCTV 查詢 ───────────────────────────────────────────────────


# TDX API 僅支援 city 路徑，不支援全國無參數查詢
_ALL_CITIES = [
    "Taipei", "NewTaipei", "Taoyuan", "Taichung", "Tainan", "Kaohsiung",
    "Hsinchu", "HsinchuCounty", "MiaoliCounty", "ChanghuaCounty",
    "NantouCounty", "YunlinCounty", "Chiayi", "ChiayiCounty",
    "PingtungCounty", "YilanCounty", "HualienCounty", "TaitungCounty",
    "PenghuCounty", "Keelung",
]

_city_cache: dict[str, list[dict]] = {}


def _city_from_id(cctv_id: str) -> Optional[str]:
    """從 CCTVID 首碼推測所屬縣市。"""
    if "-" in cctv_id:
        parts = cctv_id.split("-")
        prefix = parts[0] if len(parts) > 1 and len(parts[0]) > 1 else cctv_id[:1]
    else:
        prefix = cctv_id[:1]
    table = {
        "T": "Taipei", "NT": "NewTaipei", "TY": "Taoyuan",
        "TCG": "Taichung", "TN": "Tainan", "KS": "Kaohsiung",
        "HC": "Hsinchu", "ML": "MiaoliCounty",
        "CH": "ChanghuaCounty", "YL": "YunlinCounty",
        "CY": "Chiayi", "IL": "YilanCounty",
        "HL": "HualienCounty", "TT": "TaitungCounty",
        "PH": "PenghuCounty", "KL": "Keelung",
    }
    return table.get(prefix)


def _fetch_city_cctvs(city: str, top: int = 300) -> list[dict]:
    """查詢單一縣市監視器（含快取）。"""
    cache_key = f"{city}:{top}"
    if cache_key in _city_cache:
        return _city_cache[cache_key]
    params = {"$top": top, "$format": "JSON"}
    data = _tdx_get(f"/Road/Traffic/CCTV/City/{city}", params)
    cctvs = data.get("CCTVs", []) if data else []
    if cctvs:
        _city_cache[cache_key] = cctvs
    return cctvs


def query_cctv_by_city(city: str, top: int = 300) -> list[dict]:
    return _fetch_city_cctvs(city, top=top)


def _fetch_all_cctvs(top_per_city: int = 200) -> list[dict]:
    """逐一查詢所有縣市，彙整全國監視器。"""
    all_cams = []
    for city in _ALL_CITIES:
        cams = _fetch_city_cctvs(city, top=top_per_city)
        all_cams.extend(cams)
    return all_cams


def query_cctv_by_id(cctv_id: str, city: str = None) -> Optional[dict]:
    """依 CCTVID 查詢單一監視器 GPS。

    優先使用精準端點 City/{city}/{id}，避免大量搜尋與 rate limit；
    退路為依 ID 首碼推測縣市後搜尋全部，或逐一掃描所有縣市。
    """
    candidates = [city] if city else []
    if not candidates:
        guessed = _city_from_id(cctv_id)
        if guessed:
            candidates.append(guessed)

    for c in candidates:
        data = _tdx_get(f"/Road/Traffic/CCTV/City/{c}/{cctv_id}")
        if data:
            cctvs = data.get("CCTVs", [])
            if cctvs:
                return cctvs[0]

    # 退路：逐一搜尋所有縣市（無推測時）
    if not candidates:
        candidates = _ALL_CITIES
    for c in candidates:
        cams = _fetch_city_cctvs(c, top=300)
        for cam in cams:
            if cam.get("CCTVID") == cctv_id:
                return cam
    return None


def query_cctv_by_road(road_keyword: str, city: str = None, top: int = 30) -> list[dict]:
    """依路名關鍵字查詢監視器。"""
    if city:
        cctvs = _fetch_city_cctvs(city, top=500)
    else:
        cctvs = _fetch_all_cctvs()
    matched = [c for c in cctvs if road_keyword in c.get("RoadName", "")]
    return matched[:top]


def query_cctv_nearby(
    lat: float, lon: float, radius_km: float = 1.0, city: str = None, top: int = 20
) -> list[dict]:
    """查詢指定座標附近 radius_km 範圍內的監視器。"""
    if city:
        cctvs = _fetch_city_cctvs(city, top=500)
    else:
        cctvs = _fetch_all_cctvs()

    nearby = []
    for c in cctvs:
        clat = c.get("PositionLat")
        clon = c.get("PositionLon")
        if clat is None or clon is None:
            continue
        dist = haversine(lat, lon, clat, clon)
        if dist <= radius_km:
            c["_distance_km"] = round(dist, 3)
            nearby.append(c)

    nearby.sort(key=lambda x: x["_distance_km"])
    return nearby[:top]


# ─── 整合天氣 ────────────────────────────────────────────────────


def get_camera_weather(cctv_id: str, n_stations: int = 3) -> dict:
    """查詢監視器 GPS 並取得附近測站天氣。"""
    result: dict = {
        "cctv_id": cctv_id,
        "cctv_name": None,
        "cctv_road": None,
        "cctv_gps": None,
        "weather": None,
        "error": None,
    }

    camera = query_cctv_by_id(cctv_id)
    if not camera:
        result["error"] = f"找不到 CCTVID: {cctv_id}"
        return result

    lat = camera.get("PositionLat")
    lon = camera.get("PositionLon")
    if lat is None or lon is None:
        result["error"] = f"攝影機 {cctv_id} 無 GPS 資料"
        return result

    result["cctv_name"] = camera.get("RoadName", "")
    result["cctv_road"] = camera.get("RoadName", "")
    result["cctv_gps"] = (lat, lon)

    weather = get_nearby_observations((lat, lon), n=n_stations)
    result["weather"] = weather
    if weather.get("error"):
        result["error"] = weather["error"]

    return result


# ─── 輸出 ────────────────────────────────────────────────────────


def print_camera_info(camera: dict) -> None:
    print(f"  ID: {camera.get('CCTVID', '-')}")
    print(f"  道路: {camera.get('RoadName', '-')}")
    print(f"  座標: ({camera['PositionLat']:.6f}, {camera['PositionLon']:.6f})")
    if camera.get("_distance_km") is not None:
        print(f"  距離: {camera['_distance_km']}km")


def print_camera_weather(result: dict) -> None:
    print(f"\n{'=' * 55}")
    print(f"CCTV 天氣 — {result.get('cctv_id', '')}")
    print(f"{'=' * 55}")

    if result.get("error"):
        print(f"錯誤: {result['error']}")
        return

    print(f"位置: {result.get('cctv_road', '')}")
    lat, lon = result["cctv_gps"]
    print(f"座標: {lat:.6f}, {lon:.6f}")
    print()

    weather = result.get("weather")
    if weather:
        print_nearby_weather(weather)
    else:
        print("無法取得天氣資料")


# ─── CLI ─────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法: uv run weather_tdx.py <指令> [參數...]")
        print()
        print("指令:")
        print("  id <CCTVID>                 查詢單一監視器 GPS")
        print("  city <城市名> [筆數]         查詢縣市所有監視器")
        print("  road <路名> [城市]           依路名查詢監視器")
        print("  nearby <lat> <lon> [半徑km]  查詢附近監視器")
        print("  weather <CCTVID>            監視器 GPS + 附近天氣")
        print()
        print("範例:")
        print('  uv run weather_tdx.py id T000029')
        print('  uv run weather_tdx.py city Taipei 5')
        print('  uv run weather_tdx.py road 敦化南路')
        print('  uv run weather_tdx.py nearby 25.04497 121.54888 0.5')
        print('  uv run weather_tdx.py weather T000029')
        return

    cmd = sys.argv[1]

    if cmd == "id":
        if len(sys.argv) < 3:
            print("請指定 CCTVID")
            return
        cam = query_cctv_by_id(sys.argv[2])
        if cam:
            print_camera_info(cam)
        else:
            print("查無此監視器")

    elif cmd == "city":
        city = sys.argv[2] if len(sys.argv) > 2 else "Taipei"
        top = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        cctvs = query_cctv_by_city(city, top=top)
        print(f"\n{city} 監視器 ({len(cctvs)} 筆):")
        print(f"{'─' * 55}")
        for c in cctvs:
            print_camera_info(c)
            print()

    elif cmd == "road":
        road = sys.argv[2] if len(sys.argv) > 2 else ""
        city = sys.argv[3] if len(sys.argv) > 3 else None
        if not road:
            print("請指定路名")
            return
        cctvs = query_cctv_by_road(road, city=city)
        print(f"\n「{road}」監視器 ({len(cctvs)} 筆):")
        print(f"{'─' * 55}")
        for c in cctvs:
            print_camera_info(c)
            print()

    elif cmd == "nearby":
        if len(sys.argv) < 4:
            print("請指定緯度與經度")
            return
        lat, lon = float(sys.argv[2]), float(sys.argv[3])
        radius = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
        cctvs = query_cctv_nearby(lat, lon, radius)
        print(f"\n({lat:.6f}, {lon:.6f}) 附近 {radius}km 監視器 ({len(cctvs)} 筆):")
        print(f"{'─' * 55}")
        for c in cctvs:
            print_camera_info(c)
            print()

    elif cmd == "weather":
        if len(sys.argv) < 3:
            print("請指定 CCTVID")
            return
        result = get_camera_weather(sys.argv[2])
        print_camera_weather(result)

    else:
        print(f"未知指令: {cmd}")


if __name__ == "__main__":
    main()
