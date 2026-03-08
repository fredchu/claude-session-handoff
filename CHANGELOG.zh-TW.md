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
