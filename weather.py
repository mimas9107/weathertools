#!/usr/bin/env python3
"""
中央氣象署天氣資料抓取工具
"""

import os
import requests
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

CWB_API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

load_dotenv()


def get_cwb_api_key() -> str:
    """取得 CWB API Key"""
    return os.getenv("CWB_API_KEY", "your-cwb-api-key")


def get_weather_data(location_name: Optional[str] = None) -> dict:
    """
    取得中央氣象署天氣資料

    Args:
        location_name: 縣市名稱，如 "臺北市"、"新北市" 等

    Returns:
        dict: 包含天氣、温度、濕度等資訊
    """
    auth_key = get_cwb_api_key()

    result = {
        "source": "中央氣象署",
        "location": location_name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "weather": None,
        "temperature": None,
        "humidity": None,
        "rainfall": None,
        "wind_speed": None,
        "description": None,
        "raw": None,
    }

    try:
        params = {
            "Authorization": auth_key,
            "elementName": "Weather,Temperature,RelativeHumidity,WindSpeed,Precipitation",
        }

        if location_name:
            params["locationName"] = location_name

        response = requests.get(f"{CWB_API_URL}/F-C0032-001", params=params, timeout=10)
        response.raise_for_status()
        result["raw"] = response.json()

    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP 錯誤: {e}"
    except requests.exceptions.Timeout:
        result["error"] = "連線逾時"
    except requests.exceptions.RequestException as e:
        result["error"] = f"連線錯誤: {e}"

    return result


def get_current_observation(station_id: Optional[str] = None) -> dict:
    """
    取得中央氣象署即時觀測資料

    Args:
        station_id: 測站代碼，如 "466900" (臺北)、"467050" (高雄)

    Returns:
        dict: 包含各項觀測資料
    """
    auth_key = get_cwb_api_key()

    result = {
        "source": "中央氣象署即時觀測",
        "station": station_id,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "temperature": None,
        "humidity": None,
        "pressure": None,
        "wind_direction": None,
        "wind_speed": None,
        "rainfall": None,
        "visibility": None,
        "weather": None,
        "raw": None,
    }

    try:
        params = {
            "Authorization": auth_key,
            "dataid": "O-A0001-001",
            "elementName": "TEMP,HUMD,PRES,WDSE,WIND,RAIN,VISIBILITY,Weather",
        }

        if station_id:
            params["stationId"] = station_id

        response = requests.get(
            f"{CWB_API_URL}/{params['dataid']}", params=params, timeout=10
        )
        response.raise_for_status()
        result["raw"] = response.json()

    except Exception as e:
        result["error"] = str(e)

    return result


def get_uvi_data(location_name: Optional[str] = None) -> dict:
    """
    取得中央氣象署紫外線指數

    Args:
        location_name: 縣市名稱

    Returns:
        dict: 紫外線指數資訊
    """
    auth_key = get_cwb_api_key()

    result = {
        "source": "中央氣象署 UV",
        "location": location_name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "uvi": None,
        "level": None,
        "description": None,
    }

    try:
        params = {"Authorization": auth_key, "elementName": "UVI"}

        if location_name:
            params["locationName"] = location_name

        response = requests.get(f"{CWB_API_URL}/F-A0011-001", params=params, timeout=10)
        response.raise_for_status()
        result["raw"] = response.json()

    except Exception as e:
        result["error"] = str(e)

    return result


def parse_weather_code(wx: str) -> str:
    """
    解析天氣現象代碼為文字

    CWB 天氣代碼對照:
    - 01: 晴天
    - 02: 多雲
    - 03: 陰天
    - 04: 陰時多雲
    - 05: 多雲時陰
    - 06: 多雲短暫雨
    - 07: 陰短暫雨
    - 08: 雨天
    - 09: 雷雨
    - 10: 霧
    - ...
    """
    weather_codes = {
        "01": "晴天",
        "02": "多雲",
        "03": "陰天",
        "04": "陰時多雲",
        "05": "多雲時陰",
        "06": "多雲短暫雨",
        "07": "陰短暫雨",
        "08": "雨天",
        "09": "雷陣雨",
        "10": "霧",
        "11": "有霧",
        "12": "晴時多雲",
        "13": "其他",
    }
    return weather_codes.get(wx.zfill(2), f"未知({wx})")


def get_uv_level(uvi: float) -> tuple:
    """
    根據 UV 指數回傳等級和建議

    Returns:
        tuple: (等級名稱, 建議)
    """
    if uvi <= 2:
        return ("低", "可安心戶外活動")
    elif uvi <= 5:
        return ("中", "外出請防曬")
    elif uvi <= 7:
        return ("高", "減少戶外活動")
    elif uvi <= 10:
        return ("甚高", "戶外活動需特別防護")
    else:
        return ("極高", "避免戶外活動")


def print_weather(result: dict) -> None:
    """格式化輸出天氣資訊"""
    print(f"\n{'=' * 50}")
    print(f"🌤 天氣資訊 - {result.get('source', '未知來源')}")
    print(f"{'=' * 50}")

    if "error" in result:
        print(f"❌ 錯誤: {result['error']}")
        print("💡 提示: 請至 https://opendata.cwa.gov.tw 申請 API Key")
        return

    print(f"📍 地點: {result.get('location', '未指定')}")
    print(f"🕐 更新時間: {result.get('time', '未知')}")

    weather = result.get("weather")
    if weather:
        print(f"🌤️ 天氣狀況: {weather}")

    temp = result.get("temperature")
    if temp:
        print(f"🌡️ 温度: {temp}°C")

    humidity = result.get("humidity")
    if humidity:
        print(f"💧 濕度: {humidity}%")

    rainfall = result.get("rainfall")
    if rainfall is not None:
        print(f"🌧️ 雨量: {rainfall}mm")

    wind = result.get("wind_speed")
    if wind is not None:
        print(f"💨 風速: {wind}m/s")

    print()


def main():
    """測試"""
    print("中央氣象署天氣工具")
    print("=" * 40)

    data = get_weather_data()
    print_weather(data)


if __name__ == "__main__":
    main()
