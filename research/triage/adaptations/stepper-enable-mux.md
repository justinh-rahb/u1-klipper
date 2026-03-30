# stepper_enable.py — Restore mux_command Registration

## Tier
Drop

## Fork Change Summary
The fork changed `SET_STEPPER_ENABLE` from `register_mux_command` (upstream) to
a plain `register_command` in `klippy/extras/stepper_enable.py`. In upstream,
each named stepper registers itself as a sub-command via:

```python
gcode.register_mux_command('SET_STEPPER_ENABLE', "STEPPER", name, ...)
```

This allows `SET_STEPPER_ENABLE STEPPER=<name>` to dispatch to the correct
per-stepper handler. The fork reverts this to a plain `register_command`, losing
the mux dispatch.

The change is a passive API snapshot regression — `register_mux_command` existed
in the Klipper version the fork was based on, and the fork's older `gcode.py`
may have had a slightly different mux API. However, the current fork's `gcode.py`
still supports mux commands, so the reversion is safe to reverse.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) uses `register_mux_command` in
`klippy/extras/stepper_enable.py` (lines 87–89):

```python
gcode.register_mux_command('SET_STEPPER_ENABLE', "STEPPER", name,
                           self.cmd_SET_STEPPER_ENABLE,
                           desc=self.cmd_SET_STEPPER_ENABLE_help)
```

This approach correctly handles multi-stepper setups where each stepper
registers its own `SET_STEPPER_ENABLE STEPPER=<name>` handler.

## Migration Path

1. **Replace** the fork's plain `register_command('SET_STEPPER_ENABLE', ...)` with the upstream `register_mux_command('SET_STEPPER_ENABLE', "STEPPER", name, ...)` pattern.
2. **Verify `gcode.register_mux_command` signature** in the fork's `gcode.py` matches upstream. The fork's `gcode.py` (item B4) retains the mux command infrastructure.
3. **Testing checkpoint:** Confirm that `SET_STEPPER_ENABLE STEPPER=stepper_x ENABLE=0` dispatches correctly per stepper. Run U1's existing homing sequence tests if available.

### Config implications
None — this is a registration mechanism change. Existing G-code macros calling
`SET_STEPPER_ENABLE STEPPER=<name>` will work correctly after restoration.
If the fork's version registered a single handler for all steppers, behaviour
for multi-stepper calls may change — verify with the U1's 4-extruder config.

### klipper-router / Extended Firmware overlay implications
None.

## Risk
**Low.** The underlying functionality is identical; only the command dispatch
mechanism changes. The mux pattern is the more correct implementation. The fork's
`gcode.py` still contains `register_mux_command`, so no infrastructure changes
are needed.
