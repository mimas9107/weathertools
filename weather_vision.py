#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
監視器畫面天氣分析工具 - 使用 Ollama Vision Model

重構後的版本，能處理 MJPEG、YouTube 和 HLS 串流。
"""

import os
import requests
import ollama
import base64
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any
from playwright.async_api import async_playwright, Playwright, Browser
from dotenv import load_dotenv

load_dotenv()

# --- 常數設定 ---

CONFIG_API_URL = os.environ.get("VIEWPOINTS_API_URL", "https://viewpoints-4dzi.onrender.com")
DEFAULT_SCREENSHOT_DIR = Path("screenshots")
DEFAULT_OLLAMA_MODEL = "llava:latest"
CAMERA_MAPPING: Dict[str, Dict[str, Any]] = {}

# --- 認證與 Token 管理 ---
_auth_token: Optional[str] = None


def login_and_get_token() -> Optional[str]:
    """使用帳號密碼登入並取得 JWT Token"""
    global _auth_token
    username = os.environ.get("VIEWPOINTS_USERNAME")
    password = os.environ.get("VIEWPOINTS_PASSWORD")

    if not username or not password:
        print("⚠️ 請設定 VIEWPOINTS_USERNAME 和 VIEWPOINTS_PASSWORD 環境變數。")
        return None

    try:
        print(f"🔄 正在登入至 {CONFIG_API_URL}...")
        response = requests.post(
            f"{CONFIG_API_URL}/api/auth/login",
            data={"username": username, "password": password},
            timeout=10
        )
        response.raise_for_status()
        token_data = response.json()
        _auth_token = token_data.get("access_token")
        if _auth_token:
            print("✅ 登入成功，已取得 Token。")
            return _auth_token
        else:
            print(f"❌ 登入失敗: {token_data.get('detail', '未知錯誤')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 登入請求失敗: {e}")
        return None

VISION_PROMPT = """
你是一個專業的台灣天氣觀測員，你的任務是分析風景監視器的即時畫面。
請根據圖片內容，僅用 JSON 格式回覆以下天氣資訊，不要包含任何其他文字或說明。
你的回覆必須是一個完整的 JSON 物件，格式如下：
{
  "weather": "天氣狀況 (晴天/多雲/陰天/雨天/起霧)",
  "visibility": "能見度 (良好/普通/差)",
  "light": "光線 (明亮/柔和/昏暗)",
  "sky": "天空狀況 (藍天/灰濛/多雲/陰暗)",
  "description": "用繁體中文簡要描述畫面中的天氣與景色，約 20-40 字"
}
"""

# --- 組態與連線檢查 ---

def get_camera_config() -> bool:
    """從 API 獲取可用的監視器設定，過濾出可處理的類型。"""
    global CAMERA_MAPPING
    CAMERA_MAPPING.clear()
    try:
        print(f"🔄 正在從 {CONFIG_API_URL}/api/config 獲取最新的監視器列表...")
        headers = {}
        if _auth_token:
            headers["Authorization"] = f"Bearer {_auth_token}"
        response = requests.get(f"{CONFIG_API_URL}/api/config", headers=headers, timeout=15)
        response.raise_for_status()
        config_data = response.json()
        
        for cam in config_data.get("cameras", []):
            cam_id = cam.get("id")
            if not cam_id:
                continue

            cam_type = cam.get("type")
            
            if cam_type == "image" and cam.get("imageUrl"):
                CAMERA_MAPPING[cam_id] = {
                    "name": cam.get("name", "未命名"),
                    "type": "image",
                    "url": cam["imageUrl"],
                }
            elif cam_type in ["youtube", "hls"] and cam.get("url"):
                CAMERA_MAPPING[cam_id] = {
                    "name": cam.get("name", "未命名"),
                    "type": cam_type,
                    "url": cam["url"], # 這是播放頁面的 URL
                }
        
        if not CAMERA_MAPPING:
            print("⚠️ 未能從 API 獲取任何可用的監視器。 সন")
            return False
            
        print(f"✅ 成功獲取 {len(CAMERA_MAPPING)} 個可分析的監視器設定。 সন")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ 無法獲取監視器設定: {e}")
        return False
    except json.JSONDecodeError:
        print("❌ 解析監視器設定失敗，收到的不是有效的 JSON 格式。 সন")
        return False

def check_ollama_connection() -> bool:
    """檢查與 Ollama 服務的連線狀態。"""
    try:
        ollama.list()
        print("✅ Ollama 服務連線成功。 সন")
        return True
    except Exception:
        print("❌ 無法連線到 Ollama 服務。請確認 `ollama serve` 正在本機運行。 সন")
        return False

# --- 圖片擷取核心邏輯 ---

async def _screenshot_video_with_playwright(browser: Browser, page_url: str, output_path: Path) -> bool:
    """使用 Playwright 對影片串流頁面進行截圖。"""
    page = None
    context = None
    try:
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()
        print(f"   ... (Playwright) 正在導航至: {page_url}")
        
        await page.goto(page_url, timeout=45000, wait_until="domcontentloaded")

        video_selectors = [".player-container", "video", "iframe", "body > div"]
        video_element = None
        
        for sel in video_selectors:
            try:
                print(f"   ... (Playwright) 嘗試選擇器: {sel}")
                video_element = await page.wait_for_selector(sel, timeout=5000)
                if video_element:
                    break
            except Exception:
                continue

        if not video_element:
            print(f"   ⚠️ 找不到特定播放器元素，將截取整個頁面。")

        print("   ... (Playwright) 等待畫面渲染...")
        await asyncio.sleep(5)

        if video_element:
            await video_element.screenshot(path=str(output_path))
        else:
            await page.screenshot(path=str(output_path), full_page=True)
        
        print(f"   ✅ (Playwright 截圖) 已儲存至: {output_path}")
        return True

    except Exception as e:
        print(f"   ❌ (Playwright) 截圖時發生錯誤: {e}")
        return False
    finally:
        if page:
            await page.close()
        if context:
            await context.close()

def _download_mjpeg_frame(image_url: str, output_path: Path) -> bool:
    """從 MJPEG 串流中擷取並儲存單一畫面。"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(image_url, timeout=20, stream=True, headers=headers)
        response.raise_for_status()

        content_type = response.headers.get('content-type', '')

        if 'multipart/x-mixed-replace' in content_type:
            print("   ... (MJPEG 串流) 正在擷取畫面...")
            jpeg_data = b''
            for chunk in response.iter_content(chunk_size=1024):
                jpeg_data += chunk
                start = jpeg_data.find(b'\xff\xd8')
                end = jpeg_data.find(b'\xff\xd9')
                if start != -1 and end != -1 and end > start:
                    img_frame = jpeg_data[start:end+2]
                    with output_path.open("wb") as f:
                        f.write(img_frame)
                    print(f"   ✅ (MJPEG 畫面) 已儲存至: {output_path}")
                    return True
            print("   ❌ 無法從 MJPEG 串流中擷取到有效的畫面。 সন")
            return False
        elif 'image/' in content_type:
             with output_path.open("wb") as f:
                f.write(response.content)
             print(f"   ✅ (靜態圖片) 已儲存至: {output_path}")
             return True
        else:
            print(f"   ❌ 下載失敗: 不支援的內容類型 '{content_type}'。 সন")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   ❌ 下載失敗: {e}")
        return False

