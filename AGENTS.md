---
name:          "AGENTS.md"
description:   "中央氣象署資料擷取與視覺分析指引"
created_date:  "2026/05/29 13:25:00"
modified_date: "2026/06/18 10:45:00"
project_version: "1.0.0"
document_version: "1.1.0"
agent_sign: ['human/mimas', 'gemini cli/gemini-cli']
---

# WeatherTools 氣象工具專案 (AGENTS.md)

本文件定義此專案的特化開發行為。Agent 必須同時遵循工作區全域規範 (../AGENTS.md)。

## 1. 專案特化規範
- **環境**: Python uv 管理。
- **工具**: 優先使用 ~/bin/todomgr 與 ~/bin/notes-cli 進行任務紀錄。
- **測試**: 參照 /docs/testing-standard.md，報告存放於 ./reports/。

---
*註：本文件專注於專案業務與技術細節，通用環境指令與 Token 節約準則請查閱全域規範。*
