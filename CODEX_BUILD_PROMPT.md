# AEGIS — Codex Full Build & Fix Specification

This file is the complete task specification for an AI coding agent (Codex, Claude Code, Aider, etc.) to build, complete, and fix the AEGIS codebase. Paste this entire file as the task. Every section is mandatory.

---

## CONTEXT

AEGIS is a personal sovereign autonomous intelligence platform. It consists of a Python kernel and a society of standing agents that communicate over an internal event bus. This repo is real and partially built. The agent's job is to complete what is broken and fill what is missing — never invent architecture that contradicts the existing docs.

---

## READ BEFORE WRITING

Read these files first, in this order:

1. `FOUNDING_CHARTER.md`
2. `PHASES/README.md`
3. `PHASES/PHASE_01_KERNEL_CORE.md`
4. `ARCHITECTURE/SYSTEM_MAP.md` (skip if absent)
5. All files under `kernel/`
6. All files under `agents/`

Only implement what is already documented. Do not add folders, agents, or features that are not already in the repo docs.

---

## OPERATING CONSTRAINTS

- No secrets hardcoded. All secrets are env vars, referenced in `config/aegis.toml`.
- Every trust-critical action (delete, spend, publish, policy change, external write) must pass through `kernel/policy.py` before execution.
- Agents communicate only through `kernel/bus.py`. Direct agent-to-agent calls are forbidden.
- If a component cannot be fully built, create a typed stub with `raise NotImplementedError("reason")` and append a line to `FAILURES.md` at repo root explaining what is missing and why.
- Kernel total line count (all files combined) must stay under 1000 lines. Refactor if exceeded.
- After each fix, make one atomic commit with the commit message listed in the Commit Strategy section.

---

## FAILURE PROTOCOL

When something breaks or a dependency is missing:

1. Write the error and exact context to `FAILURES.md` (create it if absent).
2. Build a typed stub so downstream code compiles and imports cleanly.
3. Move on to the next component immediately.
4. Only halt if 3 or more downstream components are impossible to stub.

---

## WHAT IS COMPLETE — READ ONLY, DO NOT REWRITE

These components are working. Read them for context. Only touch them if a later fix explicitly requires a change:

- `kernel/events.py` — Pydantic event schemas, strict validation, timezone enforcement, secret-leakage detection
- `kernel/bus.py` — append-only JSONL event bus, trace ID replay, in-process fallback
- `kernel/policy.py` — triple-gate policy engine, fail-closed on destructive/wealth action classes
- `kernel/router.py` — local-first model router (Ollama → OpenRouter fallback)
- `kernel/memory.py` — SQLite fallback memory client with provenance tracking
- `kernel/scheduler.py` — priority queue with dedup, retry, resume points
- `kernel/introspect.py` — CLI commands: trace, map, wealth, memory, doctor, demo-flow
- `agents/warden/agent.py` — structure enforcement and delegation veto
- `agents/scribe/agent.py` — memory write, compression, skill promotion
- `pyproject.toml`, `docker-compose.yml`, `config/aegis.toml`, `scripts/install.sh`

---

## FIXES REQUIRED — COMPLETE IN ORDER

---

### FIX 1 — `agents/forge/agent.py`

**Current state:** `on_wake()` returns a hardcoded string and executes nothing. Forge is the artifact execution engine and must actually run things.

**Required behavior:**

```python
# agents/forge/agent.py
#
# Forge executes artifacts: code generation, documents, and shell commands.
# It wraps the Aider CLI for code tasks.
#
# Steps:
#   1. Parse event.payload for: task_type, spec, output_path
#   2. task_type == "code"   → invoke Aider via subprocess:
#                               aider --message "<spec>" --yes --no-git <output_path>
#                             If aider is not installed: write spec to output_path as
#                             a plaintext artifact and set fallback_mode=true in the log.
#   3. task_type == "shell"  → run the command via subprocess, 60s timeout
#   4. task_type == "document" → write payload["spec"] content to output_path
#   5. Before any execution: call kernel/policy.py authorize().
#      If REJECTED: emit POLICY_DECISION event, return immediately without executing.
#   6. After execution: emit AGENT_MAP_CONSEQUENCE event with artifact path + log.
#   7. Append to .aegis/forge_log.jsonl:
#      {trace_id, task_type, command, exit_code, duration_ms, output_path, fallback_mode}
#
# Required event.payload fields:
#   task_type: "code" | "shell" | "document"
#   spec: str
#   output_path: str
```

**Acceptance test:**
An event with `task_type: "document"`, a spec string, and an output_path causes Forge to write the spec to that path. The forge log is written. Policy state appears in the emitted consequence event.

---

### FIX 2 — `agents/loop/agent.py`

**Current state:** `on_wake()` returns a hardcoded string. Loop is the autonomous backlog digester and must actually sequence work.

**Required behavior:**

