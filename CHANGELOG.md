# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-04-20

### Added
- JWT 登入認證機制，整合 viewpoints API
- Playwright 多重備用選擇器截圖邏輯
- `.env.example` 環境變數範本檔案

### Changed
- `weather_vision.py` 支援 YouTube/HLS 串流截圖
- 更新專案文件為繁體中文

### Fixed
- 修正 Playwright `jpeg_quality` 參數錯誤
- 改善 YouTube 串流截圖穩定性

## [0.1.0] - 2025-02-04

### Added
- `weather.py` - 中央氣象署天氣資料抓取工具
- `weather_vision.py` - 監視器畫面天氣分析工具 (Ollama Vision)
- 初始專案結構