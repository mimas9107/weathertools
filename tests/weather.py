#!/usr/bin/env python3
"""
中央氣象署天氣資料抓取工具
"""

import requests
from datetime import datetime

CWB_API_URL = "https://opendata.cwb.gov.tw/api/v1/rest/datastore"


def get_weather_data(location_name: str = None) -> dict:
    """
    取得中央氣象署天氣資料
    """
    auth_key = "your-cwb-api-key"  # 需要申請

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
            "elementName": "Weather,PoP12h,Temperature,RelativeHumidity,WindSpeed,Precipitation",
        }

        if location_name:
            params["locationName"] = location_name

        response = requests.get(f"{CWB_API_URL}/F-C0032-001", params=params, timeout=10)
        response.raise_for_status()
        result["raw"] = response.json()

    except Exception as e:
        result["error"] = str(e)

    return result


def get_uvi_data(location_name: str = None) -> dict:
    """
    取得中央氣象署紫外線指數
    """
    result = {
        "source": "中央氣象署 UV",
        "location": location_name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "uvi": None,
        "level": None,
        "description": None,
    }

    try:
        auth_key = "your-cwb-api-key"
        params = {"Authorization": auth_key, "parameterName": "UVI"}

        if location_name:
            params["locationName"] = location_name

        response = requests.get(f"{CWB_API_URL}/F-A0011-001", params=params, timeout=10)
        response.raise_for_status()
        result["raw"] = response.json()

    except Exception as e:
        result["error"] = str(e)

    return result


def get_forecast(location_name: str = None, days: int = 3) -> dict:
    """
    取得天氣預報
    """
    result = {"source": "中央氣象署預報", "location": location, "forecast": []}

    return result


def parse_weather_condition(wx: str) -> str:
    """
    解析天氣現象代碼為文字
    """
    weather_codes = {
        "01": "晴天",
        "02": "多雲",
        "03": "陰天",
        "04": "雨天",
        "05": "雷雨",
        "06": "霧",
        "07": "雪",
        "08": "其他",
    }
    return weather_codes.get(wx[:2], "未知")


def main():
    """測試"""
    print("中央氣象署天氣工具")
    print("=" * 40)

    data = get_weather_data()
    print(f"資料來源: {data['source']}")
    print(f"取得時間: {data['time']}")

    if "error" in data:
        print(f"錯誤: {data['error']}")
    else:
        print("成功取得資料（需填入 API Key）")


if __name__ == "__main__":
    main()
