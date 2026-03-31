# tmc.py — Restore TMCStallguardDump

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/extras/tmc.py` removes the `TMCStallguardDump` class and
its associated `from . import bulk_sensor` import. `TMCStallguardDump` was added
to upstream after the fork diverged and provides periodic stall guard value
dumping (via the bulk sensor infrastructure) for diagnostic purposes.

Additionally, the fork changes TMC error message strings from plain text to
coded JSON:
```python
# Fork error format (keep — Tier 4):
'{"coded": "0003-0522-0000-0011", "oneshot": 0, "msg": "TMC %s driver error..."}'
```

This coded error format is part of the fork's exception system (B15/B16) and
must be preserved.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) includes `TMCStallguardDump` in
`klippy/extras/tmc.py` (references `bulk_sensor.py` for periodic data capture).

The upstream `TMCStallguardDump` allows:
```ini
[tmc2209 stepper_x]
diag_pin: PA6
```
to automatically dump stall guard values when a stall is detected, useful for
sensorless homing tuning.

The U1 uses sensorless homing (TMC2209) and would benefit from this diagnostic
tool.

## Migration Path

1. **Restore `bulk_sensor.py`** from upstream `klippy/extras/bulk_sensor.py`
   if absent in the fork. Check: `grep -l "bulk_sensor" klippy/extras/*.py`.
2. **Copy the `TMCStallguardDump` class** from upstream `klippy/extras/tmc.py`
   into the fork's version.
3. **Add `from . import bulk_sensor`** import back to the fork's `tmc.py`.
4. **Preserve the fork's coded error message format**: Do not replace the coded
   JSON error strings with upstream's plain-text strings. The fork's error format
   is required by the exception system.
5. **Preserve TMC temperature rounding** change (`round(..., 0)` instead of
   `round(..., 2)`) — this is a deliberate U1 choice.
6. **Testing checkpoints:**
   - Sensorless homing (`G28`): confirm TMC stallguard fires and homing completes
   - TMC error simulation: trigger a TMC overtemp; confirm coded JSON error appears in Moonraker log
   - `TMCStallguardDump` activation (if using `diag_pin`): confirm bulk sensor data is captured

### Config implications
None for existing U1 config. To use `TMCStallguardDump`, `lava/printer.cfg`
would need `diag_pin` entries in TMC sections.

### klipper-router / Extended Firmware overlay implications
None.

## Risk
**Low.** `TMCStallguardDump` is additive. The fork's coded error strings must
not be overwritten by an inadvertent upstream merge. The `bulk_sensor` import
is safe as long as `bulk_sensor.py` is present (it is in upstream; check if
it was removed from the fork).
