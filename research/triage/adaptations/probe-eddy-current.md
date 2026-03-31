# probe_eddy_current.py — Restore trigger_analog Dependency

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/extras/probe_eddy_current.py` is a large (~767 line) reversion
from the upstream eddy current probe implementation. The most significant divergence
is that the fork removes the dependency on `trigger_analog.py`:

```python
# Upstream (removed by fork):
from . import ldc1612, trigger_analog, probe, manual_probe
```

`trigger_analog.py` was added to upstream after the fork diverged and provides
the analog trigger interface used by eddy current probe calibration. Because
`trigger_analog.py` is absent from the fork (item C35 — Tier 1 Drop), the
entire eddy current subsystem has been regressed to the pre-`trigger_analog` API.

Additionally, the fork's version removes `ProbeResult` usage (consistent with
item C3 — probe.py Adapt).

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides a complete eddy current probe
implementation in `klippy/extras/probe_eddy_current.py` using:
- `trigger_analog.py` for threshold-based probe triggering
- `ProbeResult` for structured probe results
- `ldc1612.py` for LDC1612 sensor control

The U1 does not use eddy current probes (it uses inductive coil probes via
`inductance_coil.py`), so this file's correctness is relevant only for
interoperability — not for U1 hardware function.

## Migration Path

1. **Restore `trigger_analog.py`** from upstream (item C35 in
   `removed-upstream-extras.md`). This is a prerequisite.
2. **Replace the fork's `probe_eddy_current.py`** with the upstream version.
   Since the U1 does not use eddy current probes, the upstream version can be
   taken verbatim.
3. **After restoring `probe.py` + ProbeResult** (item C3), confirm that the
   upstream `probe_eddy_current.py` works with the updated probe API.
4. **Testing checkpoint:** The U1 `lava/printer.cfg` does not include
   `[probe_eddy_current]`, so no functional testing on hardware is possible.
   Verify that Klipper starts without import errors. Optionally run the upstream
   test suite for eddy current if available.

### Config implications
None for U1 production config — eddy current probe is not used on U1.

### klipper-router / Extended Firmware overlay implications
None — eddy current probe not in overlay.

## Risk
**Low** for U1 hardware (the module is not used). **Medium** for general
compatibility — if `trigger_analog.py` is restored but has its own dependencies
on modules still absent in the fork, import errors may cascade. Resolve
`trigger_analog.py` restoration first, confirm it imports cleanly, then restore
`probe_eddy_current.py`.
