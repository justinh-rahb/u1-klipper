# motion_queuing.py — Restore Upstream Module

## Tier
Adapt

## Fork Change Summary
The fork does not include `klippy/extras/motion_queuing.py`. This module was
added to upstream Klipper after the fork's divergence and provides the
`MotionQueuing` class that manages trapq, step generator registration, and
flush timer — functionality that in the fork is inlined directly into
`toolhead.py` (item B3).

Its absence is directly coupled to the toolhead architecture divergence.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides `klippy/extras/motion_queuing.py`
with the `MotionQueuing` class. Key responsibilities:
- Owns `trapq` allocation for a `ToolHead`
- Manages `kin_flush_times` and the background flush timer
- Provides `drip_update_time` for drip-mode pacing
- Registers/unregisters step generators

## Migration Path

This item is a dependency of the toolhead adaptation (B3). Restore it as part
of that migration:

1. **Copy `motion_queuing.py`** from upstream into the fork's `klippy/extras/`.
2. **Update `toolhead.py`** (Adapt B3 Phase 2) to instantiate `MotionQueuing`
   and delegate trapq/flush management to it.
3. **Update `output_pin.py`** (Adapt C8) — `GCodeRequestQueue` uses
   `motion_queuing` from the printer object.
4. **Testing checkpoint:** Verify that `MotionQueuing` is correctly loaded
   during startup and that no `KeyError` occurs when `toolhead` looks for it.

### Config implications
None.

### klipper-router / Extended Firmware overlay implications
None.

## Risk
**Medium** — coupled to toolhead refactor (B3). Do not restore in isolation;
restore as part of the toolhead adaptation sprint.
