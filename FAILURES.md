# Failures / Remaining Gaps

## Lens runtime unavailable in this environment

- **Condition impacted:**
  - Done condition #2 (Lens URL print is gated on uvicorn availability)
  - Done condition #3 (`http://localhost:7771` accessibility)
- **Observed behavior:** `run.py` prints `Lens unavailable — run: pip install uvicorn fastapi` and continues headlessly.
- **Reason:** `uvicorn` is not installed in the execution environment.
- **Minimum additional work to close:**
  1. Install dependencies: `pip install uvicorn fastapi`
  2. Re-run `python run.py` and verify `AEGIS Lens running → http://localhost:7771`.
  3. Confirm `curl http://localhost:7771/api/health` returns HTTP 200.

## Expansion gaps not fully completed in this pass

- Lens dashboard complete rework to six routes and new SSE/API contracts was not fully implemented yet.
- MCP host is currently scaffolded with discoverable placeholder tools; full runtime tool forwarding via mcp SDK is pending.
- Real hardware-dependent acceptance tests (voice, WiFi, Bluetooth, USB, OCR) were not verifiable in this environment.
