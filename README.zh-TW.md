# claude-session-handoff

讓 Claude Code 擁有跨 session 記憶的技能，透過 Apple Notes 實現。

**[English README](README.md)**

## 問題

Claude Code 的 session 是無狀態的。每次 session 結束，所有 context 都消失。下一次 session 從零開始——不記得做過什麼、進行到哪、做了什麼決策。

## 解法

這個 skill 在每次 session 結束前，自動把結構化的交接筆記寫入 Apple Notes，下次 session 開始時透過 `SessionStart` hook 讀回來。等於 AI 自動幫你寫交接便條。

## 架構

```
Session 結束
    ↓
┌─────────────────────────────────────────┐
│ [私有] Session Handoff — {AgentID}      │  ← 單一 agent 的工作狀態
│ [共有] Session Handoff — Shared         │  ← 跨 agent 同步
└─────────────────────────────────────────┘
    ↓ 舊內容歸檔
┌─────────────────────────────────────────┐
│ [歸檔] Session Handoff — Archive        │  ← 滾動歷史
└─────────────────────────────────────────┘
    ↓ 每週整合
┌─────────────────────────────────────────┐
│ [長期] MEMORY.md / 記憶庫檔案            │  ← 提煉後的知識
└─────────────────────────────────────────┘
```

### 三階記憶系統

| 層級 | 儲存位置 | 生命週期 |
|------|---------|---------|
| **活躍層** | 私有 + 共有筆記 | 每次 session 覆寫 |
| **歸檔層** | Archive 筆記 | 滾動保留最近 5 條 |
| **長期層** | MEMORY.md / 記憶庫 | 永久，提煉後的模式 |

### 多 Agent 支援

如果你在多台機器跑 Claude Code（例如筆電做互動開發 + 伺服器跑無人值守任務），每個 agent 有自己的私有筆記，同時共享一則筆記做跨 agent 協調。

也支援單 agent 模式——直接跳過共有筆記就好。

## 安裝

### 1. 安裝 skill

```bash
npx skills add fredchu/claude-session-handoff
```

### 2. 安裝 Apple Notes MCP

你需要一個能讀寫 Apple Notes 的 MCP server。例如：[apple-notes-mcp](https://github.com/Dhravya/apple-notes-mcp)

```bash
claude mcp add --scope user apple-notes -- npx -y apple-notes-mcp
```

### 3. 設定 SessionStart hook

在 `.claude/settings.json` 加入 hook，讓 session 開始時自動讀取交接筆記：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "your-script-to-read-handoff-notes.sh"
      }
    ]
  }
}
```

腳本需搜尋 Apple Notes 裡的交接筆記，把內容輸出到 stdout。

### 4. 在 CLAUDE.md 加入觸發規則

在專案或使用者層級的 `CLAUDE.md` 加入：

```markdown
## Session Handoff
- 用戶說「收工」「bye」「結束」「handoff」時 → 執行 `/session-handoff`
- 即使「還沒做什麼事」也不可跳過
```

## 使用方式

session 結束時說「收工」或「handoff」就好。Skill 會自動：

1. **歸檔**前一次的交接內容
2. **寫入**新的私有 + 共有筆記
3. **整合**（Archive 達 5 條時觸發週報）
4. **即時偵測**值得寫入長期記憶的教訓

## 運作原理

### 內容分流

```
本次 session 產出的資訊
    ↓
另一個 agent 也需要知道？
    ├── 是 → 共有筆記
    └── 否 → 私有筆記
```

- **私有**：進行中的 feature branch、環境特有問題、只跟這台機器有關的事
- **共有**：跨 agent 的專案狀態、用戶決策、環境同步進度

### 字元預算

筆記保持精簡，注入 session 時不浪費 token：

| 筆記 | 預算 |
|------|------|
| 私有 | 1500 字元 |
| 共有 | 1000 字元 |
| 注入總計 | ~2500 字元 |

## 為什麼用 Apple Notes？

- macOS 原生——不需要額外基礎設施
- 透過 iCloud 跨裝置同步
- 全文搜尋
- 資料夾分類
- 有現成的 MCP server

## 授權

MIT
