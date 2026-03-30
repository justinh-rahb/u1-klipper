# queuefile.py

## Summary
A fork-exclusive module that provides a thread-safe, background-queue-based file I/O system for the klippy host process. All file writes, appends, and deletes are off-loaded to a single daemon thread (`QueueListener._bg_thread`) so that the reactor event loop is never blocked by disk I/O. The module supports both fire-and-forget async operations and synchronised blocking calls that integrate with the klippy reactor's `pause()` mechanism. Safe atomic writes use a `.tmp` rename pattern. The module is set up once in `klippy.py`'s `main()` via `setup_bg_file_operations()` and torn down via `clear_bg_file_operations()`. It is used extensively by `exception_manager.py` and indirectly by `klippy.py`'s `update_snapmaker_config_file()` to write JSON config and exception state.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| N/A — upstream does all file I/O synchronously on calling threads | Background thread with a `queue.Queue(maxsize=1000)` decouples file I/O from the reactor | Prevents disk latency from stalling the real-time print loop |
| N/A | Atomic safe-write via write-to-`.tmp` then `os.replace()` | Ensures config/exception files are never left in a half-written state on power loss |

## Additions
- `FileOperation` dataclass — encapsulates a single pending file operation (`op_type`, `filename`, `content`, `flush`, `sync`, `timeout`, `safe_write`, `timestamp`, `future`).
- `FileOperationException` / `FileOperationTimeout` — custom exception types.
- `QueueHandler` — puts `FileOperation` objects onto `bg_queue`; raises `FileOperationException` if the queue is full:
  - `write_file(filename, content, flush, safe_write)`
  - `delete_file(filename)`
  - `append_file(filename, content, flush, safe_write)`
- `QueueListener` — owns the background thread and queue:
  - `_bg_thread()` — consumer loop; processes operations in order.
  - `_process_operation(op)` — dispatches to write / delete / append logic; handles `.tmp` safe-write and directory creation.
  - `stop()` — sends `None` sentinel to terminate the background thread.
- Module-level singleton API:
  - `setup_bg_file_operations()` → `QueueListener` (creates singleton `MainQueueHandler`).
  - `clear_bg_file_operations()` — stops and destroys the singleton.
  - `async_write_file(filename, content, flush, safe_write)` — non-blocking write.
  - `async_delete_file(filename)` — non-blocking delete.
  - `async_append_file(filename, content, flush, safe_write)` — non-blocking append.
  - `sync_write_file(reactor, filename, content, flush, safe_write, timeout)` — blocking write; polls `op.future` via `reactor.pause()`.
  - `sync_delete_file(reactor, filename, timeout)` — blocking delete.
  - `sync_append_file(reactor, filename, content, flush, safe_write, timeout)` — blocking append.
- Constants: `QUEUE_SIZE=1000`, `QUEUE_TIMEOUT=1.0`, `DEFAULT_SYNC_TIMEOUT=30.0`.

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `sync_write_file` and friends spin-poll `op.future.done()` with 10 ms `reactor.pause()` sleeps. Under heavy scheduler load this can block for longer than the 30 s `DEFAULT_SYNC_TIMEOUT`.
- If `bg_queue` fills to 1000 entries (e.g. from exception spam), new write requests raise `FileOperationException` and are dropped silently at the caller.
- `_process_operation` catches all exceptions generically (`except Exception`) and only surfaces them if `op.sync` is `True`; async failures are swallowed.
- `os.fsync` calls are commented out in the safe-write path, so "safe" writes are only atomic against process crashes, not power loss.
- `concurrent.futures.Future` is used for synchronisation but `op.future.cancel()` is never called; stale futures from timed-out operations may hold references.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/klippy/queuefile.py
@@ -0,0 +1,~200 @@
+# New file – no upstream equivalent
+class FileOperation: ...
+class QueueHandler:
+    def write_file / delete_file / append_file: ...
+class QueueListener:
+    def _bg_thread(self): ...
+    def _process_operation(self, op): ...  # safe_write via .tmp + os.replace
+
+def async_write_file / async_delete_file / async_append_file: ...
+def sync_write_file / sync_delete_file / sync_append_file: ...
```

</details>
