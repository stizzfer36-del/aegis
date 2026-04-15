# AEGIS v2

**Autonomous Evolving General Intelligence System**

---

## Structure

```
aegis/
├── core/           # Kernel: events, bus, memory, policy, router, scheduler, anomaly
├── agents/         # 5 agents: warden, scribe, forge, loop, herald
├── topics/         # 30 open-source integration domains
├── interface/      # Lens dashboard (FastAPI)
├── infra/          # Docker, env, Dockerfile
├── tests/          # Pytest test suite
└── run.py          # Single entrypoint
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/stizzfer36-del/aegis
cd aegis
git checkout restructure/v2  # or main after PR merge

# 2. Install
pip install -e .[full]
aider-install           # for code generation

# 3. Configure
cp infra/.env.example .env
# Edit .env — set OLLAMA_URL or OPENROUTER_API_KEY at minimum

# 4. Start infrastructure
cd infra && docker compose up -d   # starts NATS
cd ..

# 5. Run
python run.py
# Dashboard: http://localhost:7771
```

## Tests

```bash
pip install -e .[dev]
pytest tests/ -v
```

## 30 Topics

| # | Topic | Tools |
|---|-------|-------|
| 01 | Agent Orchestration | crewAI, AutoGen, LangGraph, agent-zero, SuperAGI |
| 02 | Local LLM | Ollama, llama.cpp, vLLM, GPT4All, Jan |
| 03 | Coding Agents | Aider, OpenHands, SWE-agent, OpenCode |
| 04 | Memory & Knowledge | mem0, Chroma, Weaviate, Letta, Zep |
| 05 | Surveillance & OSINT | theHarvester, Spiderfoot, Shodan, Recon-ng |
| 06 | Network Sniffing | Wireshark, Scapy, Zeek, Suricata, mitmproxy |
| 07 | Web Scraping | Playwright, Crawl4AI, Scrapy, Firecrawl |
| 08 | Workflow Automation | n8n, Temporal, Prefect, Airflow |
| 09 | Hardware & IoT | Home Assistant, ESPHome, Tasmota, Flipper Zero |
| 10 | SDR & Radio | rtl-sdr, dump1090, GNU Radio, SDRangel |
| 11 | Security & Pentest | Metasploit, Nuclei, Nmap, sqlmap |
| 12 | Data Pipeline | NATS, Kafka, Redpanda, Vector |
| 13 | Vector Search | Qdrant, Milvus, Faiss, LanceDB |
| 14 | Computer Vision | OpenCV, YOLO, SAM, DeepFace |
| 15 | Voice & Audio | Whisper, Coqui TTS, Silero VAD, RVC |
| 16 | Robotics | ROS2, MoveIt2, Gazebo, LeRobot |
| 17 | Crypto & Blockchain | web3.py, Foundry, CCXT, Hardhat |
| 18 | Sports Betting | The Odds API, PrizePicks, XGBoost |
| 19 | Finance & Trading | Alpaca, CCXT, Backtrader, vectorbt |
| 20 | DevOps & Infra | Docker, Kubernetes, Terraform, Ansible |
| 21 | Databases | PostgreSQL, DuckDB, Redis, ClickHouse |
| 22 | API Gateway | Kong, Traefik, Envoy, Caddy |
| 23 | NLP & Text | spaCy, Transformers, LlamaIndex |
| 24 | Image Generation | Stable Diffusion, ComfyUI, AUTOMATIC1111 |
| 25 | 3D Printing | OctoPrint, Klipper, Marlin, PrusaSlicer |
| 26 | Social Media | Mastodon.py, Tweepy, Telethon, PRAW |
| 27 | Gaming | Godot, Gymnasium, Stable Baselines3, mineflayer |
| 28 | Email & Comms | Apprise, python-telegram-bot, Matrix |
| 29 | Search & Indexing | MeiliSearch, Typesense, OpenSearch |
| 30 | Monitoring | Prometheus, Grafana, OpenTelemetry, Loki |

## Env Vars

See `infra/.env.example` for all environment variables.
