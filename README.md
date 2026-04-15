# AEGIS

AEGIS is a persistent agentic operating system with five standing agents:
herald → warden → loop → forge → scribe.

## Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env
python chat.py
```

## Components

- `kernel/core`: event model, bus, memory, policy, providers, tools.
- `agents/*`: standing agents.
- `kernel/orchestrator.py`: end-to-end intent execution.
- `lens/server.py`: FastAPI control/observability API.