```python
# agents/loop/agent.py
#
# Loop selects the highest-priority task from the backlog and sequences it through Forge.
#
# On HUMAN_INTENT event:
#   1. Parse intent, urgency, impact, feasibility from payload (default all to 3 if absent).
#   2. Score:  priority = (urgency * 2 + impact * 2 + feasibility) / 5
#   3. Enqueue via kernel/scheduler.py. Skip if duplicate key already pending.
#   4. Append to .aegis/backlog.jsonl:
#      {"key": str, "intent": str, "status": "pending", "retries": 0, "priority": float}
#
# On AGENT_THINKING event:
#   1. Pop highest-priority item from scheduler.
#   2. Decompose into one sub-task: {spec: str, output_path: str}.
#   3. Emit AGENT_EXECUTE event targeting Forge.
#
# On AGENT_MAP_CONSEQUENCE event (Forge completed):
#   1. Emit REMEMBER_CANDIDATE event for Scribe.
#   2. Mark task as "done" in backlog.jsonl.
#
# On failure: call scheduler.retry(). After 3 retries: mark "failed", move on.
# Never enqueue the same key twice in one session.
```

**Acceptance test:**
A HUMAN_INTENT event with `intent: "write a hello world python script"` results in a backlog.jsonl entry with status "pending" and a scored priority value.

---

### FIX 3 — `kernel/scheduler.py` — add async tick loop

**Current state:** The scheduler has no runner. `wake_next()` is never called automatically — agents stay asleep.

**Add this function:**

```python
import asyncio

async def tick(scheduler: Scheduler, bus: EventBus, interval_seconds: float = 1.0) -> None:
    """
    Drives the scheduler from run.py.
    Every interval_seconds: pops the next ready item and publishes its event to the bus.
    Runs until cancelled.
    """
    while True:
        item = scheduler.wake_next()
        if item:
            bus.publish(item.event)
        await asyncio.sleep(interval_seconds)
```

---

### FIX 4 — `run.py` (create at repo root)

**Current state:** There is no single entrypoint. Every component must be started manually.

**Required behavior:**

```python
# run.py — AEGIS system entrypoint
# Usage: python run.py
#
# Startup sequence:
#   1. Run kernel.introspect doctor checks.
#      If any CRITICAL check fails: print the failure and exit(1).
#   2. Initialize: bus, scheduler, memory, policy gate, router.
#   3. Instantiate the 5 core agents: Warden, Scribe, Herald, Forge, Loop.
#   4. Launch scheduler tick as asyncio task.
#   5. Launch each agent's listen loop as asyncio task.
#   6. Print startup summary:
#      "AEGIS running — {N} agents active — bus: {NATS|fallback} — memory: {letta|sqlite}"
#   7. await asyncio.gather(*tasks)
#   8. Handle SIGINT/SIGTERM for graceful shutdown (cancel tasks, flush bus, close memory).
```

---

### FIX 5 — `agents/herald/bridge.py` — complete Telegram connection

**Current state:** The Telegram bridge is partially stubbed. Messages sent to the bot are never received.

**Required behavior:**

```python
# Complete agents/herald/bridge.py
#
# Use python-telegram-bot v20+ (async API).
#
# Inbound (Telegram → AEGIS):
#   On every message: create a HUMAN_INTENT event with
#     trace_id = f"tg_{update.message.message_id}"
#   Publish to bus.
#
# Outbound (AEGIS → Telegram):
#   On AGENT_MAP_CONSEQUENCE event from bus:
#     Look up originating chat_id from .aegis/herald_sessions.jsonl by trace_id.
#     Send consequence_summary as a reply to that chat_id.
#
# Session store: .aegis/herald_sessions.jsonl
#   Each line: {"trace_id": str, "chat_id": int}
#   Flush on shutdown.
#
# If TELEGRAM_BOT_TOKEN env var is absent:
#   Log a warning and skip Telegram initialization.
#   Herald runs in terminal-only mode.
```

---

### FIX 6 — `lens/` — wire real live data

**Current state:** `lens/app/page.tsx` is a static `<ul>` with 5 placeholder items. No data, no routing, no live feed.

**Build a real Next.js 15 app with these five files:**

**`lens/app/api/events/route.ts`** — SSE endpoint:
```typescript
// Tail .aegis/events.jsonl using fs.watch.
// Stream each new line as a Server-Sent Event: data: <json>\n\n
// Content-Type: text/event-stream
// Send a comment ping every 15s to keep the connection alive.
```

**`lens/app/page.tsx`** — Live Trace Viewer:
```typescript
// Connect to /api/events via EventSource.
// Render a live scrolling table:
//   columns: time | agent | event_type | policy_state | consequence_summary | wealth_impact
// Style: dark background #0d0d0d, monospace font, accent #00ff9d for APPROVED events.
// Auto-scroll to latest. Sliding window: max 200 rows in DOM.
```

