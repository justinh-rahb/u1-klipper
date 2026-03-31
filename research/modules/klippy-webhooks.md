# webhooks.py

## Summary
`webhooks.py` implements the Unix socket server that connects klippy to Moonraker. The fork's changes: (1) remove the optional `msgspec` fast JSON encoder/decoder in favour of always using the standard `json` module; (2) replace the `klippy:analyze_shutdown` event subscription with a simpler `klippy:shutdown` handler; (3) integrate the structured exception system (on API errors, extract the coded message field and call `printer.raise_coded_exception`); (4) add `has_remote_method(method)` for probing Moonraker capability; (5) remove the `reactor.assert_no_pause()` wrapper from the status-subscription dispatch loop.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Tries to `import msgspec` for fast JSON; falls back to `json` | Always uses `import json`; `msgspec` import removed | Simplification; `msgspec` not available on Snapmaker SoC |
| `WebhookServer` subscribes to `klippy:analyze_shutdown` → `_handle_analyze_shutdown(msg, details)` | Subscribes to `klippy:shutdown` → `_handle_shutdown()` (no arguments) | `analyze_shutdown` event removed from klippy.py |
| `_handle_analyze_shutdown` logs and sets shutdown message | `_handle_shutdown` performs the same function without `msg`/`details` args | Matches simplified event |
| API request error: `web_request.set_error(WebRequestError(str(e)))` | Also calls `printer.extract_coded_message_field(str(e))` and `printer.raise_coded_exception(e)` for non-`gcode/script` methods | Routes API errors to exception bus |
| Status subscription loop runs inside `reactor.assert_no_pause()` | `assert_no_pause()` removed; loop runs unguarded | `assert_no_pause()` removed from the fork's reactor |
| `send_buffer` built with `json_dumps(data) + b"\x03"` | Built with `json.dumps(data, ...).encode() + b"\x03"` | No `msgspec` |
| `json.loads(request, object_hook=json_loads_byteify)` | Same, but `json_loads_byteify` only defined for Python 2 (dead code in Python 3) | Python 2 compatibility code retained but irrelevant |

## Additions
- `WebhookServer.has_remote_method(method)` → `bool` — checks if `method` is registered in `_remote_methods`. Used by `ExceptionManager` to gate exception forwarding.
- `ClientConnection.exception_manager` attribute set to `self.printer.lookup_object('exception_manager', None)` in `_handle_ready`.

## Removals / Overrides
- `msgspec` optional import and `json_dumps`/`json_loads` wrappers removed.
- `klippy:analyze_shutdown` event handler registration removed.
- `reactor.assert_no_pause()` context removed from `_handle_subscriptions`.

## Risks / Compatibility Notes
- Removing `msgspec` reduces JSON serialisation throughput. On a heavily subscribed status feed, this could increase CPU load on the SoC.
- `raise_coded_exception` is called for every non-`gcode/script` API error, including benign user errors. This may generate spurious entries in the exception log.
- `_handle_shutdown` no longer receives the shutdown message or details dict; if these were needed for UI error display, that information is now only available via the coded exception system.
- The `json_loads_byteify` Python 2 compatibility code is still present but never executed under Python 3.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/webhooks.py
+++ b/klippy/webhooks.py
@@ -9,30 +8 @@
-try:
-    import msgspec
-    json_dumps = msgspec.json.encode
-    json_loads = msgspec.json.decode
-except ImportError:
-    import json
-    ...
+import logging, socket, os, sys, errno, json, collections

@@ -139 +127 @@
-    "klippy:analyze_shutdown", self._handle_analyze_shutdown)
+    "klippy:shutdown", self._handle_shutdown)

 # _handle_analyze_shutdown(msg, details) -> _handle_shutdown()
 # API error path: extract_coded_message_field + raise_coded_exception
 # has_remote_method(method) added
 # assert_no_pause() removed from _handle_subscriptions
```

</details>
