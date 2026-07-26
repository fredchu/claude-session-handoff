# claude-session-handoff

讓 Claude Code 擁有跨 session 記憶的技能，用純 Markdown 檔案實現——對 Obsidian vault 友善。

> 需要 Python 3（僅用標準庫）。任何可寫目錄都能當儲存區；作者本人用 iCloud 同步的 Obsidian vault。也附帶舊版 Apple Notes 的遷移工具（僅限 macOS）。

**[English README](README.md)**

## 問題

Claude Code 的 session 是無狀態的。每次 session 結束，所有 context 都消失。下一次 session 從零開始——不記得做過什麼、進行到哪、做了什麼決策。

## 解法

這個 skill 在每次 session 結束前，自動把結構化的 Markdown 交接檔（shard）寫入檔案系統儲存區，下次 session 開始時透過 `SessionStart` hook 讀回來。等於 AI 自動幫你寫交接便條。

> **v2.0 儲存後端切換** — 後端已從 Apple Notes 改為純 Markdown 檔案。v1.x 用戶請看 [從 Apple Notes 遷移](#從-apple-notes-遷移v1x)。

## 架構

```
Session 結束
    ↓
┌───────────────────────────────────────────────┐
│ [私有] {root}/Active/{AgentID}.md             │  ← 單一 agent 的工作狀態
│ [共有] {root}/Shared/{AgentID}.md             │  ← 跨 agent 同步（每 agent 一片）
└───────────────────────────────────────────────┘
    ↓ 舊內容歸檔
┌───────────────────────────────────────────────┐
│ [歸檔] {root}/Archive/{YYYY}/….md             │  ← 每次 session 一個檔案
└───────────────────────────────────────────────┘
    ↓ 定期整合
┌───────────────────────────────────────────────┐
│ [長期] MEMORY.md / episodic 記憶檔            │  ← 提煉後的知識
└───────────────────────────────────────────────┘
```

每個檔案都帶 YAML frontmatter（`schema_version / kind / agent / updated_at`），由內附腳本生成並驗證。格式壞掉會大聲報錯，不會被靜默弄爛。

### 三階記憶系統

| 層級 | 儲存位置 | 生命週期 |
|------|---------|---------|
| **活躍層** | 私有 + 共有 shard | 每次 session 覆寫 |
| **歸檔層** | `Archive/{YYYY}/` 檔案 | 滾動保留最近 5 條 |
| **長期層** | MEMORY.md / episodic 檔案 | 永久，提煉後的模式 |

### 多 Agent 支援

如果你在多台機器跑 Claude Code（例如筆電做互動開發 + 伺服器跑無人值守任務），每個 agent 寫自己的私有 shard **和自己的共有 shard**（`Shared/{AgentID}.md`）——永遠不碰別的 agent 的檔案。session 開始時，各 agent 的 hook 會合併所有 `Shared/*.md`。

也支援單 agent 模式——直接跳過共有 shard 就好。

## 安裝

### 1. 安裝 skill

```bash
npx skills add fredchu/claude-session-handoff
```

### 2. 選一個 handoff root

任何可寫目錄都行。兩種常見選擇：

- `~/.agents/handoff` — 純本地、零依賴
- iCloud/Syncthing 上的 Obsidian vault 資料夾 — 跨機器同步，還能在 Obsidian 裡瀏覽

```bash
mkdir -p ~/.agents/handoff
```

### 3. 設定 SessionStart hook

複製範例 hook 腳本，設定你的 agent 名稱和 root：

```bash
cp hooks/session-start.sh ~/.claude/hooks/session-start.sh
chmod +x ~/.claude/hooks/session-start.sh
# 編輯腳本裡的 AGENT_ID 和 HANDOFF_ROOT
```

加入 `.claude/settings.json`：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "~/.claude/hooks/session-start.sh"
      }
    ]
  }
}
```

hook 會呼叫 `handoff_cli.py session-start`，印出私有 shard 加上所有 agent 的共有 shard（超過 `--stale-days`（預設 14 天）未更新的 shard 會標 `⚠️ stale`）。

### 4. 在 CLAUDE.md 加入設定和觸發規則

在使用者層級的 `CLAUDE.md`（`~/.claude/CLAUDE.md`）加入：

```markdown
## Session Handoff Config
- Agent ID: Main
- Handoff root: ~/.agents/handoff
- Other Agents:（留空代表單 agent 模式）
- Private budget: 1500 chars
- Shared budget: 1000 chars

## Session Handoff Rules
- 用戶說「收工」「bye」「結束」「handoff」時 → 執行 `/session-handoff`
- 即使「還沒做什麼事」也不可跳過
```

## 使用方式

session 結束時說「收工」或「handoff」就好。Skill 會自動：

1. **歸檔**前一次的交接內容（每次 session 一個帶 frontmatter 的檔案）
2. **寫入**新的私有 + 共有 shard（透過 `handoff_cli.py`）
3. **整合**（Archive 達 5 條時自動觸發，老條目提煉進 episodic 記憶）
4. **提煉教訓**寫入長期記憶

## 運作原理

### 所有寫入走同一個 CLI

執行的 LLM 永遠不手寫 shard 檔案。所有寫入（Active / Shared / Archive）一律走 `scripts/handoff_cli.py`，由它負責 frontmatter 生成、schema 驗證、atomic write、路徑逃逸防護：

```bash
python3 scripts/handoff_cli.py write   --root "$ROOT" --kind active --agent "Main" --body-file /tmp/private.md
python3 scripts/handoff_cli.py write   --root "$ROOT" --kind shared --agent "Main" --body-file /tmp/shared.md
python3 scripts/handoff_cli.py archive --root "$ROOT" --agent "Main" --session-id "20260726-topic" --slug "topic" --body-file /tmp/old.md
```

讀取直接讀檔即可。這個設計來自血淚教訓：v1.x（Apple Notes 時期）讓 LLM 現場即興寫入，長期累積出重複筆記和被弄爛的內容；確定性腳本從源頭解決。atomic write 也避免雲端同步上傳寫到一半的檔案。

### 內容分流

```
本次 session 產出的資訊
    ↓
另一個 agent 也需要知道？
    ├── 是 → 共有 shard
    └── 否 → 私有 shard
```

- **私有**：進行中的 feature branch、環境特有問題、只跟這台機器有關的事
- **共有**：跨 agent 的專案狀態、用戶決策、環境同步進度

### 字元預算

shard 保持精簡，注入 session 時不浪費 token：

| Shard | 預算 |
|------|------|
| 私有 | 1500 字元 |
| 共有 | 1000 字元 |
| 注入總計 | ~2500 字元 |

## 為什麼用純 Markdown？

- git 可 diff、可 grep、不被特定廠商綁死
- 任何同步層都能用（iCloud、Syncthing、git），還能在 Obsidian 裡瀏覽
- frontmatter 有 schema 驗證——壞掉會大聲報錯
- 沒有 AppleScript 的不穩定、沒有 HTML round-trip 摧殘（Apple Notes 曾把 CJK 粗體標題切碎成多段）
- 跨平台：儲存腳本是純標準庫 Python

## 從 Apple Notes 遷移（v1.x）

repo 保留了舊版工具，做一次性匯出：

```bash
python3 scripts/export_notes_to_markdown.py --root ~/.agents/handoff --agent "Main" \
  --folder "Claude 工作區"
```

這會把現有的私有 / 共有 / Archive 筆記轉進 Markdown 儲存區。匯出後就完全不要再寫 Apple Notes——舊筆記變成凍結的歸檔。

## 授權

MIT
