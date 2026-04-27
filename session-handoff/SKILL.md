---
name: session-handoff
description: "Save current session state to Apple Notes at session end. Triggers on handoff, bye, done, wrap up, or Chinese equivalents. Multi-agent architecture with private (per-agent) and shared (cross-agent) notes. Three-tier memory: Active, Archive, Long-term. Use whenever the user wants to end a session, save progress, or says anything indicating they are done for now. (收工/結束)"
---

# Session Handoff — Multi-Agent Three-Tier Memory System

## The Problem

Claude Code sessions are stateless. When a session ends, all context is lost. The next session starts from scratch — no memory of what was done, what's in progress, or what decisions were made.

This skill solves that by writing structured handoff notes to Apple Notes before each session ends, and reading them back at the start of the next session via a SessionStart hook.

## Configuration

Read the user's CLAUDE.md for a `Session Handoff` config section. If found, use those values. If not found, use defaults.

**Example config in CLAUDE.md:**

```markdown
## Session Handoff Config
- Agent ID: Pro CC
- Notes folder: Claude Workspace
- Other Agents: Mini CC
- Private budget: 1500 chars
- Shared budget: 1000 chars
```

**Defaults (when no config section exists):**

| Setting | Default | How it's determined |
|---------|---------|---------------------|
| Agent ID | Machine hostname | `hostname -s` |
| Notes folder | `Claude Workspace` | Fixed |
| Other Agents | _(none — single-agent mode)_ | |
| Private budget | 1500 chars | |
| Shared budget | 1000 chars | |

When Other Agents is empty, automatically use Single-Agent Mode (skip Shared note, no AgentID suffix on note title).

## Architecture

```
Session ends
    ↓
[Private] Session Handoff — {AgentID}   ← read by this agent's hook
[Shared]  Session Handoff — Shared      ← read by all agents' hooks
    ↓ old content prepended to
[Mid-term] Session Handoff — Archive    ← merged history, tagged by agent
    ↓ periodic consolidation
[Long-term] Memory files (MEMORY.md)    ← distilled universal knowledge
```

### Agent Identification

Define your agents in CLAUDE.md (see Configuration above). Example:

| AgentID | Machine | Role |
|---------|---------|------|
| `Pro CC` | MacBook Pro | Interactive development |
| `Mini CC` | Mac mini server | Unattended tasks, cron jobs |

To add a new agent, just add it to the "Other Agents" list in your config. Note naming extends automatically.

## Note Naming

| Note | Title | Written by | Read by |
|------|-------|------------|---------|
| Private | `Session Handoff — {AgentID}` | Self | Self |
| Shared | `Session Handoff — Shared` | Any agent | All agents |
| Archive | `Session Handoff — Archive` | Any agent | On demand |

## Content Routing (Key to Deduplication)

```
This session's output
    ↓
Does another agent need to know?
    ├── Yes → Write to Shared
    └── No  → Write to Private
```

| Where | Content type | Example |
|-------|-------------|---------|
| **Private** | Work only this agent is doing | A feature branch in progress |
| **Private** | Environment-specific issues | PATH problems on this machine |
| **Shared** | Cross-agent project state | App developed on Main, deploying to Server |
| **Shared** | User decisions/preference changes | User decided to deprecate a tool |
| **Shared** | One side done, other needs to know | Main installed a new MCP, Server needs it too |

**Dedup rule: Content written to Shared is NOT repeated in Private.**

## Character Budget

| Note | Budget |
|------|--------|
| Private | Per config (default 1500 chars) |
| Shared | Per config (default 1000 chars) |
| Hook-injected context total | ~2500 chars |

The budget exists because these notes get injected into every session start. Keeping them compact means less token waste and more room for actual work.

## Workflow

### Phase 1: Archive (Preserve Old Content)

1. Search for own private note `Session Handoff — {AgentID}`
2. If found, read its content
3. Search for `Session Handoff — Archive`
   - Exists → prepend old private content to Archive top (with date separator, tagged with AgentID)
   - Not found → create Archive, move to configured notes folder
