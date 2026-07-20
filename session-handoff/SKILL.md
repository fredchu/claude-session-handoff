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

### Phase 0: Dedup Precheck (Heal Pre-existing Duplicates)

Before reading/writing anything, ensure each canonical title resolves to exactly one note. Run for each title you will touch (`Session Handoff — {AgentID}`, `Session Handoff — Shared`, `Session Handoff — Archive`):

```bash
python3 scripts/applescript_notes.py dedup --title "Session Handoff — {AgentID}"
```

- `OK: 1 note(s)` (or 0) → proceed.
- `Found N duplicate notes…` → inspect the listed ids/dates, then heal with `--apply` (keeps the newest by a locale-independent sort key, deletes the rest) **before** any write — otherwise an exact-title write could update an arbitrary one of the duplicates.

> The example SessionStart hook (`hooks/session-start.sh`) already runs this same `dedup --apply` sweep for all three canonical titles on **every** session start, logging to `~/.claude/scripts/handoff-dedup.log`. That deterministic sweep — not this prose step — is the actual safety net: write-path prevention depends on agents following this skill, but the hook heals duplicates regardless of who or what created them. This Phase 0 step is a belt-and-suspenders precheck for the case where the hook is not installed.

### Phase 1: Archive (Preserve Old Content)

1. Read own private note `Session Handoff — {AgentID}` (`applescript_notes.py read --title …`, or MCP).
2. If found, keep its content for archiving.
3. Read `Session Handoff — Archive`, prepend old private content to the top (date separator, tagged with AgentID), then write back via `applescript_notes.py write --title "Session Handoff — Archive" --html-file …`. The write upserts — it creates the Archive note if it does not exist yet (no separate create step).
4. Read `Session Handoff — Shared` (Phase 2 determines what to update).

### Phase 2: Write (Overwrite Private + Update Shared)

1. Review this session's conversation, route content:
   - Only relevant to self → write to Private
   - Useful across agents → write to Shared
2. Write private note `Session Handoff — {AgentID}` via `applescript_notes.py write --title … --html-file …` (upsert — same command whether it exists or not; no first-time branch).
3. Update Shared note the same way (only update own sections, never delete other agents' content — read current Shared, edit your sections, write the merged HTML back).
4. Use `<div><b>段落標題</b></div>` to separate multiple projects — **never `<h2>`** (infects subsequent text with font-size: 11px)
5. **Auto-detect consolidation trigger** — Phase 2 寫完後立即跑 `scripts/count_archive_entries.py --note-title "Session Handoff — Archive"`，取 `should_consolidate` 旗標。若為 `true`（即 Archive 條目數 ≥ 5）→ **直接進 Phase 3，不問用戶**。

### Phase 3: Weekly Consolidation (自動觸發 — Phase 2 後 if Archive >= 5)

**觸發機制**：Phase 2 step 5 偵測到 `should_consolidate: true` 直接進此 Phase。**不問用戶**（用戶 CLAUDE.md 規則：「Weekly Consolidation 達門檻時直接執行，不需確認」）。

1. **Generate weekly report** → save to memory/episodic directory（按 ISO week 分組老 entries）
2. **Distill patterns** → scan Archive for recurring cross-agent issues
3. **Clean Archive** → 用 `python3 scripts/consolidate_archive.py --apply --keep 5 --episodic-dir /Users/fredchu/.agents/memory/episodic` 執行：歸檔老 entries 到 episodic，Archive 留最新 5 條，自動透過 `applescript_notes.py` 寫回 Apple Notes

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
- **建立 / 更新**：一律走 `scripts/applescript_notes.py write`（exact-title upsert，內建 lint + transient retry）。不要手寫 `make new note` / `set body`，也不要用 MCP create-note（會製造重複標題）。
- **讀取/搜尋**：MCP 或 `applescript_notes.py read` 皆可
- **去重**：`applescript_notes.py dedup --title T [--apply]`

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

### 寫入方式（一律走 upsert 腳本，不要手寫 AppleScript）

**所有建立/更新都必須透過 `scripts/applescript_notes.py write`。** 它是 find-or-create upsert：用**精確標題**（`name is`，非 `contains`）找既有 note，找到就覆寫 body、找不到才建立——同一個指令處理建立與更新兩種情況，呼叫端不需要也不應該自己判斷「first time 與否」。

> **為什麼**：歷史上建立/更新讓 LLM 現場手寫 `make new note` / `set body` 並自行判斷是否首次，跨 session 判斷不穩 + Notes 偶發 `-1719` 索引錯誤 → 累積出重複 note（2026-05-29 清出 2 個 Shared、3 個 Pro CC）。腳本把這段確定性邏輯固化，內建 exact-match + transient retry，從源頭消滅重複。

```bash
# 建立或更新（upsert）— 把 HTML 寫進暫存檔再餵給腳本（避免 shell 跳脫地獄）
python3 scripts/applescript_notes.py write \
  --title "Session Handoff — Pro CC" \
  --html-file /tmp/handoff_private.html
# 預設 --folder "Claude 工作區" --account "iCloud"；腳本會先 quick_lint（含 <p>/font-size 擋下，exit 2）
```

讀取仍可用 MCP 或 osascript；只有**寫入**強制走腳本。
- `read --title T`：讀 body（精確標題）
- `exists --title T`：exit 0=存在 / 1=不存在
- `dedup --title T [--apply]`：偵測同標題重複（見 Phase 1 precheck）

## Rules

- NEVER skip handoff with "nothing was done" — even a briefing session gets a note
- Confirm to user after writing handoff, include the note title
- Private note title is always `Session Handoff — {AgentID}`
- Shared note title is always `Session Handoff — Shared`
- When updating Shared, only update own sections — never delete other agents' content
- Multiple projects in one note, separated by `<div><b>段落標題</b></div>` — never `<h2>`
- Write notes in HTML format (not markdown) — Apple Notes doesn't render markdown
- 所有寫入（建立/更新/Archive prepend）一律走 `scripts/applescript_notes.py write`（exact-title upsert）；不要手寫 AppleScript 或用 MCP create-note。讀取可用 MCP。
- Phase 0 dedup precheck 是防重複的第一道關卡；發現重複先 `dedup --apply` 再寫

## Prerequisites

- **macOS** — Apple Notes is macOS/iOS only
- **Apple Notes MCP** — optional, for **reading/searching** convenience (e.g., [apple-notes-mcp](https://github.com/Dhravya/apple-notes-mcp)). **Writes do NOT use MCP** — they go through `scripts/applescript_notes.py write` (exact-title upsert). MCP `create-note` produces duplicate headings and is the bypass that caused duplicate notes.
- **Python 3** — runs the deterministic helper scripts (`applescript_notes.py`, consolidation, lint). Stdlib only.
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
