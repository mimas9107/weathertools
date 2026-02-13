#!/usr/bin/env python3
"""
監視器天氣分析工具 - 使用 Ollama Vision Model
"""

import ollama
import base64
from pathlib import Path

CAMERA_IMAGES = {
    "cam1_yangmingshu.png": "陽明書屋遠眺台北盆地",
    "cam2_hehuan.png": "合歡山武嶺亭",
    "cam3_eryanping.png": "二延平步道",
    "cam4_tai64.png": "台64線",
    "cam5_alishan_sunrise.png": "阿里山小笠原山觀景台",
}

PROMPT = """這是一張台灣風景監視器的截圖。請分析圖片中的天氣狀況。

請用以下格式回覆：
1. 天氣狀況：[晴天/多雲/陰天/雨天/霧氣]
2. 能見度：[好/普通/差]
3. 光線狀況：[明亮/柔和/昏暗]
4. 簡短描述看到的景色

注意：
- 台灣山區經常有雲霧繚繞
- 晴天時天空應該是明亮的藍色
- 陰天時畫面會比較灰暗
- 傍晚時光線會比較黃暗
"""


def encode_image(image_path: str) -> str:
    """將圖片轉為 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_weather(image_path: str, model: str = "minicpm-v:latest") -> dict:
    """使用 Ollama Vision Model 分析天氣"""
    result = {
        "file": image_path,
        "weather": None,
        "visibility": None,
        "light": None,
        "description": None,
        "raw_response": None,
    }

    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [encode_image(image_path)],
                }
            ],
            options={
                "temperature": 0.1,  # 低溫度以獲得穩定回答
            },
        )

        result["raw_response"] = response["message"]["content"]
        text = response["message"]["content"]

        # 解析回應
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("1. 天氣狀況：") or line.startswith("天氣狀況："):
                result["weather"] = line.split("：")[1].strip()
            elif line.startswith("2. 能見度：") or line.startswith("能見度："):
                result["visibility"] = line.split("：")[1].strip()
            elif line.startswith("3. 光線狀況：") or line.startswith("光線狀況："):
                result["light"] = line.split("：")[1].strip()
            elif line.startswith("4. 簡短描述") or "簡短描述" in line:
                result["description"] = (
                    line.split("：")[1].strip()
                    if "：" in line
                    else line.replace("4. 簡短描述看到的景色：", "").strip()
                )

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    """主程式"""
    print("=" * 60)
    print("監視器天氣分析工具 - Ollama Vision Model")
    print("=" * 60)

    # 檢查可用模型
    models = ollama.list()
    vision_models = [
        m["model"]
        for m in models["models"]
        if "vision" in m["model"].lower()
        or "llava" in m["model"].lower()
        or "minicpm" in m["model"].lower()
    ]

    if not vision_models:
        print("警告：未找到視覺模型！")
        print("請先安裝視覺模型，例如：")
        print("  ollama pull minicpm-v:latest")
        print("  ollama pull llama3.2-vision")
        print("  ollama pull bakllava")
        return

    print(f"找到視覺模型: {vision_models}")
    model = vision_models[0]
    print(f"使用模型: {model}")
    print()

    # 分析每個監視器
    for filename, name in CAMERA_IMAGES.items():
        image_path = f"/home/mimas/projects/esp-miao/{filename}"

        if not Path(image_path).exists():
            print(f"⚠️  {name}: 檔案不存在")
            print()
            continue

        print(f"📷 分析中: {name}")

        result = analyze_weather(image_path, model)

        if "error" in result:
            print(f"  ❌ 錯誤: {result['error']}")
        else:
            print(f"  天氣: {result['weather']}")
            print(f"  能見度: {result['visibility']}")
            print(f"  光線: {result['light']}")
            print(f"  描述: {result['description']}")
            print(f"  (原始回應: {result['raw_response'][:100]}...)")

        print()


if __name__ == "__main__":
    main()
