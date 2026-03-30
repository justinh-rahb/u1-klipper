# toolhead.py

## Summary
`toolhead.py` implements the `ToolHead` class that manages the motion planner (look-ahead queue, trapezoid queue, step generation). The fork's changes are substantial and reflect an older Klipper architecture: the upstream's `MotionQueuing` helper class is not used; instead, `ToolHead` directly owns trapq, flush timer, step generators, and all MCU coordination. The look-ahead queue algorithm returns to the older `max_smoothed_v2`/`smooth_delta_v2` velocity smoothing approach (upstream replaced this with the `minimum_cruise_ratio` / `mcr_pseudo_accel` algorithm). The fork also adds U1-specific features: configurable `max_logical_extruder_num` / `max_physical_extruder_num`, flow-calibration mode that disables junction smoothing, `SWITCH_OF_EXTENDED_EXTRUDER` G-code command, new `SET_MAX_Z_ACCEL` and `SET_MAX_Z_VELOCITY` commands, coded error messages for "Must home axis" and "Move out of range" errors, and an auto-activate-extruder callback on `klippy:ready`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `ToolHead` uses `MotionQueuing` for trapq, step gen, flush | Directly owns `trapq`, `flush_timer`, `step_generators`, `kin_flush_times` | Older architecture; `MotionQueuing` not present in fork |
| `LookAheadQueue` flushes and returns move list for external processing | `LookAheadQueue` calls `toolhead._process_moves()` directly on flush | Tighter coupling; removes the intermediate list |
| `LookAheadQueue.is_empty()` method | Removed; callers use `not self.lookahead.queue` directly | Minor simplification |
| `minimum_cruise_ratio` / `mcr_pseudo_accel` velocity smoothing | `max_accel_to_decel` / `max_smoothed_v2` / `smooth_delta_v2` smoothing | Older algorithm; `minimum_cruise_ratio` config key still accepted via migration |
| `Move.next_junction_v2` + `limit_next_junction_speed()` | Removed; replaced by `max_smoothed_v2` | Corresponds to the look-ahead algorithm reversion |
| `Move.calc_junction` uses multiple extra-axis results | Uses single `extruder.calc_junction` result | `extra_axes` list removed; single extruder only |
| `ToolHead.extra_axes` list supports multiple extra axes | `self.extruder` single reference; `add_extra_axis`, `remove_extra_axis`, `get_extra_axes` removed | Single-extruder simplification |
| `ToolHeadCommandHelper` separate class registers G-code commands | Commands registered directly in `ToolHead.__init__` | Merged; `ToolHeadCommandHelper` class removed |
| `LOOKAHEAD_FLUSH_TIME = 0.150` | `LOOKAHEAD_FLUSH_TIME = 0.250` | Larger flush window for slower MCU comms |
| `BUFFER_TIME_HIGH = 1.0` | `BUFFER_TIME_LOW = 1.0`, `BUFFER_TIME_HIGH = 2.0` | Larger buffer for multi-MCU latency |
| Drip mode uses `motion_queuing.drip_update_time` | `DripModeEndSignal` exception + `_update_drip_move_time` loop | Self-contained drip mode without `MotionQueuing` |
| `set_max_velocities()` separate method | Logic inlined into `cmd_SET_VELOCITY_LIMIT` | Simplification |
| `M204` calls `toolhead.set_max_velocities(None, accel, ...)` | Directly sets `self.max_accel` and calls `_calc_junction_deviation()` | Removes indirection |
| `get_status()` returns `extra_axes` dict | Removed from status response | `extra_axes` concept removed |
| Default modules loaded by `load_printer_objects`: includes `garbage_collection` | `garbage_collection` removed; `machine_state_manager` added | U1-specific module; upstream GC module not used |

