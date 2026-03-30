# probe.py — Adopt ProbeResult and Upstream Probe API

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/extras/probe.py` removes the `ProbeResult` namedtuple that
upstream introduced and reverts to the older `do_probe()` return signature that
returns a plain `(x, y, z)` tuple.

In upstream, `ProbeResult` is a namedtuple with fields `(x, y, z, pos, params)`
that carries additional context (probe parameters, sample position) alongside
the coordinates. The fork's older `probe.py` simply returns a plain tuple.

This reversion was passive — the fork's base pre-dates `ProbeResult`. However,
because the fork adds `probe_inductance_coil.py` (D13) which integrates with the
probe API, and `bed_mesh.py` (C4) which calls probe finalize callbacks, the
fork's probe API surface must be internally consistent. At the moment it is —
but it diverges from upstream, making future merges harder.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides `ProbeResult` as a namedtuple
in `klippy/extras/manual_probe.py`:
```python
class ProbeResult:
    def __init__(self, pos, probe_params=None):
        ...
```
And `klippy/extras/probe.py` uses it:
```python
from . import manual_probe
...
return manual_probe.ProbeResult(...)
```

Upstream reference: `klippy/extras/probe.py` line 21, `klippy/extras/manual_probe.py`
at commit `2f05309d`.

## Migration Path

1. **Update `klippy/extras/probe.py`** to import `manual_probe` and return
   `ProbeResult` from `do_probe()` / `run_probe()` instead of a plain tuple.
2. **Update `klippy/extras/probe_inductance_coil.py`** (D13): the inductance
   coil probe integrates with the probe API. Update its return values and
   `finalize_cb` signature to work with `ProbeResult`.
3. **Update `klippy/extras/bed_mesh.py`** (C4): the fork's `bed_mesh.py` calls
   probe finalize callbacks. Update to unpack or access `ProbeResult` fields.
4. **Update `klippy/extras/screws_tilt_adjust.py`** and any other fork files
   that receive probe results — search for `probe.run_probe(` callers.
5. **Restore `load_cell_probe.py`** (item C31 in removed-upstream-extras): after
   this migration, `load_cell_probe.py` will be compatible with the updated
   `probe.py`.
6. **Testing checkpoints:**
   - `BED_MESH_CALIBRATE`: verify all probe points return valid Z values
   - `PROBE_CALIBRATE`: confirm manual probe flow works
   - `AUTO_SCREWS_TILT_ADJUST`: confirm tram routine uses correct probe results
   - Inductance coil single probe `PROBE`: confirm `ProbeResult` fields are correct

### Config implications
None — `ProbeResult` is an internal API change not visible to configs.

### klipper-router / Extended Firmware overlay implications
If the overlay provides a custom probe module that calls `probe.run_probe()`,
update it to handle `ProbeResult` fields.

## Risk
**Medium.** The probe API is used by several fork-specific modules
(`probe_inductance_coil`, `bed_mesh`, `auto_screws_tilt_adjust`). Each must
be updated. Missing one will cause a runtime `AttributeError` or index error
when probing. Systematic grepping for `run_probe(`, `do_probe(`, and probe
finalize callbacks is required to find all call sites.
