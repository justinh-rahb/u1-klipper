# buttons.py — Restore DebounceButton Class

## Tier
Drop

## Fork Change Summary
The fork removed the `DebounceButton` class from `klippy/extras/buttons.py`.
`DebounceButton` was added to upstream Klipper after the fork's divergence point
and was never merged into the fork. No U1 config or module uses `DebounceButton`,
so its absence is silent.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) includes `DebounceButton` in
`klippy/extras/buttons.py`. It wraps a GPIO-backed button with software
debouncing using a configurable debounce time, preventing spurious triggers on
noisy button lines.

Upstream reference: `klippy/extras/buttons.py` at commit `2f05309d`.

## Migration Path

1. **Copy the `DebounceButton` class** from upstream `klippy/extras/buttons.py` into the fork's `buttons.py`.
2. **Check for API dependencies:** `DebounceButton` uses only standard `buttons.py` internals and `reactor` callbacks — no dependency on `MotionQueuing`, `steppersync`, or other removed subsystems.
3. **Testing checkpoint:** Verify that all existing U1 button-triggered macros (e.g., filament run-out detection that uses `[buttons]`) continue to work. No functional change expected — `DebounceButton` is additive.

### Config implications
None. No U1 config uses `[buttons] debounce_time`. Adding `DebounceButton` is
purely additive — existing button configs are unaffected.

### klipper-router / Extended Firmware overlay implications
None — `buttons.py` is not part of the overlay.

## Risk
**Low.** Additive class restoration with no existing callers in the fork.
Only risk is an import error if `DebounceButton`'s upstream implementation
references a module not present in the fork (e.g., `bulk_sensor`). Inspect the
upstream implementation: current `DebounceButton` has no such dependency.
