# Project Environment & Tooling (Local Only)

## 1. Environment Constraints
- **Python**: Use `uv` for package management (strictly no system-wide installs).
- **JS/TS**: Use `nvm`, `npm`, or `npx`.
- **System**: Use `brew` for macOS dependencies.

## 2. Local Tooling Paths
- **Todo Manager**: `~/bin/todomgr` (Usage: `todomgr [add|list|done] "task"`)
- **Notes CLI**: `~/bin/notes-cli` (Usage: `notes-cli [save|find] "content"`)

## 3. Testing & Reporting
- **Pre-test**: Ensure all services are initialized.
- **Execution**: Refer to `/docs/testing-standard.md` for methodology.
- **Reports**: Save output to `./reports/TEST-[YYYYMMDD].md`.

## 4. Operational Alignment
- Follow `~/.config/agents/AGENTS.md` for all logic and reasoning standards.
- In case of conflict, this document defines *Tooling*, while root defines *Behavior*.
# AI Agent 動作限制規範

# Critical rules:
## 1. 檔案下載限制
- **禁止自動下載大檔案**
- 任何下載任務若檔案大小 > 50MB，必須提示使用者使用終端機手動下載
- 格式：
  ```
  ⚠️ 檔案大小超過 50MB，建議您手動下載：
  
  cd /target/path
  curl -O https://large-file.url
  # 或
  wget https://large-file.url
  
  完成後請通知我繼續後續步驟。
  ```

## 2. Ollama 模型操作限制
- **禁止未經同意的模型操作**
- 任何模型卸載/刪除必須先詢問使用者
- 格式：
  ```
  ⚠️ 您有 4 個大型模型載入記憶體中：
  - qwen3:8b-optimized (5.2GB)
  - qwen2.5-coder:7b (4.7GB)
  - qwen3:8b (5.2GB)
  - gemma3:4b (3.3GB)
  
  這些模型佔用大量記憶體。您希望：
  1. 繼續保留所有模型
  2. 從記憶體卸載特定模型（不刪除硬碟檔案）
  3. 從硬碟刪除特定模型
  
  請選擇選項或提供具體指令。
  ```

## 3. 記憶體使用檢查
- **下載前必須檢查可用記憶體**
- 任何下載或模型操作前檢查系統記憶體
- 格式：
  ```
  📊 系統記憶體狀況：
  - 總記憶體：15GB
  - 已使用：8.5GB
  - 可用：6.8GB
  - 使用率：57%
  
  您確定要下載/安裝此檔案/模型嗎？（建議確認記憶體足夠）
  ```

## 4. 阻塞操作限制
- **禁止阻塞對話流程**
- 所有長時間操作（>30秒）必須：
  1. 先調問使用者是否要執行
  2. 提供預估時間
  3. 提供中斷選項
- 格式：
  ```
  ⏳ 此操作預估需要 5-10 分鐘，將暫時阻塞對話。
  
  您希望：
  1. 立即執行（我會在此等待完成）
  2. 在終端機手動執行（請提供指令）
  3. 取消此操作
  
  請選擇選項。
  ```

## 5. 安全操作確認
- **敏感操作必須二次確認**
- 模型刪除、系統清理、大檔案操作需要二次確認
- 格式：
  ```
  ⚠️ 重要提醒：您即將永久刪除以下模型：
  - qwen3:8b-optimized (5.2GB)
  - qwen2.5-coder:7b (4.7GB)
  
  此操作無法復原。您確定要繼續嗎？（yes/no）
  ```

## 6. 錯誤回滾機制
- **所有操作必須能夠回滾**
- 執行任何修改性質的操作前，記錄當前狀態
- 格式：
  ```
  操作前狀態已記錄。如需回滾，請輸入：rollback
  ```

## 7. 記憶體使用限制
- **Ollama 模型不能超過系統可用記憶體的80%**
- 任何模型操作前必須檢查記憶體使用率
- 格式：
  ```
  📊 當前記憶體使用率：57%
  模型檔案大小：5.2GB
  安裝後預估使用率：85%
  建議先卸載其他模型或增加記憶體。
  ```

## 8. 網路下載限制
- **不能同時執行多個網路下載任務**
- 任何下載使用網路頻頻必須檢查網路資源
- 格式：
  ```
  🌐 網路資源檢查：
  - 下載速率：10MB/s
  - 延遲：50ms
  - 剩餘頻頻：100%
  
  確定要下載此檔案嗎？
  ```

## 9. 程式碼安全
- **不能執行未知來源的程式碼**
- 任何執行指令必須驗證源碼是合理的
- 格式：
  ```
  🔒 程式碼安全檢查：
  - 源碼來源：當前專案目錄
  - 已當前用戶確認
  - 不包含短網址或外部命令
  
  確定要執行此程式碼嗎？
  ```

## 10. 用戶選擇優先
- **所有操作必須等待用戶決定**
- 任何經典的計畫都必須先給用戶確認
- 格式：
  ```
  🎯 專案準備狀態：
  - 已備份現有檔案
  - 已分析專案結構
  - 已準備實作計畫
  
  您希望繼續執行這些計畫嗎？
  ```

