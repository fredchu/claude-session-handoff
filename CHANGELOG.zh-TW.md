## 1.3.0 - 2026-04-27

### 變更
- 新增 macOS 26 HTML 格式規則表（h1/h2/h3、code block、清單、空行對照）
- 建立筆記改用 AppleScript `make new note`（取代 MCP `create-note`，避免標題重複）
- 更新筆記優先使用 AppleScript `set body of`（MCP `update-note` 可作為備用）
- 段落標題從 `<h2>` 改為 `<div><b>...</b></div>`，避免舊版 macOS 的 font-size 感染

### 文件
- 補上 Pro CC 必遵守的 macOS 26 HTML 格式要求
- 註明 h1/h2/h3 font-size 感染是舊版 macOS Tahoe 的 OS bug，已修復

## 1.2.0 - 2026-03-25

### 新功能
- 將 Phase 4 從單純的 Spot Check 擴充為完整 Lesson Extraction 系統
- 新增 5 個偵測信號：反覆編輯、bash 失敗循環、用戶糾正、WebSearch 缺口、方案切換
- 新增 5 步驟提煉流程：掃描 → 提煉 → 判斷歸屬 → 詢問用戶 → 跨專案 promote
- 新增結構化教訓檔格式
- 新增跨專案 promote 檢查（同類教訓出現在 2+ 專案時建議 promote 到 MEMORY.md）

## 1.1.0 - 2026-03-08

### 新功能
- 從 CLAUDE.md 讀取 Agent 設定（AgentID、筆記資料夾、字元預算），不再寫死
- 新增 SessionStart hook 範例腳本（`hooks/session-start.sh`）
- 新增 macOS 限定說明

### 重構
- 將 SKILL.md 移至 repo 根目錄，相容 skills.sh 平台

### 文件
- 安裝方式改用 `npx skills add`
- 新增具體的 hook 設定步驟與 CLAUDE.md 設定範例

## 1.0.0 - 2026-03-08

### 新功能
- 多 Agent session 交接：私有筆記 + 共有筆記寫入 Apple Notes
- 三階記憶系統：活躍層 → 歸檔層 → 長期層
- 內容分流與自動去重
- 字元預算控制（注入總計約 2500 字元）
- 每週整合（Archive 達 5 條時自動觸發）
- 即時偵測值得寫入長期記憶的教訓
- 支援單 Agent 模式
