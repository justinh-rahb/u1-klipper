# machine_state_manager.py

## Summary
`machine_state_manager.py` provides `MachineStateManager`, a Klipper extra that tracks the printer's high-level operational state (`MachineMainState`) and a finer-grained sub-state (`ActionCode`). It enforces a state-transition rule matrix: most non-IDLE states can only be entered from IDLE, while IDLE and ABNORMAL can be reached from any state. Pre- and post-transition hooks can be registered by other modules. A 10-entry history ring-buffer records state changes for diagnostics. On klippy shutdown the state is automatically set to ABNORMAL. G-code commands allow external systems (e.g., a UI) to drive state changes and query current status.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: explicit printer-lifecycle state machine with transition guards, action sub-states, hooks, and history | U1 UI needs to know whether the printer is idle, printing, calibrating, loading filament, etc. to gate user interactions and prevent conflicting operations |

## Additions

### Enumerations
- **`MachineMainState`** (IntEnum) — 14 states: `IDLE`, `PRINTING`, `XYZ_OFFSET_CALIBRATE`, `BED_LEVELING`, `FLOW_CALIBRATION`, `SHAPER_CALIBRATE`, `UPGRADING`, `ABNORMAL`, `SCREWS_TILT_ADJUST`, `AUTO_LOAD`, `AUTO_UNLOAD`, `MANUAL_LOAD`, `PARK_POINT_MANUAL_CALIBRATION`, `HOMING_ORIGIN_CALIBRATION`.
- **`ActionCode`** (IntEnum) — ~40 sub-states covering homing, plate detection, printing phases, calibration sub-steps, and filament operations (e.g. `PRINT_AUTO_FEEDING = 133`, `BED_LEVELING = 256`, `FLOW_CALIBRATE = 320`).

### Classes
- **`MachineStateManagerErr`** — Custom exception for invalid transitions.
- **`MachineStateManager`** — Klipper extra loaded as `[machine_state_manager]`.

### G-code Commands
- **`SET_MAIN_STATE MAIN_STATE=<name|int> [ACTION=<name|int>]`** — Attempt a validated state transition.
- **`SET_ACTION_CODE ACTION=<name|int> [MAIN_STATE=<name|int>]`** — Update action code, optionally asserting the expected current main state.
- **`GET_MACHINE_STATE`** — Report current main state and action code.
- **`GET_STATE_HISTORY [SHOW_ERROR=0|1]`** — Dump last 10 state transitions.
- **`EXIT_TO_IDLE [REQ_FROM_STATE=<name|int>]`** — Transition to IDLE, optionally asserting the requesting state.
- **`SHOW_STATE_RULES`** — Print the transition and exit rule tables.

### Public API
- `change_state(new_state, action=None)` — Thread-safe (uses reactor mutex); validates transition, runs pre-hooks, updates state, runs post-hooks.
- `exit_to_idle(requested_from_state=None)` — Convenience wrapper for transitioning to IDLE.
- `set_action_code(action_code, main_state=None)` — Update action code with optional state guard.
- `register_pre_hook(hook)` / `unregister_pre_hook(hook)` — Register callbacks invoked before a state change; return `False` to veto.
- `register_post_hook(hook)` / `unregister_post_hook(hook)` — Register callbacks invoked after a successful state change.
- `can_transition(target_state, current_state=None)` → bool
- `get_status(eventtime)` → `{'main_state': ..., 'action_code': ...}`

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- The transition rule table (`DEFAULT_TRANSITION_RULES`) only explicitly restricts a subset of state pairs; `IDLE` and `ABNORMAL` are universally reachable from any state.
- The hook system uses a plain Python list protected by the reactor mutex; if a hook raises an exception the transition is rolled back but the hook is not removed.
- G-code-driven state changes (`SET_MAIN_STATE`) bypass any business-logic guards and directly call `change_state`; a malformed G-code script could put the printer in an inconsistent state.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, time
+from enum import Enum, IntEnum, unique
+
+class MachineStateManagerErr(Exception): ...
+
+@unique
+class MachineMainState(IntEnum):
+    IDLE = 0; PRINTING = 1; XYZ_OFFSET_CALIBRATE = 2
+    BED_LEVELING = 3; FLOW_CALIBRATION = 4; ...
+    HOMING_ORIGIN_CALIBRATION = 13
+
+@unique
+class ActionCode(IntEnum):
+    IDLE = 0; HOMING = 1; DETECT_PLATE = 2
+    PRINT_AUTO_FEEDING = 133; BED_LEVELING = 256; ...
+    HOMING_ORIGIN_CALIBRATING = 832
+
+class MachineStateManager:
+    def __init__(self, config):
+        ...
+        gcode.register_command('SET_ACTION_CODE', ...)
+        gcode.register_command('SET_MAIN_STATE', ...)
+        gcode.register_command('GET_MACHINE_STATE', ...)
+        gcode.register_command('GET_STATE_HISTORY', ...)
+        gcode.register_command('EXIT_TO_IDLE', ...)
+        gcode.register_command('SHOW_STATE_RULES', ...)
+
+def load_config(config):
+    return MachineStateManager(config)
```
</details>
