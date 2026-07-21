---
name: session-handoff
description: "Save current session state to the Obsidian vault (Markdown handoff store) at session end. Triggers on handoff, bye, done, wrap up, or Chinese equivalents. Multi-agent architecture with private (per-agent) and shared (cross-agent) shards. Three-tier memory: Active, Archive, Long-term. Use whenever the user wants to end a session, save progress, or says anything indicating they are done for now. (收工/結束)"
---

# Session Handoff — Multi-Agent Three-Tier Memory System

## The Problem

Claude Code sessions are stateless. When a session ends, all context is lost. The next session starts from scratch — no memory of what was done, what's in progress, or what decisions were made.

This skill solves that by writing structured Markdown handoff shards to a filesystem store (an Obsidian vault) before each session ends, and reading them back at the start of the next session via a SessionStart hook.

> **2026-07-21 cutover**：儲存後端已從 Apple Notes 切換為 Obsidian vault「Agent 工作區」的
> `handoff/` 目錄（iCloud 同步）。Apple Notes 舊 note 已凍結並匯出歸檔，不要再寫。

## Configuration

Read the user's CLAUDE.md for a `Session Handoff` config section. If found, use those values. If not found, use defaults.

**Example config in CLAUDE.md:**

```markdown
## Session Handoff Config
- Agent ID: Pro CC
- Handoff root: ~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Agent 工作區/handoff
- Other Agents: Mini CC
- Private budget: 1500 chars
- Shared budget: 1000 chars
```

**Defaults (when no config section exists):**

| Setting | Default | How it's determined |
|---------|---------|---------------------|
| Agent ID | Machine hostname | `hostname -s` |
| Handoff root | `~/.agents/handoff` | Fixed fallback（本機實際用 vault 路徑，見上） |
| Other Agents | _(none — single-agent mode)_ | |
| Private budget | 1500 chars | |
| Shared budget | 1000 chars | |

## Architecture

```
Session ends
    ↓
[Private] {root}/Active/{AgentID}.md   ← read by this agent's hook
[Shared]  {root}/Shared/{AgentID}.md   ← all agents' hooks merge every Shared/*.md
    ↓ old Active content archived to
[Mid-term] {root}/Archive/{YYYY}/….md  ← one file per session, frontmatter-tagged
    ↓ periodic consolidation
[Long-term] Memory files (MEMORY.md)   ← distilled universal knowledge
```

Every file carries YAML frontmatter (`schema_version / kind / agent / updated_at`), validated by `scripts/markdown_storage.py`. Malformed files fail loudly instead of being silently mangled.

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

| Shard | Budget |
|------|--------|
| Private | Per config (default 1500 chars) |
| Shared | Per config (default 1000 chars) |
| Hook-injected context total | ~2500 chars |

The budget exists because these shards get injected into every session start. Keeping them compact means less token waste and more room for actual work.

## Workflow

### Phase 0: Storage Sanity Check

```bash
ROOT="/Users/fredchu/Library/Mobile Documents/iCloud~md~obsidian/Documents/Agent 工作區/handoff"
find "$ROOT" -name "* 2.md" -o -name "*.icloud" | head
```

- 無輸出 → proceed。
- `* 2.md` 出現 → iCloud 衝突副本，先人工比對合併再寫（不要直接刪）。
- `*.icloud` 出現 → 檔案被 evict 未下載，先 `brctl download` 該路徑再讀寫。

### Phase 1: Archive (Preserve Old Content)

1. Read own shard `{root}/Active/{AgentID}.md`（直接 Read；frontmatter 之後是 body）。
2. If found, archive its body（壓縮成摘要後寫入；`--session-id` 用「日期+主題」保 idempotent）：
   ```bash
   python3 scripts/handoff_cli.py archive --root "$ROOT" --agent "Pro CC" \
     --session-id "20260721-topic" --slug "topic" --body-file /tmp/old_active.md
   ```
3. Read `{root}/Shared/*.md`（Phase 2 determines what to update）。

### Phase 2: Write (Overwrite Private + Update Own Shared Shard)

1. Review this session's conversation, route content:
   - Only relevant to self → Private
   - Useful across agents → Shared