## Additions
- Config keys (new): `max_logical_extruder_num` (int), `max_physical_extruder_num` (int).
- `Move.line` field — stores the print file line number for each move; passed to firmware via `queue_step` command.
- Structured error dispatch in `Move.move_error()` for `"Must home X/Y/Z axis first"` (codes `0003-0522-{0..2}-0012`) and `"Move out of range on X/Y/Z axis"` (codes `0003-0522-{0..2}-0013`).
- `ToolHead.is_calibrating_flow` flag — set by `flow_calibration:begin` / `flow_calibration:end` events; disables junction smoothing during flow calibration.
- `ToolHead.print_file_line` attribute — current G-code line number, stamped onto each move.
- `ToolHead.is_grab_complete` flag — tracks whether extruder grab/activate sequence completed.
- `ToolHead._handle_ready()` / `_extruder_auto_activate()` — on `klippy:ready`, schedules extruder auto-activation after 3 s.
- `ToolHead.register_step_generator(handler)` — registers a step-generation callback.
- `ToolHead.note_step_generation_scan_time(delay, old_delay)` — manages `kin_flush_delay`.
- `ToolHead.note_mcu_movequeue_activity(mq_time, set_step_gen_time)` — updates `need_flush_time` and kicks flush timer.
- `ToolHead._advance_flush_time(flush_time)` / `_advance_move_time(next_print_time)` — batched step generation.
- `ToolHead._process_moves(moves)` — replaces upstream's two-step lookahead flush + trapq injection.
- `ToolHead.set_accel(accel)` — sets `max_accel` and recomputes junction deviation; waits for moves to complete.
- `ToolHead.set_grab_complete(enable)` — sets `is_grab_complete` flag.
- `DripModeEndSignal` exception class.
- `_update_drip_move_time(next_print_time)` — drip mode pacing without `MotionQueuing`.
- G-code commands (new/moved):
  - `SWITCH_OF_EXTENDED_EXTRUDER INDEX=<n>` — activates a logical extruder above `max_physical_extruder_num`.
  - `SET_MAX_Z_ACCEL A=<accel>` — overrides `kin.max_z_accel` at runtime.
  - `SET_MAX_Z_VELOCITY V=<vel>` — overrides `kin.max_z_velocity` at runtime.
- Constants added: `BUFFER_TIME_LOW`, `BGFLUSH_LOW_TIME`, `BGFLUSH_BATCH_TIME`, `BGFLUSH_EXTRA_TIME`, `MIN_KIN_TIME`, `MOVE_BATCH_TIME`, `STEPCOMPRESS_FLUSH_TIME`, `SDS_CHECK_TIME`, `MOVE_HISTORY_EXPIRE`, `DRIP_SEGMENT_TIME`, `DRIP_TIME`.

## Removals / Overrides
- `ToolHeadCommandHelper` class — removed; commands merged into `ToolHead`.
- `ToolHead.add_extra_axis`, `remove_extra_axis`, `get_extra_axes` — removed.
- `ToolHead.extra_axes` list — replaced by `self.extruder`.
- `ToolHead.set_max_velocities()` — removed; logic inlined.
- `LookAheadQueue.is_empty()` — removed.
- `Move.next_junction_v2`, `Move.limit_next_junction_speed()`, `Move.max_mcr_start_v2`, `Move.mcr_delta_v2` — removed.
- `ToolHead.motion_queuing` — not used; `MotionQueuing` object not created.
- Default module `garbage_collection` — removed from auto-loaded list.

## Risks / Compatibility Notes
- The `max_smoothed_v2` look-ahead algorithm produces different (generally lower) junction velocities than the upstream `minimum_cruise_ratio` method. Print quality and speed may differ, particularly on short moves.
- `LOOKAHEAD_FLUSH_TIME` increased to 0.250 s means the planner holds more moves in the queue before flushing; this increases latency between the host and first step output.
- `SWITCH_OF_EXTENDED_EXTRUDER` requires `print_task_config` object to be present; if it is absent, the command raises an error.
- `_extruder_auto_activate()` runs 3 seconds after `klippy:ready` and silently calls `run_script("ACTIVATE_EXTRUDER ...")` — this could conflict with a print that starts immediately.
- `set_accel(accel)` calls `wait_moves()` which blocks the reactor; calling it frequently could stall the print loop.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/toolhead.py
+++ b/klippy/toolhead.py
 # Key structural changes:
 # - ToolHeadCommandHelper removed; commands merged into ToolHead
 # - LookAheadQueue: max_smoothed_v2 algorithm (older); calls _process_moves directly
 # - ToolHead: owns trapq, flush_timer, step_generators directly
 # - extra_axes list replaced by single self.extruder
 # - New: max_logical_extruder_num, max_physical_extruder_num config keys
 # - New G-code: SWITCH_OF_EXTENDED_EXTRUDER, SET_MAX_Z_ACCEL, SET_MAX_Z_VELOCITY
 # - DripModeEndSignal + _update_drip_move_time for self-contained drip mode
 # - is_calibrating_flow flag; flow_calibration events
 # - LOOKAHEAD_FLUSH_TIME: 0.150 -> 0.250; BUFFER_TIME_HIGH: 1.0 -> 2.0
```

</details>