async def get_camera_image(browser: Optional[Browser], camera_id: str, output_dir: Path) -> Optional[Path]:
    """根據攝影機類型，分派給合適的函式來擷取影像。"""
    if camera_id not in CAMERA_MAPPING:
        print(f"⚠️ 未知的監視器 ID: {camera_id}")
        return None

    camera = CAMERA_MAPPING[camera_id]
    camera_type = camera["type"]
    url = camera["url"]
    name = camera["name"]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{camera_id}_{timestamp}.png" # Playwright 預設存為 png

    print(f"📥 開始處理: {name} ({camera_id}) - 類型: {camera_type}")
    
    success = False
    if camera_type == "image":
        success = _download_mjpeg_frame(url, output_path)
    elif camera_type in ["youtube", "hls"]:
        if not browser:
            print("   ❌ 錯誤: 未提供 Playwright 瀏覽器實例，無法截圖。 সন")
            return None
        success = await _screenshot_video_with_playwright(browser, url, output_path)

    return output_path if success else None


# --- 分析與結果展示 ---

def analyze_image_weather(image_path: Path, model: str = DEFAULT_OLLAMA_MODEL) -> Dict[str, Any]:
    """使用 Ollama 分析單張圖片的天氣。 (此函式保持不變) """
    # ... (Omit unchanged function body for brevity)
    analysis_result: Dict[str, Any] = {
        "file": str(image_path), "timestamp": datetime.now().isoformat(), "model": model, "success": False,
    }
    if not image_path.exists():
        analysis_result["error"] = f"檔案不存在: {image_path}"; return analysis_result
    try:
        print(f"🧠 正在使用 {model} 分析圖片: {image_path.name}...")
        with image_path.open("rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": VISION_PROMPT, "images": [image_base64]}],
            options={"temperature": 0.1},
        )
        raw_response = response["message"]["content"]
        analysis_result["raw_response"] = raw_response
        json_str = raw_response[raw_response.find("{") : raw_response.rfind("}") + 1]
        if json_str:
            parsed_data = json.loads(json_str); analysis_result.update(parsed_data); analysis_result["success"] = True
            print("   ✅ 分析成功。 সন")
        else:
            analysis_result["error"] = "無法從模型回應中解析出有效的 JSON。 সন"
            print("   ⚠️ 解析失敗...")
    except Exception as e:
        analysis_result["error"] = f"分析時發生錯誤: {e}"; print(f"   ❌ 分析時發生錯誤: {e}")
    return analysis_result