4. Search for `Session Handoff — Shared`, read existing shared content (Phase 2 determines what to update)

### Phase 2: Write (Overwrite Private + Update Shared)

1. Review this session's conversation, route content:
   - Only relevant to self → write to Private
   - Useful across agents → write to Shared
2. Overwrite private note `Session Handoff — {AgentID}`
   - First time: AppleScript `make new note at folder "Claude 工作區" with properties {body:"..."}`
3. Update Shared note (only update own sections, never delete other agents' content)
   - First time: AppleScript `make new note at folder "Claude 工作區" with properties {body:"..."}`
4. Use `<div><b>段落標題</b></div>` to separate multiple projects — **never `<h2>`** (infects subsequent text with font-size: 11px)

### Phase 3: Weekly Consolidation (Triggered when Archive >= 5 entries)

1. **Generate weekly report** → save to memory/episodic directory
2. **Distill patterns** → scan Archive for recurring cross-agent issues
3. **Clean Archive** → keep only the most recent 5 entries

### Phase 4: Lesson Extraction (Session 回顧)

在 Phase 2 寫完 handoff 後，回顧本次 session 是否有值得記錄的教訓。

**偵測信號（任一命中即觸發）：**

| 信號 | 代表什麼 |
|------|---------|
| 同一檔案 Edit 3+ 次才做對 | 踩坑、反覆試錯 |
| Bash 指令失敗 → 修正 → 再跑 | debug 循環 |
| 用戶糾正做法（「不是這樣」「用 X 不要 Y」） | 偏好/地雷 |
| WebSearch 查了某技術問題才解決 | 知識缺口 |
| 嘗試了方案 A 失敗、換方案 B 才成功 | 技術選型教訓 |

**流程：**

1. **掃描**：回顧 session 中的 error→fix 循環、用戶糾正、方案切換
2. **提煉**：每個教訓用一句話描述 root cause + 正確做法
3. **判斷歸屬**：教訓屬於哪個專案？
   - 有明確專案 → `company/<project>/lessons/YYYY-MM-DD-<topic>.md`
   - 通用性高（工具用法、Claude Code 行為）→ MEMORY.md 或 `記憶庫/語義記憶/`
4. **詢問用戶**：「這次 session 有 N 個教訓值得記：[列表]。要存嗎？」
   - 用戶說好 → 寫入
   - 用戶說不用 → 跳過
5. **跨專案 Promote 檢查**：寫入教訓後，grep `company/*/lessons/` 找相似 pattern
   - 同類教訓在 **2+ 專案** 出現 → 建議 promote 到 MEMORY.md
   - Promote 後在原始 lessons 檔加一行 `> ⬆️ 已 promote 到 MEMORY.md`

**教訓檔格式（company lessons）：**

```markdown
# 標題 — 一句話結論

> 日期：YYYY/MM/DD
> 專案：<project name>
> 分支/路徑：（如適用）

## Root Cause
一段話說明為什麼會踩坑。

## 正確做法
下次遇到同類問題該怎麼做。

## 證據
- 本次 session 中的具體事件（簡述）
```

**不記的東西：**
- 純粹的進度更新（那是 handoff 的事）
- 已經寫在 CLAUDE.md 裡的規則
- 一次性的操作細節（已經在 git history 裡）

## Note Format

Notes use HTML。操作規則：
- **建立**：AppleScript `make new note with properties {body:...}`（不用 MCP create-note — 會標題重複）
- **更新**：AppleScript `set body of targetNote to "..."`（優先；MCP update-note 可作備用，但務必確認 HTML 不含禁用標籤）
- **讀取/搜尋**：MCP 即可

### macOS 26 HTML 格式規則（Pro CC 必遵守）

| 格式 | HTML | 說明 |
|------|------|------|
| 筆記標題（大） | `<h1>標題</h1>` | → 24px bold；第一行自動成筆記名稱 |
| 段落標題 | `<h2>標題</h2>` | → 18px bold |
| 子標題 | `<h3>標題</h3>` 或 `<div><b>...</b></div>` | 兩者結果相同 |
| 內文 | `<div>...</div>` | |
| Code block（每行） | `<div><tt>code</tt><tt><br></tt></div>` | iOS/macOS 原生格式 |
| 清單 | `<ul><li>...</li></ul>` | |
| 空行 | `<div><br></div>` | |

**避免**：`<p>`（多餘間距）、任何自訂 `font-size`

**注意**：h1/h2/h3 感染 font-size 是舊版 macOS Tahoe 的 OS bug（已修復）。更新 OS 後 h1/h2/h3 正常可用。

### Private Note 模板

```html
<div>Session Handoff — {AgentID}</div>
<div><i>更新時間：YYYY/MM/DD</i></div>
<div><br></div>
<div><b>Project Alpha</b></div>
<ul><li>進行中的工作項目</li><li>本次完成的項目</li></ul>
<div><br></div>
<div><b>Project Beta</b></div>
<ul><li>項目內容</li></ul>
```

### Shared Note 模板

```html
<div>Session Handoff — Shared</div>
<div><i>最後更新：YYYY/MM/DD by {AgentID}</i></div>
<div><br></div>
<div><b>環境同步</b></div>
<ul><li>New MCP server installed — AgentA done, AgentB pending</li></ul>
<div><br></div>
<div><b>跨 Agent 專案狀態</b></div>
<ul><li>Project Alpha: developed on AgentA, ready to deploy to AgentB</li></ul>
```

### Archive Entry

```html
<div><b>YYYY/MM/DD [{AgentID}] — Project Alpha, Beta</b></div>
<div>[compressed handoff content]</div>
<hr>
```

### 寫入方式

```applescript
-- 建立新筆記（用 AppleScript，不用 MCP create-note）
tell application "Notes"
    tell account "iCloud"
        make new note at folder "Claude 工作區" with properties {body:"HTML_HERE"}
    end tell
end tell
```

更新既有筆記：優先用 AppleScript（`set body of selectedNote to "HTML_HERE"`），MCP `update-note` 也可，但確認寫入的 HTML 不含 `<h2>`/`<h3>`/`<ul>`/`<li>` 和自訂 `font-size`。

```applescript
-- 更新既有筆記
tell application "Notes"
    set targetNote to first note of folder "Claude 工作區" whose name contains "Session Handoff — Pro CC"
    set body of targetNote to "HTML_HERE"
end tell
```

## Rules

- NEVER skip handoff with "nothing was done" — even a briefing session gets a note
- Confirm to user after writing handoff, include the note title
- Private note title is always `Session Handoff — {AgentID}`
- Shared note title is always `Session Handoff — Shared`
- When updating Shared, only update own sections — never delete other agents' content
- Multiple projects in one note, separated by `<div><b>段落標題</b></div>` — never `<h2>`
- Write notes in HTML format (not markdown) — Apple Notes doesn't render markdown
- 建立筆記用 AppleScript，讀取用 MCP；更新優先用 AppleScript（避免 MCP 殘留舊格式）

## Prerequisites

- **macOS** — Apple Notes is macOS/iOS only
- **Apple Notes MCP** — for reading/writing notes (e.g., [apple-notes-mcp](https://github.com/Dhravya/apple-notes-mcp))
- **SessionStart hook** — to inject handoff content at session start (see `hooks/session-start.sh` for a working example)

### SessionStart Hook Setup

1. Copy the example hook script:
   ```bash
   cp hooks/session-start.sh ~/.claude/hooks/session-start.sh
   chmod +x ~/.claude/hooks/session-start.sh
   ```

2. Edit the script — set your `AGENT_ID` and `NOTES_FOLDER` at the top.

3. Add to `.claude/settings.json`:
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

The hook reads your handoff notes via AppleScript and outputs their content to stdout. Claude Code injects this as context at session start.

## Single-Agent Mode

Activated automatically when no "Other Agents" are configured (or for users with only one machine):

- Skip the Shared note entirely
- Use a single `Session Handoff` note (no AgentID suffix)
- Archive and consolidation work the same way
- Character budget: ~2000 chars for the single note
