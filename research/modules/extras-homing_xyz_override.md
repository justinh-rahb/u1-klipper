# homing_xyz_override.py

## Summary
`homing_xyz_override.py` implements `HomingXYZOverride`, which completely replaces the G28 homing command with a custom sequence tailored to the U1's multi-extruder tool-changer. Before probing Z it verifies the active extruder is correctly docked or active (calling `get_extruder_activate_status()`), handles unhomed axes by performing a Z-hop using a homing endstop move (for positive-dir Z) or a set-position lift, then moves to a configured XY position, and finally executes a configurable G-code template plus a multi-sample Z probe with its own speed, tolerance, and retract parameters. The module also raises structured Snapmaker error codes (`0002-0528-*`) for common failure modes.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Upstream has `safe_z_home` and `homing_override` for custom G28 sequences | Fork adds `homing_xyz_override` with built-in extruder-status validation, structured error codes, and a two-phase Z probe (fast first-touch + accurate second probe) | U1 tool-changer requires extruder dock-state verification before Z homing; the upstream modules lack this integration |

## Additions

### Classes
- **`HomingXYZOverride`** — Klipper extra loaded as `[homing_xyz_override]`. Intercepts and replaces `G28`.

### G-code Commands
- **`G28`** (override) — The full custom homing sequence: optional Z-hop, XY homing, extruder status check, move to probe position, Z probe. Falls back to previous G28 implementation for axes not handled by this module.

### Key Config Options
- `home_xy_position` — XY position to move to before Z probing (required).
- `z_hop` — Z height to lift before XY movement if Z is already homed.
- `z_hop_speed` — Speed for Z-hop lift.
- `z_hop_homing_accel` — Acceleration override during Z-hop homing move.
- `z_safe` — Minimum Z height when Z is already homed.
- `z_safe_speed` — Speed for Z-safe lift.
- `speed` — XY travel speed to probe position.
- `set_position_z` — Z coordinate assumed before Z-axis is homed (for `set_position`).
- `safe_move_y_pos` — Y limit below which XY moves are safe.
- `z_first_probe_speed` — Speed for the initial fast Z touch.
- `z_first_probe_tolerance` — Tolerance for first-touch samples.
- `z_first_probe_sample_count` — Number of samples for first touch.
- `z_first_probe_retract_dist` — Retract distance between first-touch samples.
- `z_offset` — Fixed Z offset applied after probing.
- `z_probe_speed`, `z_probe_fast_speed`, `z_probe_accel`, `z_probe_z_accel`, `z_probe_tolerance`, `z_probe_lift_speed`, `z_probe_samples`, `z_probe_trigger_freq`, `z_probe_retract_dist`
- `gcode` — G-code template executed as part of the homing sequence (loaded via `gcode_macro`).
- `z_hop_homing_begin_gcode`, `z_hop_homing_end_gcode` — Templates executed around the Z-hop homing move.

### Events Consumed
- `stepper_enable:motor_off` — Clears `z_raised` and `homing_stepper_z_info` when motors are disabled.

### Conflict Check
- Raises a config error if `[homing_override]` or `[safe_z_home]` sections are also present.

## Removals / Overrides
- **Replaces `G28`** — The previous `G28` handler is saved as `prev_G28` and can be called for axes not handled by this module.
- Cannot coexist with `homing_override` or `safe_z_home`.

## Risks / Compatibility Notes
- The extruder status validation (`get_extruder_activate_status`, `check_allow_retry_switch_extruder`, `analyze_switch_extruder_error`) are all fork-specific extruder methods; stock Klipper extruder objects will fail with `AttributeError`.
- Structured error strings (e.g. `'{"coded": "0002-0528-0000-0001", ...}'`) are passed to `gcmd.error()` and `printer.command_error()` — stock Klipper will treat these as plain error strings.
- The `_z_probe_pre_process` method modifies `gcmd.get_command_parameters()` in-place to pass probe parameters, which mutates the G-code command object.
- `grab_hall_sensor_type` attribute check on extruder adds another fork-specific dependency.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Run user defined actions in place of a normal G28 homing command
+import math, logging, copy
+import stepper
+from . import homing
+
+class HomingXYZOverride:
+    def __init__(self, config):
+        ...
+        self.prev_G28 = self.gcode.register_command("G28", None)
+        self.gcode.register_command("G28", self.cmd_G28)
+        if config.has_section("homing_override") or config.has_section("safe_z_home"):
+            raise config.error("(homing_override or safe_z_home) and "
+                               "homing_xyz_override cannot be used simultaneously")
+
+    def cmd_G28(self, gcmd):
+        # 1. Z-hop if needed
+        # 2. Check extruder park status
+        # 3. Move to home_xy_position
+        # 4. Execute gcode template
+        # 5. Two-phase Z probe
+        ...
+
+def load_config(config):
+    return HomingXYZOverride(config)
```
</details>
