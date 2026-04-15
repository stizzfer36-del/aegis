# AEGIS

Implementation scaffold for the AEGIS kernel, core society agents, infrastructure, interfaces, Lens dashboard, and tests.

## Quick start

```bash
python -m pip install -e '.[dev]'
python -m kernel.introspect demo-flow
python -m kernel.introspect doctor
pytest -q
```

## ADS-B bootstrap flow (Lens)

AEGIS now exposes a hardware-aware bootstrap endpoint for Chromebook + RTL-SDR setups:

```bash
curl -X POST http://127.0.0.1:9000/api/setup/bootstrap -H 'content-type: application/json' -d '{"intent_key":"my-rig"}'
# returns needs_confirmation until you send CONFIRM
curl -X POST http://127.0.0.1:9000/api/setup/bootstrap -H 'content-type: application/json' -d '{"intent_key":"my-rig","confirm":"CONFIRM"}'
```

On first run it performs live detection for steps 1-4, pauses before destructive actions, and writes results into memory. Re-running the same `intent_key` rehydrates steps 1-4 from memory for sub-10 second startup behavior.
