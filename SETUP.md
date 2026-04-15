# AEGIS Setup Guide (Single Device)

This guide takes you from zero to `aegis doctor` on one machine (Linux VPS, macOS, Windows WSL, or Android Termux).

## What you need

- Git
- Python 3.11+
- Docker + Docker Compose
- 2GB RAM minimum (Oracle Free Tier ARM works)
- A terminal

## Step 1 — Clone

```bash
git clone https://github.com/stizzfer36-del/aegis.git
cd aegis
```

## Step 2 — Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Mac/Linux/WSL
# .venv\Scripts\activate         # Windows native
pip install -e ".[dev]"
```

## Step 3 — Config

```bash
cp config/aegis.toml config/aegis.local.toml
```

Open `config/aegis.local.toml` and fill in:
- `OPENROUTER_API_KEY` — get free at openrouter.ai
- `TELEGRAM_BOT_TOKEN` — get from @BotFather on Telegram (optional for v1)
- Leave everything else as-is for local dev

> Note: the current checked-in config references `OPENAI_API_KEY` and `TELEGRAM_BOT_TOKEN` as environment variables. If you use OpenRouter, export `OPENAI_API_KEY` with your OpenRouter-compatible key in your shell before running AEGIS.

## Step 4 — Start services

```bash
docker-compose up -d
```

Wait 30 seconds for all services to become healthy. Check with:

```bash
docker-compose ps
```

All services should show `healthy` or `running`.

## Step 5 — Verify

```bash
python -m kernel.introspect doctor
```

Expected output: all checks green, no critical failures.

## Step 6 — Run a demo flow

```bash
python -m kernel.introspect demo-flow
```

This sends one synthetic intent through the full kernel pipeline and prints the trace.

## Step 7 — Telegram (optional)

Set `TELEGRAM_BOT_TOKEN` in your config, then:

```bash
python -m agents.herald.agent
```

Message your bot on Telegram. It will respond through the same session as your terminal.

## Step 8 — Lens dashboard (optional)

```bash
cd lens
npm install
npm run dev
```

Open http://localhost:3000 — you will see live trace data, agent status, and the wealth dashboard.

## Termux (Android) setup

```bash
pkg install python git docker
pip install -e ".[dev]"
python -m kernel.introspect doctor
```

Note: Docker is not available on all Android builds. Run the kernel and agents directly without `docker-compose` on Termux. Services like NATS can be replaced with the in-process fallback bus already built into `kernel/bus.py`.

## Troubleshooting

**doctor shows NATS unreachable** — run `docker-compose up -d` and wait 30 seconds.

**pip install fails** — make sure you are on Python 3.11+. Run `python3 --version` to check.

**Telegram bot not responding** — confirm `TELEGRAM_BOT_TOKEN` is set and the herald agent process is running.

**Port 3000 in use** — run `PORT=3001 npm run dev` in the lens folder.
