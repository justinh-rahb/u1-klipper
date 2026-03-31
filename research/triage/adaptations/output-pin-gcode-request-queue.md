# output_pin.py — Restore GCodeRequestQueue and Template Evaluator

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/extras/output_pin.py` removes two upstream classes:
- `GCodeRequestQueue` — time-accurate G-code pin value updates synchronised with
  the motion queue (uses `MotionQueuing` timing)
- `PrinterTemplateEvaluator` — evaluates Jinja2 template expressions for dynamic
  pin values

These were removed because the fork's `toolhead.py` does not implement
`MotionQueuing` (item B3). `GCodeRequestQueue` depends on `motion_queuing` being
present in the printer object. Without `MotionQueuing`, time-accurate pin control
is not available.

The result is that the fork's `output_pin.py` reverts to a simpler synchronous
`SET_PIN` implementation without time-accurate buffering or template support.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides both `GCodeRequestQueue` and
`PrinterTemplateEvaluator` in `klippy/extras/output_pin.py` (lines 15, 101).

`GCodeRequestQueue` enables laser power synchronisation with motion — a common
use case for CNC/laser machines. `PrinterTemplateEvaluator` enables:
```ini
[output_pin my_pin]
value: {printer.toolhead.position.z * 0.1}  # dynamic Z-proportional value
```

The U1 does not use laser cutting or dynamic template pin values, so these
features are not functionally required for U1 operation. However, restoring
them improves upstream compatibility for users running the Extended Firmware
on machines that do use these features.

## Migration Path

**Option A — Restore after MotionQueuing migration (recommended):**
1. Complete the MotionQueuing migration (Adapt B3 — toolhead.py).
2. Restore `motion_queuing.py` (item C32).
3. Copy `GCodeRequestQueue` and `PrinterTemplateEvaluator` from upstream
   `output_pin.py` into the fork.
4. Update the fork's `output_pin.py` `PrinterOutputPin.__init__` to create
   a `GCodeRequestQueue` and `PrinterTemplateEvaluator` when configured.

**Option B — Stub/defer until MotionQueuing done:**
This item has no functional impact on U1 hardware. Defer to after toolhead
migration (B3) since `GCodeRequestQueue` is useless without `MotionQueuing`.

### Testing checkpoints
- `SET_PIN PIN=my_pin VALUE=0.5`: confirm pin responds
- Template pin: configure a pin with a Jinja2 value expression; confirm it
  evaluates correctly (after MotionQueuing is in place)

### Config implications
None for U1 production config. `lava/printer.cfg` does not use template pins.

### klipper-router / Extended Firmware overlay implications
None.

## Risk
**Low** for U1 hardware. **Medium** if attempted before MotionQueuing (B3) —
`GCodeRequestQueue` will fail to find `motion_queuing` in the printer object
at init time. Sequence this after B3 is complete.