**`lens/app/wealth/page.tsx`** — Wealth Dashboard:
```typescript
// Subscribe to /api/events.
// Running totals updated live: projected_wealth | realized_wealth | total_cost_tokens | total_cost_dollars
```

**`lens/app/api/memory/route.ts`** + **`lens/app/memory/page.tsx`** — Memory Browser:
```typescript
// Route: read .aegis/memory.db via better-sqlite3, return rows as JSON.
// Page: display rows in a table (trace_id | topic | content preview).
//       Client-side topic filter.
```

**`lens/app/status/page.tsx`** — Agent Status:
```typescript
// Show last-seen time per agent derived from the event log.
// Green dot: seen within 60s. Yellow: 60–300s. Red: >300s or never seen.
```

---

### FIX 7 — `kernel/memory.py` — add full-text search

**Current state:** `query()` only does exact-match on topic and trace_id.

**Add:**

```python
def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Keyword search across topic and content columns.
    Uses SQLite LIKE by default.
    When Letta client is active, delegates to Letta semantic search instead.
    """
```

---

### FIX 8 — `tests/` — add real coverage

**Current state:** Tests exist but assert trivial or hardcoded values.

**Add these test cases:**

`tests/test_forge.py`:
- A `"code"` task type with an output_path causes Forge to write a file to that path.
- A policy-rejected event prevents execution and no file is written.
- `forge_log.jsonl` is written with the correct fields after execution.

`tests/test_loop.py`:
- A HUMAN_INTENT event causes a new entry in `backlog.jsonl` with status `"pending"`.
- A duplicate intent with the same key is not enqueued a second time.
- A task that fails three times is marked `"failed"` in backlog.jsonl.

`tests/test_run.py`:
- A missing CRITICAL dependency causes `run.py` to exit(1) before starting agents.
- All 5 agents are instantiated during a normal startup sequence.
- Sending SIGINT produces no errors and flushes the bus.

---

## ACCEPTANCE CRITERIA

All of the following commands must succeed before the build is considered done:

```bash
# 1. Kernel health check
python -m kernel.introspect doctor

# 2. Full demo trace
python -m kernel.introspect demo-flow

# 3. Test suite
pytest -q

# 4. Entrypoint starts cleanly
timeout 5 python run.py || true

# 5. Forge executes a document task
python -c "
from kernel.events import AegisEvent, EventType, Cost, PolicyState, WealthImpact, now_utc
from agents.forge.agent import ForgeAgent
e = AegisEvent(
  trace_id='test_forge_001',
  event_type=EventType.AGENT_EXECUTE,
  ts=now_utc(), agent='loop', intent_ref='test',
  cost=Cost(tokens=10, dollars=0.001),
  consequence_summary='write test doc',
  wealth_impact=WealthImpact(type='neutral', value=0.0),
  policy_state=PolicyState.APPROVED,
  payload={'task_type': 'document', 'spec': 'hello from forge', 'output_path': '/tmp/forge_test.txt'}
)
result = ForgeAgent().on_wake(e)
print('forge ok:', result.summary)
"

# 6. Loop enqueues an intent
python -c "
from kernel.events import AegisEvent, EventType, Cost, PolicyState, WealthImpact, now_utc
from agents.loop.agent import LoopAgent
e = AegisEvent(
  trace_id='test_loop_001',
  event_type=EventType.HUMAN_INTENT,
  ts=now_utc(), agent='user', intent_ref='test',
  cost=Cost(tokens=0, dollars=0.0),
  consequence_summary='hello world request',
  wealth_impact=WealthImpact(type='neutral', value=0.0),
  policy_state=PolicyState.APPROVED,
  payload={'intent': 'write a hello world python script', 'urgency': 4, 'impact': 3, 'feasibility': 5}
)
result = LoopAgent().on_wake(e)
print('loop ok:', result.summary)
"

# 7. Lens starts
cd lens && npm run build
```

---

## COMMIT STRATEGY

One commit per fix, in this order:

```
fix: forge agent — real artifact execution with policy gate and Aider fallback
fix: loop agent — backlog scoring, sequencing, retry logic
fix: scheduler — async tick loop
feat: run.py — AEGIS system entrypoint with graceful shutdown
fix: herald — complete Telegram bridge with session continuity
feat: lens — live SSE trace viewer, wealth dashboard, memory browser, agent status
fix: memory — full-text keyword search
fix: tests — forge, loop, run coverage
```

---

## DONE CONDITION

The build is complete when all seven conditions are true:

1. `python -m kernel.introspect doctor` — all checks green
2. `pytest -q` — all pass, or every failure documented in `FAILURES.md`
3. `timeout 5 python run.py` — starts cleanly, no import or startup errors
4. Forge writes an artifact file from an `AGENT_EXECUTE` event
5. Loop writes a backlog entry from a `HUMAN_INTENT` event
6. `cd lens && npm run build` — exits 0
7. No hardcoded secrets anywhere in the codebase