2. Body 寫成台灣繁體中文 Markdown（第一行 `Session Handoff — {AgentID}`、第二行更新時間，之後每專案一個 `**粗體標題**` 段 + bullets）。**不要自己寫 frontmatter** — CLI 會生成並驗證。
   ```bash
   python3 scripts/handoff_cli.py write --root "$ROOT" --kind active --agent "Pro CC" --body-file /tmp/private.md
   python3 scripts/handoff_cli.py write --root "$ROOT" --kind shared --agent "Pro CC" --body-file /tmp/shared.md
   ```
3. Shared 是 per-agent shard（`Shared/{AgentID}.md`）— 只寫自己的檔，永遠不動別的 agent 的 shard。hook 端會合併所有 `Shared/*.md`。
4. **Auto-detect consolidation trigger** — Phase 2 寫完後立即跑
   `python3 scripts/count_archive_entries.py --archive-dir "$ROOT/Archive"`，取 `should_consolidate` 旗標。若為 `true`（Archive 條目數 ≥ 5）→ **直接進 Phase 3，不問用戶**。

### Phase 3: Weekly Consolidation (自動觸發 — Phase 2 後 if Archive >= 5)

**觸發機制**：Phase 2 step 4 偵測到 `should_consolidate: true` 直接進此 Phase。**不問用戶**（用戶 CLAUDE.md 規則：「Weekly Consolidation 達門檻時直接執行，不需確認」）。

1. **Generate weekly report** → save to memory/episodic directory（按 ISO week 分組老 entries）
2. **Distill patterns** → scan Archive for recurring cross-agent issues
3. **Clean Archive** → `python3 scripts/consolidate_archive.py --keep 5 --archive-dir "$ROOT/Archive" --episodic-dir /Users/fredchu/.agents/memory/episodic`

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

## Shard Format

一律 Markdown（不再是 HTML）。**寫入只走 `scripts/handoff_cli.py`**（它呼叫 `markdown_storage.py` 做 frontmatter 生成、schema 驗證、atomic write、路徑逃逸防護）。讀取直接 Read 檔案即可。

### Private body 模板

```markdown
Session Handoff — {AgentID}
更新時間：YYYY/MM/DD

**Project Alpha**
- 進行中的工作項目
- 本次完成的項目

**Project Beta**
- 項目內容
```

### Shared body 模板

```markdown
Session Handoff — Shared
最後更新：YYYY/MM/DD by {AgentID}

**環境同步**
- New MCP server installed — AgentA done, AgentB pending

**跨 Agent 專案狀態**
- Project Alpha: developed on AgentA, ready to deploy to AgentB
```

> **為什麼強制走 CLI**：歷史上（Apple Notes 時期）讓 LLM 現場手寫 AppleScript 並自行判斷
> 「首次與否」，跨 session 判斷不穩 → 累積出重複 note。腳本把確定性邏輯固化（upsert、
> schema 驗證、atomic write），從源頭消滅重複與半成品檔。iCloud 同步下 atomic write 也
> 避免 bird 上傳寫到一半的檔案。

## Rules

- NEVER skip handoff with "nothing was done" — even a briefing session gets a shard
- Confirm to user after writing handoff, include the shard path
- Private shard is always `{root}/Active/{AgentID}.md`；own Shared shard is `{root}/Shared/{AgentID}.md`
- Never touch another agent's shards
- Body 一律台灣繁體中文 Markdown；技術名詞保留原文
- 所有寫入（Active/Shared/Archive）一律走 `scripts/handoff_cli.py`；不要手寫 frontmatter、不要直接 Write shard 檔、絕不再寫 Apple Notes handoff note
- Phase 0 sanity check 發現 iCloud 衝突副本（`* 2.md`）→ 先人工合併再寫

## Prerequisites

- **Python 3** — runs the deterministic helper scripts（stdlib only）
- **A filesystem handoff root** — 本機用 Obsidian vault「Agent 工作區」`handoff/`（iCloud 同步）；任何可寫目錄皆可
- **SessionStart hook** — to inject handoff content at session start（本機：`~/.claude/scripts/fetch-handoff.sh` 呼叫 `handoff_cli.py session-start`）

## Single-Agent Mode

Activated automatically when no "Other Agents" are configured (or for users with only one machine):

- Skip the Shared shard entirely
- Archive and consolidation work the same way
- Character budget: ~2000 chars for the single shard
