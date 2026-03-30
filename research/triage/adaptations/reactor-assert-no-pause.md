# reactor.py — Restore assert_no_pause Context Manager

## Tier
Drop

## Fork Change Summary
The fork removed the `assert_no_pause` context manager from `klippy/reactor.py`.
In the fork, this method is simply absent. The removal occurred because the
upstream `MotionQueuing` subsystem (which is the primary caller of
`assert_no_pause`) was also removed from the fork (see Adapt item B3 —
`toolhead.py`). Without `MotionQueuing`, the context manager has no callers
inside the fork's Klipper core, so it was dropped.

The change is a passive removal caused by snapshot divergence, not a deliberate
architectural decision.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) retains `assert_no_pause` in
`klippy/reactor.py` at line 271:

```python
def assert_no_pause(self):
    if self._pending_notifies:
        raise ReactorError("assert_no_pause failed")
```

It is used by `klippy/extras/motion_queuing.py` and protects against scheduling
a paused callback during motion. Restoring it to the fork is a no-op unless
`MotionQueuing` is also restored (Adapt item B3).

## Migration Path

1. **Copy the `assert_no_pause` method** from upstream `klippy/reactor.py` (line 271) back into the fork's `klippy/reactor.py`.
2. **No callers exist in the current fork** — the method will be dormant until `MotionQueuing` (C32) is restored.
3. **Testing checkpoint:** Run the fork's existing reactor test (if any) and verify no `AttributeError` on startup. Confirm that all existing G-code command paths still work.

### klipper-router / Extended Firmware overlay implications
None — `reactor.py` is a core file with no overlay implications.

## Risk
**Low.** Adding a dormant method with no callers introduces zero behavioural
change. The only risk is a name collision if the fork has added a different
`assert_no_pause` implementation — check the fork's `reactor.py` for any
existing method by that name before applying.
