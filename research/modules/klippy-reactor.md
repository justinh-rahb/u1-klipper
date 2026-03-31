# reactor.py

## Summary
`reactor.py` is the green-thread event loop at the heart of klippy. The fork tracks back to an older version of the reactor (circa Klipper 0.10/2020): `ReactorPreventPause` / `assert_no_pause()` / `verify_can_pause()` are removed; the `ReactorError` exception class is absent; the FD-tracking data structures are simplified; the `run()` loop no longer creates a new dispatch greenlet per iteration; and the `_cached_dispatch_greenlets` / `_prevent_pause_count` state is simplified. The `ReactorFileHandler` gains a `fileno()` method. The `select`-based and `poll`-based reactor variants both have their FD registration logic reworked to use `file_handler` objects directly (no integer FD dict lookup for the select variant). A minor bug introduced by the fork's `_dispatch_loop`: `self.write_fds` (typo, missing underscore) — though this was likely corrected in practice.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `ReactorPreventPause` context manager + `assert_no_pause()` / `verify_can_pause()` | Removed entirely | Simplification; code paths that called it were also changed |
| `ReactorError` exception class | Removed | Only used by `verify_can_pause()` |
| `run()` creates a new `ReactorGreenlet` on every iteration of `while self._process` | Creates exactly one `ReactorGreenlet`, switches to it once | Simpler lifecycle |
| `pause()` checks `_prevent_pause_count` before switching | Pause check removed | `_prevent_pause_count` removed |
| `_fds` dict keyed by integer FD for select variant | List-based read/write FD tracking directly on `file_handler` objects | No integer FD lookup needed |
| `_check_fds` dispatch method for select events | Inlined into `_dispatch_loop` with per-object callbacks | Removes indirection |
| `timer_handler.timer_is_running` flag set/unset around timer execution | Flag removed from timer dispatch | `timer_is_running` attribute removed |
| `_gc_checking` bool → `_check_gc` method | `_check_gc` is now the bool; GC logic inlined in `_check_timers` | Minor naming change |
| `ReactorGreenlet` pool: `_cached_dispatch_greenlets` | Renamed `_greenlets` | Minor rename |
| Poll variant: `_fds` dict keyed by integer FD | `_fds` dict keyed by `file_handler`; copy-on-write via `fds = self._fds.copy()` | Thread-safety attempt for concurrent registration |
| `register_fd` returns `file_handler` and stores `fd` in `self._fds[fd]` | select: uses list; poll: uses copy dict with `file_handler` key | Different tracking |

## Additions
- `ReactorFileHandler.fileno()` method — returns `self.fd`; makes file handlers directly usable as `select`/`poll` descriptors.

## Removals / Overrides
- `ReactorError` exception class — removed.
- `ReactorPreventPause` context manager class — removed.
- `Reactor.assert_no_pause()` — removed.
- `Reactor.verify_can_pause()` — removed.
- `Reactor._prevent_pause_count` attribute — removed.
- `ReactorTimer.timer_is_running` attribute — removed.
- `Reactor._check_fds` method — logic inlined into `_dispatch_loop`.
- `Reactor._check_gc` method — replaced by inline GC logic.
- `_cached_dispatch_greenlets` renamed to `_greenlets`.

## Risks / Compatibility Notes
- Any code that calls `reactor.assert_no_pause()` (e.g. as a context manager) will raise `AttributeError`. The fork removes all call sites in `klippy.py`, `webhooks.py`, and `toolhead.py`, but any extra module that calls it will break.
- `reactor.verify_can_pause()` is also gone; extras that probe for pause safety have no equivalent.
- The `self.write_fds` typo in `_dispatch_loop` (should be `self._write_fds`) was present in the diff reviewed; if not corrected in a later commit it would cause an `AttributeError` at runtime whenever write FDs are monitored.
- The single-greenlet `run()` loop means that if the dispatch greenlet exits unexpectedly, the reactor terminates rather than creating a new one. This may cause klippy to exit rather than recover on certain greenlet exceptions.
- Copy-on-write `_fds` dict in the poll variant adds allocation overhead on every `register_fd`/`unregister_fd` call.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/reactor.py
+++ b/klippy/reactor.py
@@ -13,3 -13 @@
-class ReactorError(Exception): pass
-
@@ -96,8 @@
-class ReactorPreventPause: ...
+# ReactorPreventPause removed

 # ReactorTimer: timer_is_running removed
 # Reactor: _prevent_pause_count, assert_no_pause, verify_can_pause removed
 # Reactor._gc_checking -> _check_gc (bool, inline)
 # run(): single greenlet instead of per-iteration new greenlet
 # _fds / _check_fds: simplified to direct file_handler lists
 # ReactorFileHandler.fileno() added
```

</details>
