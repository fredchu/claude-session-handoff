## 2.0.0 - 2026-07-26

### 重大變更
- **儲存後端從 Apple Notes 切換為純 Markdown 檔案**，存放於檔案系統的 handoff root（任何可寫目錄皆可；作者用 iCloud 同步的 Obsidian vault）。既有的 Apple Notes handoff 筆記請用 `export_notes_to_markdown.py` 做一次性匯出後凍結——skill 不再寫入 Apple Notes。
- 共有狀態改為**每 agent 一片 shard**（`Shared/{AgentID}.md`），由各 agent 的 SessionStart hook 合併讀取，取代原本的單一共有筆記。任何 agent 都不會寫別的 agent 的檔案。
- Archive 改為 **每次 session 一個檔案**，存於 `Archive/{YYYY}/` 並帶 YAML frontmatter，取代原本單一滾動的 Archive 筆記。

### 新增
- `markdown_storage.py` — 儲存層，負責 frontmatter 生成、schema 驗證（`schema_version / kind / agent / updated_at`）、atomic write、路徑逃逸防護；格式壞掉會大聲報錯。附 pytest 測試套件。
- `handoff_cli.py` — 唯一寫入口（`write` / `archive` / `session-start`）。`session-start` 印出私有 shard 加所有 agent 的共有 shard，含字元預算截斷，超過 `--stale-days`（預設 14 天）未更新的 shard 標 `⚠️ stale`。
- `export_notes_to_markdown.py` — v1.x Apple Notes 內容一次性遷移進 Markdown 儲存區。
- Phase 0 儲存健檢，防 iCloud 陷阱：衝突副本（`* 2.md`）與被 evict 的（`.icloud`）檔案。

### 變更
- `count_archive_entries.py` / `consolidate_archive.py` 移植到 Markdown 後端；consolidation 改為預設直接執行（`--dry-run` 才是預覽——舊的 `--apply` 旗標移除）。
- Episodic（長期）輸出搬到 `~/.agents/memory/episodic`。
- 範例 hook `hooks/session-start.sh` 改寫為呼叫 `handoff_cli.py session-start`（AppleScript 讀取器與去重掃描在 Markdown 後端已不需要）。
- README（英文 + 繁中）全面改寫為 Markdown/Obsidian 架構。

## 1.4.1 - 2026-06-15

### 修復
- `consolidate_archive.py`：新增 fail-safe 防護，當解析回傳 0 條（例如短暫的 applescript 讀取競態讀到過期／空白 HTML）時，不再把 Archive 筆記重寫成只剩標題、銷毀 handoff 歷史。改為：來源非空但解析 0 條 → 以非零碼中止、條目數在 keep 範圍內 → no-op、只有真正溢出才重寫；並補上 promote／no-op／fail-closed／只剩標題 等情境的回歸測試。
- `consolidate_archive.py`：重建時保留 Archive 標準標題列、強制 `--episodic-dir`，確保歸檔條目不會被靜默丟棄。

## 1.4.0 - 2026-05-29

### 新增
- 把所有確定性邏輯抽成純 stdlib Python 腳本（`applescript_notes.py`、`consolidate_archive.py`、`count_archive_entries.py`、`lint_handoff_html.py`、`render_handoff_html.py`）並附 pytest 測試套件，取代過去每次都要 LLM 現場重新推導的散文式指引。
- Phase 2 後自動觸發 weekly consolidation：Archive 達門檻時自動執行，不再詢問。
- `applescript_notes.py dedup --title T [--apply]`：列出或修復同精確標題的重複筆記，以與語系無關的 `YYYYMMDDHHMMSS` 排序鍵保留最新一則（同秒以 id 決勝）；刪除在重試下具冪等性。
- 範例 hook（`hooks/session-start.sh`）的確定性 SessionStart 去重掃描：每次 session 啟動對所有標準標題跑 `dedup --apply`，記錄到 `~/.claude/scripts/handoff-dedup.log`、絕不輸出到 stdout。這是真正的安全網——無論重複怎麼產生都能修復，因為寫入路徑的預防本身依賴 LLM 是否遵循流程。

### 修復
- **重複筆記的根因。** 建立／更新過去是 LLM 現場手寫 AppleScript、自行判斷「首次或更新」，長期累積出重複的標準筆記。所有寫入現在一律走 `applescript_notes.py write` 的精確標題（`name is`，非 `contains`）upsert，且 `run_applescript` 會重試短暫的 osascript 失敗（`-1719`／`-1712`／`-1700`／execution error／索引錯誤）。
- Archive 標題 regex 現在容忍 Apple Notes 在 round-trip 注入的 `<br>`（及自閉合 `<br/>`），`count_archive_entries.py` 不再對真實 Archive 筆記回報 0。

### 變更
- **寫入不再使用原始 AppleScript 或 MCP `create-note`**（取代下方 1.3.0 的說明）。流程把所有建立／更新／archive-prepend 都導向 `applescript_notes.py write`，並新增 Phase 0 去重預檢。Apple Notes MCP 現為選用，僅用於讀取／搜尋。

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
