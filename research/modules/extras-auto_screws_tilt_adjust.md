# auto_screws_tilt_adjust.py

## Summary
`auto_screws_tilt_adjust.py` implements `AutoScrewsTiltAdjust`, an automated bed-levelling screw adjustment wizard for the Snapmaker U1. Unlike the upstream `screws_tilt_adjust` which performs a single probe pass and reports turn amounts, this module drives a multi-round interactive loop: it probes all four screw positions, computes Z differences, pauses to let the user make manual adjustments, re-probes to verify convergence, and repeats until all four corners are within the `adjust_tolerance` threshold or the `max_adjust_times` limit is reached. It uses the fork's `probe_inductance_coil.ProbePointsHelper` and supports a configurable `screw_order`. A rich step-state machine (`AutoScrewsTiltAdjustStep`) tracks progress and is exposed via webhooks for UI integration.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `screws_tilt_adjust` in upstream probes once and reports mm/turn amounts; no interactive loop | Fork drives an iterative probe-adjust-verify loop with state machine, webhooks, and configurable screw order | U1 UI guides the user through interactive screw adjustment; the upstream one-shot approach is insufficient for a guided workflow |

## Additions

### Classes
- **`AutoScrewsTiltAdjustError`** / `AutoScrewsTiltAdjustAbort` / `AutoScrewsTiltAdjustPass` / `AutoScrewsTiltAdjustLimit`  — Custom exceptions for FSM flow control.
- **`AutoScrewsTiltAdjustStep`** — Namespace of state-name string constants (e.g. `IDLE`, `PROBING_BED`, `WAIT_MANUAL_ADJUST_SCREWS`, `SCREWS_TILT_ADJUST_OK`).
- **`AutoScrewsTiltAdjust`** — Klipper extra loaded as `[auto_screws_tilt_adjust]`.

### G-code Commands
- **`AUTO_SCREWS_TILT_ADJUST`** — Run full automatic iterative adjustment.
- **`AUTO_SCREWS_TILT_ADJUST_ENTRY`** — Enter the adjustment workflow (set state to start).
- **`AUTO_SCREWS_TILT_ADJUST_HOMING`** — Perform homing step.
- **`AUTO_SCREWS_TILT_ADJUST_DETECT_PLATE`** — Detect the build plate.
- **`AUTO_SCREWS_TILT_ADJUST_RESET_TO_INITIAL`** — Move to initial position.
- **`AUTO_SCREWS_TILT_ADJUST_PROBE_REFERENCE_POINTS`** — Probe all four reference screw positions.
- **`AUTO_SCREWS_TILT_ADJUST_MANUAL_TUNING`** — Wait for user to manually turn screws, then re-probe.
- **`AUTO_SCREWS_TILT_ADJUST_EXIT`** — Exit the workflow.

### Webhook Endpoints
- `auto_screws_tilt_adjust/abort_screws_adjust` — Abort from UI.
- `auto_screws_tilt_adjust/next_point_adjust` — Signal that user finished adjusting the current screw.

### Config Options
- `screw1`–`screw4` (required) — XY coordinates of the four screws.
- `screw1_name`–`screw4_name` — Human-readable screw labels.
- `screw_order` (list of 4 ints, default [1,2,3,4]) — Order in which screws are adjusted.
- `screw_adjust_threshold` (float, default 0.1 mm) — Minimum Z difference that triggers an adjustment round.
- `adjust_tolerance` (float, default 0.05 mm) — Convergence threshold.
- `probe_interval` (float, default 10 mm) — Distance between probe and screw position.
- `adjust_probe_samples` (int, default 2) — Samples per probe during adjustment.
- `max_adjust_times` (int, default 30) — Maximum adjustment iterations.
- `max_verify_attempts` (int, default 10) — Maximum verification probes.
- `samples` (int, default 3) — Samples for reference probing.
- `sample_retract_dist` (float, default 0.3 mm) — Retract between samples.

### Status
- `get_status(eventtime)` → `{'probe_step', 'screw_order', 'probe_after_delay', 'min_z', 'max_z', 'target_z', 'current_point', 'base_points', 'need_adjusted_z'}`

## Removals / Overrides
- N/A (new file; conceptually related to but does not override upstream `screws_tilt_adjust`)

## Risks / Compatibility Notes
- The probe finalize callback (`probe_finalize`) and the interactive loop use `reactor.pause()` inside G-code handlers, blocking the print thread during multi-minute adjustment sessions.
- The abort-via-webhook path sets `abort_flag` asynchronously, which is read in the G-code thread without a lock — potential race condition.
- `screw_order` validation requires exactly the values 1–4 once each; mis-configuration raises a config error at load time, not at runtime.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# Helper script to automatically adjust bed screws tilt using Z probe
+import math, logging
+from . import probe_inductance_coil
+
+class AutoScrewsTiltAdjustStep:
+    IDLE = "adjust_idle"
+    PROBING_BED = "adjust_probing"
+    WAIT_MANUAL_ADJUST_SCREWS = "adjust_wait_manual"
+    SCREWS_TILT_ADJUST_OK = "adjust_complete"
+    ...
+
+class AutoScrewsTiltAdjust:
+    def __init__(self, config):
+        # Read exactly 4 screw positions
+        # Configure ProbePointsHelper with circle/rect probe mode
+        gcode.register_command("AUTO_SCREWS_TILT_ADJUST", ...)
+        gcode.register_command("AUTO_SCREWS_TILT_ADJUST_MANUAL_TUNING", ...)
+        webhooks.register_endpoint(
+            "auto_screws_tilt_adjust/abort_screws_adjust", ...)
+        webhooks.register_endpoint(
+            "auto_screws_tilt_adjust/next_point_adjust", ...)
+
+def load_config(config):
+    return AutoScrewsTiltAdjust(config)
```
</details>
