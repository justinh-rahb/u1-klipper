# stepper.py

## Summary
`stepper.py` implements `MCU_stepper`, the low-level stepper motor driver that manages the `stepcompress` queue and iterative solver. The fork's changes align with the older architecture in the rest of the fork: `MotionQueuing`/`syncemitter` is replaced with direct `stepcompress` allocation; `MCU_stepper.__init__` takes a name string instead of a config object; `generate_steps()` is added as a combined check-active + step-generation callback; and the `config_stepper` MCU firmware command gains `type=%u index=%u` parameters for the power-loss recovery system. A module-level helper (`get_stepper_type_and_index`) maps stepper names to a `(type, index)` tuple that the MCU firmware stores alongside each `queue_step` message for recovery after power loss.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `MCU_stepper.__init__(config, step_pin_params, ...)` — takes full config object | `MCU_stepper.__init__(name, step_pin_params, ...)` — takes name string | Decouples stepper from config; matches older API |
| `self._name = config.get_name()` | `self._name = name` (passed in) | Same |
| Uses `motion_queuing.allocate_syncemitter(mcu, sname)` | Directly allocates via `ffi_lib.stepcompress_alloc(oid)` | `MotionQueuing` / `syncemitter` not present in fork |
| `_stepqueue = ffi_lib.syncemitter_get_stepcompress(syncemitter)` | `_stepqueue = ffi_lib.stepcompress_alloc(oid)` with `ffi_main.gc(...)` | Direct allocation |
| `mcu.register_stepqueue` not called | `self._mcu.register_stepqueue(self._stepqueue)` called in `__init__` | Registers with MCU for flushing |
| `ffi_lib.itersolve_set_stepper_kinematics(syncemitter, sk)` | `ffi_lib.itersolve_set_stepcompress(sk, stepqueue, step_dist)` | Different FFI function signature |
| `ffi_lib.syncemitter_queue_msg` for raw message queuing | `ffi_lib.stepcompress_queue_msg(stepqueue, data, len)` | Direct stepcompress API |
| `ffi_lib.itersolve_set_trapq(sk, tq, step_dist)` | `ffi_lib.itersolve_set_trapq(sk, tq)` — `step_dist` removed | Different FFI signature |
| `set_trapq()` method name | `set_stepper_kinematics()` with new call | Method rename on kinematics set |
| Step-both-edge: checks `STEPPER_STEP_BOTH_EDGE`, `STEPPER_BOTH_EDGE`, `STEPPER_OPTIMIZED_UNSTEP` constants | Only checks `STEPPER_BOTH_EDGE`; simpler logic | Older MCU firmware support |
| `MIN_BOTH_EDGE_DURATION = 0.000000500` / `MIN_OPTIMIZED_BOTH_EDGE_DURATION` | `MIN_BOTH_EDGE_DURATION = 0.000000200` | Tighter constraint for AT32 hardware |
| `MAX_STEPCOMPRESS_ERROR = 0.000025` constant | `mcu.get_max_stepper_error()` config-driven | Per-MCU configurable error |
| `config_stepper oid=%d pin=%s dir=%s step=%s ticks=%u` MCU command | Appends `type=%u index=%u` | Power-loss recovery: MCU stores stepper identity with each move |
| `queue_step oid=%c interval=%u count=%hu add=%hi` | `queue_step oid=%c interval=%u count=%hu add=%hi line=%u` | Stores print file line number for power-loss recovery |
| `_check_active` registered as a flush callback via `motion_queuing` | Replaced by `generate_steps(flush_time)` which combines active check + step generation | Self-contained step generation without `MotionQueuing` |
| `get_mcu_position(cmd_pos=None)` — optional arg | `get_mcu_position()` — no argument; always uses current commanded position | Simplification |
| Short name for thread: slices `'stepper'` prefix differently | `if short and self._name.startswith('stepper_'):` (adds underscore) | Fix for stepper name format |

## Additions
- `power_loss_need_save_steppers = ['stepper_x', 'stepper_y', 'stepper_z', 'extruder']` module constant.
- `get_stepper_type_and_index(stepper)` — maps a stepper name string to `(type_index, axis_index)` for power-loss data. Returns `(0xFF, 0xFF)` for unrecognised names.
- `MCU_stepper._stepper_type` and `_stepper_index` attributes — populated by `get_stepper_type_and_index`.
- `MCU_stepper.generate_steps(flush_time)` — combined active-check and step-generation method; replaces `_check_active` flush callback pattern.

## Removals / Overrides
- `MIN_OPTIMIZED_BOTH_EDGE_DURATION` and `MAX_STEPCOMPRESS_ERROR` constants removed.
- `MCU_stepper._syncemitter` — not allocated; `_stepqueue` directly allocated.
- `MCU_stepper.set_trapq()` — renamed/replaced by `set_stepper_kinematics()`.
- `MCU_stepper._check_active` / `_check_active` flush callback registration via `motion_queuing` — removed.
- `MCU_stepper.get_mcu_position(cmd_pos=None)` optional argument removed.
- `configfile.deprecate_mcu_code` call for `STEPPER_STEP_BOTH_EDGE` removed (that method was also removed from configfile).

## Risks / Compatibility Notes
- The `type=%u index=%u` addition to `config_stepper` MCU command requires matching firmware that understands these fields. Running this host software against stock Klipper firmware will produce a protocol error at config time.
- `queue_step` gains a `line=%u` field — same firmware requirement as above.
- `generate_steps` is called directly by `ToolHead._advance_flush_time` (registered via `register_step_generator`). If this callback raises, it propagates through the flush timer and could crash the reactor.
- `get_stepper_type_and_index` uses `startswith` matching; a stepper named `stepper_x1` will match `stepper_x` and return index `0` rather than `1` because the remaining suffix `"1"` is a digit after `"stepper_x"`.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- a/klippy/stepper.py
+++ b/klippy/stepper.py
@@ +11 @@
+power_loss_need_save_steppers = ['stepper_x', 'stepper_y', 'stepper_z', 'extruder']
+def get_stepper_type_and_index(stepper): ...

@@ -23,3 +36 @@
-MIN_BOTH_EDGE_DURATION = 0.000000500
-MIN_OPTIMIZED_BOTH_EDGE_DURATION = 0.000000150
-MAX_STEPCOMPRESS_ERROR = 0.000025
+MIN_BOTH_EDGE_DURATION = 0.000000200

 # MCU_stepper.__init__: name string instead of config; stepcompress_alloc directly
 # config_stepper: type=%u index=%u appended
 # queue_step: line=%u appended
 # generate_steps() replaces _check_active flush callback
```

</details>
