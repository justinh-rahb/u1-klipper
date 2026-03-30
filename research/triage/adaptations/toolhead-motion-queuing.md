# toolhead.py — Migrate to minimum_cruise_ratio + MotionQueuing

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/toolhead.py` represents the single largest architectural
divergence from current upstream. It reverts two major upstream refactors:

1. **Look-ahead velocity smoothing algorithm**: The fork uses the older
   `max_smoothed_v2` / `smooth_delta_v2` algorithm (controlled by
   `max_accel_to_decel` config key). Upstream replaced this with the
   `minimum_cruise_ratio` / `mcr_pseudo_accel` algorithm, which provides
   better control over minimum cruise speed on short segments.

2. **`MotionQueuing` architecture**: Upstream extracted trapq management,
   flush timer, and step generator registration into a `MotionQueuing` helper
   class (and the corresponding `klippy/extras/motion_queuing.py`). The fork
   retains these directly in `ToolHead`, tightly coupled.

On top of these reversions, the fork adds genuine U1-specific features that must
be preserved:
- `max_logical_extruder_num` / `max_physical_extruder_num` config keys
- `SWITCH_OF_EXTENDED_EXTRUDER` G-code for virtual extruder activation
- `SET_MAX_Z_ACCEL` / `SET_MAX_Z_VELOCITY` G-codes
- Coded error messages for "Must home axis" and "Move out of range" (exception system)
- `Move.line` field for PLR print-line stamping
- `ToolHead.is_calibrating_flow` flag + `flow_calibration` events
- `ToolHead.print_file_line` attribute
- `ToolHead.is_grab_complete` flag + `_extruder_auto_activate()`
- `DripModeEndSignal` exception + `_update_drip_move_time()`

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides:
- `klippy/toolhead.py` with `minimum_cruise_ratio` velocity smoothing
- `klippy/extras/motion_queuing.py` — `MotionQueuing` class
- `LookAheadQueue` that returns a move list for `MotionQueuing` to process
- `ToolHead.extra_axes` list for multi-axis support

The `minimum_cruise_ratio` algorithm is strictly better: it directly specifies
the minimum fraction of time a move spends at cruise speed, avoiding the
confusing `max_accel_to_decel` proxy. It is configured as:
```ini
[printer]
minimum_cruise_ratio: 0.5  # default; equivalent to old max_accel_to_decel = max_accel/2
```

Upstream also accepts `max_accel_to_decel` as a migration config key and
converts it to `minimum_cruise_ratio`, so existing configs migrate transparently.

## Migration Path

This is the most complex single migration in the triage. It should be done as a
dedicated sprint, coordinated with chelper steppersync (A1/A2/A3) and
kinematics Coord (E items).

### Phase 1 — Algorithm migration (lower risk)
1. **Adopt `minimum_cruise_ratio`**: Replace the `max_smoothed_v2`/`smooth_delta_v2`
   computation in `LookAheadQueue.flush()` with upstream's `mcr_pseudo_accel` /
   `next_junction_v2` logic. Keep the `max_accel_to_decel` migration shim.
2. **Add `minimum_cruise_ratio` config key** to `[printer]` parsing.
3. **Test**: Run U1 calibration prints at various speeds; compare output G-code
   quality to the older algorithm. Expected: slightly higher junction velocities
   on short moves.

### Phase 2 — MotionQueuing architecture (higher risk)
4. **Restore `motion_queuing.py`** from upstream (see item C32).
5. **Refactor `ToolHead`** to delegate trapq, flush timer, and step generator
   management to a `MotionQueuing` instance. Follow the upstream pattern:
   - `ToolHead.__init__` creates `MotionQueuing`; keeps `self.motion_queuing`
   - `LookAheadQueue.flush()` returns move list; `MotionQueuing` calls `_process_moves()`
   - Flush timer, `SDS_CHECK_TIME`, `BGFLUSH_*` constants move into `MotionQueuing`
6. **Preserve U1 additions** as layers on top:
   - `Move.line` field — add to `Move.__init__` after upstream base is in place
   - Coded error messages — replace upstream's plain strings in `Move.move_error()`
   - `is_calibrating_flow` / `flow_calibration` events — add as new U1-specific callbacks
   - `max_logical/physical_extruder_num` — add config keys
   - `SWITCH_OF_EXTENDED_EXTRUDER`, `SET_MAX_Z_ACCEL`, `SET_MAX_Z_VELOCITY` — register as additional G-code commands
   - `_extruder_auto_activate()` — restore as a `klippy:ready` handler
   - `DripModeEndSignal` — keep fork's self-contained drip mode or migrate to upstream's `motion_queuing.drip_update_time` pattern

### Phase 3 — extra_axes (optional, low priority)
7. **Decide on `extra_axes`**: Upstream supports multiple extra axes beyond a
   single extruder. The U1 has 4 physical extruders but uses a T0–T3 tool-change
   protocol rather than simultaneous multi-axis motion. The `extra_axes` list
   approach may not add value for U1. **Recommendation:** Skip `extra_axes`
   restoration for now (Tier 3 decision); keep `self.extruder` single reference.

### Testing checkpoints
- `G28` + short print: verify no assertion errors, motion is smooth
- Multi-extruder tool change (T0→T1→T2→T3): confirm `SWITCH_OF_EXTENDED_EXTRUDER` works
- Flow calibration: confirm `is_calibrating_flow` suppresses junction smoothing
- PLR restore (`SDCARD_PRINT_PL_RESTORE`): confirm `Move.line` field passes through
- `SET_MAX_Z_ACCEL`, `SET_MAX_Z_VELOCITY` runtime commands work

### Config implications
- `lava/printer.cfg`: Replace `max_accel_to_decel:` with `minimum_cruise_ratio:` (or keep both — upstream accepts both via migration shim).
- No other config changes required.

### klipper-router / Extended Firmware overlay implications
`MotionQueuing` must be present in the overlay if the overlay imports toolhead
or relies on motion timing. The overlay `printer.cfg` `[printer]` section should
be updated to use `minimum_cruise_ratio`.

## Risk
**High.** `toolhead.py` is the heart of the motion system. Regression here
produces incorrect prints or MCU crashes. The `MotionQueuing` refactor
(Phase 2) is the highest-risk step; Phase 1 (algorithm only) can be done
independently at lower risk. Recommend completing Phase 1 before Phase 2, with
separate testing cycles. The U1's PLR `Move.line` field must survive the
refactor — this is the most likely item to be accidentally dropped.
