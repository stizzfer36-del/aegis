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