def print_analysis_result(result: Dict[str, Any]) -> None:
    """格式化印出單次分析結果。 (此函式保持不變) """
    # ... (Omit unchanged function body for brevity)
    print("-" * 60)
    camera_id = result.get("camera_id", "N/A")
    camera_info = CAMERA_MAPPING.get(camera_id, {})
    camera_name = camera_info.get("name", "未知相機")
    print(f"📍 監視器: {camera_name} ({camera_id})"); print(f"📄 檔案: {result.get('file', 'N/A')}")
    if result.get("success"):
        print(f"☀️ 天氣: {result.get('weather', 'N/A')}"); print(f"👁️ 能見度: {result.get('visibility', 'N/A')}")
        print(f"💡 光線: {result.get('light', 'N/A')}"); print(f"☁️ 天空: {result.get('sky', 'N/A')}")
        print(f"📝 描述: {result.get('description', 'N/A')}")
    else:
        print(f"❌ 錯誤: {result.get('error', '未知錯誤')}")
    print("-" * 60)

def summarize_and_print_results(results: List[Dict[str, Any]]) -> None:
    """統計並印出摘要。 (此函式保持不變)"""
    # ... (Omit unchanged function body for brevity)
    if not results: print("沒有可供摘要的結果。 সন"); return
    success_count = sum(1 for r in results if r.get("success")); fail_count = len(results) - success_count
    print("\n" + "=" * 60); print("📊 分析結果摘要"); print("=" * 60)
    print(f"總分析數量: {len(results)}"); print(f"✅ 成功: {success_count}"); print(f"❌ 失敗: {fail_count}")
    if success_count > 0:
        weather_counts: Dict[str, int] = {}
        for r in results:
            if r.get("success") and r.get("weather"):
                weather = r["weather"]; weather_counts[weather] = weather_counts.get(weather, 0) + 1
        if weather_counts:
            print("\n天氣狀況分佈:")
            for weather, count in sorted(weather_counts.items(), key=lambda item: -item[1]):
                print(f"  - {weather}: {count} 次")
    print("=" * 60)

# --- 主執行流程 (非同步) ---

async def main_async():
    """非同步主程式，管理 Playwright 瀏覽器實例。"""
    print("=" * 60); print("🏞️  天氣視覺分析工具 (Ollama)"); print("=" * 60)

    # 執行登入以取得 Token
    if not login_and_get_token():
        print("\n⚠️ 登入失敗，將嘗試以匿名身份存取 API...")

    if not get_camera_config() or not check_ollama_connection():
        print("\n無法繼續執行，請檢查錯誤訊息。 সন"); return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        print("✅ Playwright 瀏覽器實例已啟動。 সন")

        try:
            while True:
                print("\n請選擇操作模式:")
                print("  1. 分析特定監視器畫面")
                print("  2. 分析所有監視器畫面")
                print("  q. 退出")
                choice = input("\n請輸入選項 [1, 2, q]: ").strip().lower()

                if choice == "1":
                    print("\n可用的監視器:")
                    for cam_id, info in CAMERA_MAPPING.items(): print(f"  - {cam_id} ({info['type']}): {info['name']}")
                    camera_id = input("請輸入要分析的監視器 ID: ").strip()
                    if camera_id in CAMERA_MAPPING:
                        image_path = await get_camera_image(browser, camera_id, DEFAULT_SCREENSHOT_DIR)
                        if image_path:
                            result = analyze_image_weather(image_path); result["camera_id"] = camera_id
                            print_analysis_result(result)
                    else: print("錯誤: 無效的監視器 ID。 সন")
                
                elif choice == "2":
                    all_results = []
                    for cam_id in CAMERA_MAPPING.keys():
                        image_path = await get_camera_image(browser, cam_id, DEFAULT_SCREENSHOT_DIR)
                        if image_path:
                            result = analyze_image_weather(image_path); result["camera_id"] = cam_id
                            all_results.append(result)
                            print_analysis_result(result)
                    summarize_and_print_results(all_results)

                elif choice == "q":
                    print("👋 程式結束。 সন"); break
                else: print("無效的選項，請重新輸入。 সন")
        finally:
            await browser.close()
            print("✅ Playwright 瀏覽器實例已關閉。 সন")

if __name__ == "__main__":
    # 因為 Playwright 使用 asyncio，所以我們用 asyncio.run 來啟動主程式
    # 注意：Windows 上可能會出現 Proactor event loop is required... 的錯誤
    # 如果遇到，可以考慮安裝 `nest_asyncio` 並在頂部 `nest_asyncio.apply()`
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n程式被使用者中斷。 সন")
