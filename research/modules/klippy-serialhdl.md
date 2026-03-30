# serialhdl.py

## Summary
`serialhdl.py` manages the low-level serial/CAN communication with MCUs. The fork's changes focus on two areas: (1) the `SerialReader` constructor is redesigned to accept a `mcu` back-reference instead of deriving state from `mcu_name`, enabling richer error reporting; (2) the "Timer too close" and "Power loss info saved" MCU notification messages are intercepted in `_handle_unexpected_error` to translate them into structured exception codes and log system-time estimates alongside the raw clock values.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `SerialReader.__init__(reactor, mcu_name="")` — name string | `SerialReader.__init__(reactor, warn_prefix="", mcu=None)` — explicit `mcu` object reference | Enables back-references to `mcu.estimate_clock_systime()` and `mcu.clock32_to_clock64()` |
| `warn_prefix` computed from `mcu_name` inside `__init__` | `warn_prefix` passed directly as parameter | Caller responsibility |
| `sq_name` (thread name) derived from `mcu_name` and passed to `serialqueue_alloc` | `sq_name` removed; `serialqueue_alloc` called without it | Matching older FFI signature |
| Debug log for sent messages: `"Sent %d %f %f %d: %s"` (receive_time, sent_time, len) | `"Sent %d %f %f min_t=%f req_t=%f %d: %s"` — adds system-time estimates for `min_clock` and `req_clock` | Aids diagnosis of "Timer too close" errors |
| `_handle_unexpected_error` handles MCU `output` messages generically | Additional logic: if message starts with `"Timer too close: "`, parses `waketime` and `timer_read_time`, converts to system time, logs them | Translates MCU clock ticks to wall-clock times |
| No "Power loss info saved" intercept | If `msg == "Power loss info saved"`, raises a coded exception `"0003-0522-{mcu_index}-0017"` | Routes power-loss notification through exception bus |
| `CommandQueryWrapper.get_response(..., retry=True)` — optional retry | `retry` parameter removed; always retries | Consistent with mcu.py change |

## Additions
- `clock_to_systime(clock)` local function inside `_log_sequence` — converts a 64-bit MCU clock to estimated system time using `self._mcu.estimate_clock_systime(clock)`.
- `_handle_unexpected_error`: "Timer too close" parsing block — extracts `waketime` and `timer_read_time` from the message, converts to 64-bit clocks via `mcu.clock32_to_clock64`, then to system times, and logs them.
- `_handle_unexpected_error`: "Power loss info saved" intercept — maps `mcu._name` to a 0–4 index and raises coded exception `"0003-0522-{index}-0017"` via `mcu.get_printer().raise_structured_code_exception(...)`.

## Removals / Overrides
- `mcu_name` constructor parameter — replaced by `warn_prefix` + `mcu`.
- `sq_name` internal attribute and its use in `serialqueue_alloc` calls — removed.
- Thread naming via `self.ffi_lib.set_thread_name(name_short.encode())` removed.
- `get_response(..., retry=True)` `retry` parameter removed.

## Risks / Compatibility Notes
- Any caller that previously passed `mcu_name=` as a keyword argument to `SerialReader.__init__` will raise `TypeError`. The only caller is `MCU.__init__` in `mcu.py`, which was updated accordingly.
- The "Timer too close" parser uses `dict(item.split('=', 1) for item in content.split(','))` — any variation in the MCU's message format (e.g. extra spaces) will silently skip the enriched log.
- The "Power loss info saved" coded exception uses a hardcoded dict `{'mcu': 0, 'e0': 1, 'e1': 2, 'e2': 3, 'e3': 4}` to map MCU name to index. MCUs with names outside this set get `mcu_index=255`, which produces code `"0003-0522-0255-0017"`.
- Removing `sq_name` from `serialqueue_alloc` requires matching C-side FFI (`serialqueue_alloc` must no longer expect a name argument).

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/serialhdl.py
+++ b/klippy/serialhdl.py
@@ -15 +15 @@
-    def __init__(self, reactor, mcu_name=""):
+    def __init__(self, reactor, warn_prefix="", mcu=None):

 # sq_name derived and passed to serialqueue_alloc removed
 # _log_sequence: min_t/req_t system-time added to "Sent" line
 # _handle_unexpected_error:
 #   "Timer too close:" -> parse + log system times
 #   "Power loss info saved" -> raise coded exception 0003-0522-N-0017
 # get_response: retry param removed
```

</details>
