# filament_feed_fac_test.py

## Summary
`filament_feed_fac_test.py` implements `FeedFacTest`, a factory self-test module for the Snapmaker U1 filament feeder board. It drives alternating digital output patterns on five output pins (light channels, tachometer drive pins, and a port pin) and reads back the resulting states on five corresponding input pins to verify electrical continuity. It then runs the feeder motor in both forward and reverse directions at 50% PWM and checks the motor tachometer RPM falls within configured `motor_dest_rpm_min` / `motor_dest_rpm_max` bounds. It also re-uses the `FeedMotor` and `FeedTachometer` helper classes from the conceptually related `filament_feed_fac_test.py` file itself (defined inline).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: factory-floor PCB continuity and motor RPM test for the feeder board | Snapmaker uses automated end-of-line testing; this module enables a single G-code command to validate the feeder hardware before shipment |

## Additions

### Classes
- **`FeedTachometer`** — (Local copy of feeder tachometer helper) Wraps `pulse_counter.FrequencyCounter` to report RPM and cumulative count.
- **`FeedPwmCfg`** — Data class for PWM H-bridge config.
- **`FeedMotor`** — H-bridge driver with direction-reversal protection (2.5 s hard-protect time).
- **`FeedFacTest`** — Main extra class loaded via `load_config_prefix`.

### G-code Commands
- **`FEED_FACTORY_TEST MODULE=<name>`** — Runs the full factory test sequence and responds with pass/fail state, pin input/output bitmasks, and RPM readings for idle, forward, and reverse motor directions.

### Config Options
- `light_ch_1_white`, `light_ch_2_white` — Output pin names for white LEDs (driven high/low alternately).
- `wheel_tach_ch_1_1_pin`, `wheel_tach_ch_2_1_pin` — Output/drive pins for wheel tachometers.
- `port_ch_1_pin` — Output port-detect drive pin.
- `light_ch_1_red`, `light_ch_2_red` — Input pins (readback for white output).
- `wheel_tach_ch_1_2_pin`, `wheel_tach_ch_2_2_pin` — Input pins (readback for tach outputs).
- `port_ch_2_pin` — Input pin (readback for port output).
- `motor_ch_1_pin`, `motor_ch_2_pin` — H-bridge PWM pins.
- `motor_cycle_time` — PWM period (s).
- `motor_max_value` — Maximum PWM duty cycle (0–1).
- `motor_tach_pin` — Motor tachometer input pin.
- `motor_tach_ppr` — Pulses per revolution (default 2).
- `motor_tach_poll_interval` — Tachometer poll interval (default 0.5 ms).
- `motor_dest_rpm_min`, `motor_dest_rpm_max` — RPM pass/fail window.

### Test States
- `TEST_STATE_IDLE`, `TEST_STATE_TESTING`, `TEST_STATE_FAILED`, `TEST_STATE_SUCCESSFUL`

### Test Logic
1. Set even-indexed output pins HIGH, odd LOW; verify input bitmask matches.
2. Swap: even LOW, odd HIGH; verify again.
3. Run motor forward at 0.5 duty; check RPM in bounds.
4. Run motor reverse at 0.5 duty; check RPM in bounds.
5. Stop motor; check RPM == 0.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- The test uses `reactor.pause()` inside a G-code command handler to synchronously wait for motor spin-up — blocking behaviour.
- Uses bare `raise` (with no argument) to trigger the failure path — valid Python 2/3 only inside an except block; if any `if` branch triggers `raise` outside an except, it will cause a `RuntimeError`. The test is intended only as a factory tool, not for production use.
- Output pins are configured with `setup_max_duration(0.)` (unlimited duration), so a crash mid-test leaves them in an energised state.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging
+from . import pulse_counter
+
+TEST_STATE_IDLE      = 'idle'
+TEST_STATE_TESTING   = 'testing'
+TEST_STATE_FAILED    = 'failed'
+TEST_STATE_SUCCESSFUL = 'successful'
+
+FEED_MOTOR_DIR_IDLE = 0
+FEED_MOTOR_DIR_A    = 1
+FEED_MOTOR_DIR_B    = 2
+FEED_MOTOR_HARD_PROTECT_TIME = 2.5
+
+class FeedTachometer: ...
+class FeedPwmCfg: ...
+class FeedMotor: ...
+
+class FeedFacTest:
+    def __init__(self, config) -> None:
+        ...
+        gcode.register_mux_command("FEED_FACTORY_TEST", "MODULE",
+                                self.module_name,
+                                self.cmd_FEED_FACTORY_TEST)
+    def cmd_FEED_FACTORY_TEST(self, gcmd):
+        # GPIO continuity test + motor RPM test
+        ...
+
+def load_config_prefix(config):
+    return FeedFacTest(config)
```
</details>
