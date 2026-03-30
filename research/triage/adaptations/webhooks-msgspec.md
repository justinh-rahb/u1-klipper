# webhooks.py — Adopt msgspec for JSON Serialisation

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/webhooks.py` removes the optional `msgspec` import that
upstream uses for faster JSON serialisation/deserialisation:

```python
# Upstream (removed by fork):
try:
    import msgspec
    json_dumps = msgspec.json.encode
    json_loads = msgspec.json.decode
except ImportError:
    import json
    json_dumps = json.dumps
    json_loads = json.loads
```

The fork uses plain `json` module directly. This was done because `msgspec` was
not available in the U1's AArch64 Python environment at the time of the fork.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) uses `msgspec` with a graceful `ImportError`
fallback to `json`. Because the import is guarded by `try/except`, **the upstream
version already handles the case where `msgspec` is not installed** — it
silently falls back to plain `json`. This means the upstream version is
behaviorally identical to the fork's version when `msgspec` is absent.

Upstream reference: `klippy/webhooks.py` lines 10, 36–37 at commit `2f05309d`.

## Migration Path

1. **Replace** the fork's direct `import json` + `json.dumps`/`json.loads` usage
   in `webhooks.py` with the upstream try/except pattern:
   ```python
   try:
       import msgspec
       json_dumps = msgspec.json.encode
       json_loads = msgspec.json.decode
   except ImportError:
       import json
       def json_dumps(obj):
           return json.dumps(obj).encode()
       json_loads = json.loads
   ```
   Note: `msgspec.json.encode` returns `bytes`, `json.dumps` returns `str` —
   ensure the fallback is byte-compatible if the rest of `webhooks.py` expects bytes.
2. **Verify compatibility** with the fork's other `webhooks.py` changes (if any
   beyond this single change).
3. **Optionally install `msgspec`**: Add `msgspec` to `klippy/klippy-requirements.txt`
   for AArch64 builds to get the performance benefit. Confirm a pre-built
   `msgspec` wheel is available for the U1's Python version on AArch64.
4. **Testing checkpoint:** Start Klipper and send a Moonraker API request.
   Verify the JSON response is correctly serialised. Check that `msgspec` import
   success/failure is logged at startup if the fork's other logging is preserved.

### Config implications
None.

### klipper-router / Extended Firmware overlay implications
If the overlay bundles a `klippy-requirements.txt`, add `msgspec` optionally.

## Risk
**Low.** The upstream code already handles `msgspec` absence gracefully. The
only risk is a subtle bytes/str encoding difference between `msgspec.json.encode`
(returns `bytes`) and `json.dumps` (returns `str`) in the fallback path. Review
all downstream consumers of `json_dumps` in `webhooks.py` to confirm they handle
both types (or add `.encode()` to the fallback).
