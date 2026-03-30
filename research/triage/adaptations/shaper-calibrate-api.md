# shaper_calibrate.py — Restore CalibrationData Named Datasets

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/extras/shaper_calibrate.py` simplifies the `CalibrationData`
class by:
1. Removing the `name` parameter from `__init__`: was `(name, freq_bins, ...)`, now `(freq_bins, ...)`
2. Changing `self.data_sets` from a list to an integer count (`1`)
3. Removing `get_datasets()` and `save_params()` methods
4. Removing the `name` parameter from `calc_freq_response()` and `process_accelerometer_data()`

Additionally, the fork adds the `'zvd'` shaper type to `AUTOTUNE_SHAPERS`.

The CalibrationData simplification was done because the fork's
`resonance_tester.py` (item C5) is 2D-only and no longer captures named
X/Y/Z datasets — it captures a single unnamed dataset per axis per calibration
run. The `name` parameter became redundant.

The `zvd` (Zero Vibration Derivative) shaper type is a U1-specific addition
that improves vibration cancellation for the U1's print head mass.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) retains:
- `CalibrationData.__init__(self, name, freq_bins, psd_sum, psd_x, psd_y, psd_z)`
- `self.data_sets` as a list
- `get_datasets()` method
- `save_params()` on `ShaperCalibrate`
- `AUTOTUNE_SHAPERS = ['zv', 'mzv', 'ei', '2hump_ei', '3hump_ei']` (no `zvd`)

The named datasets allow multiple calibration runs to be overlaid and compared,
and `save_params()` writes the selected shaper to the config file.

## Migration Path

### Part 1 — Restore CalibrationData API (depends on resonance_tester adaptation)
1. Restore the `name` parameter to `CalibrationData.__init__`. Provide a default
   `name=''` to maintain backward compatibility with any fork code calling the
   old signature.
2. Restore `self.data_sets` as a list (or keep the integer but make it compatible
   with upstream callers that iterate over `data_sets`).
3. Restore `get_datasets()` and `save_params()` methods from upstream.
4. Update `calc_freq_response()` and `process_accelerometer_data()` to accept
   the optional `name` parameter.
5. **Update `klippy/extras/resonance_tester.py`** (fork item C5): the fork's
   resonance tester calls `shaper_calibrate` with the simplified API. Update
   `SM_FAST_SHAPER_CALIBRATE` and all `process_accelerometer_data()` calls to
   pass a `name` argument (use `'x'` or `'y'` as appropriate).
6. **Update `scripts/calibrate_shaper.py`** (item I2) and
   `scripts/graph_accelerometer.py` (item I3): both were adapted to the simplified
   API. Restore the `name` parameter usage.

### Part 2 — Retain zvd shaper (Tier 4 Keep)
7. After restoring the upstream `AUTOTUNE_SHAPERS` list, **add `'zvd'` back**:
   ```python
   AUTOTUNE_SHAPERS = ['zv', 'zvd', 'mzv', 'ei', '2hump_ei', '3hump_ei']
   ```
   The `zvd` shaper filter coefficients must be implemented in the shaper
   calculation code — confirm the fork has these coefficients and carry them forward.

### Testing checkpoints
- `SHAPER_CALIBRATE`: run a resonance test; confirm a named `CalibrationData`
  object is created with the correct axis name
- `save_params()`: confirm the selected shaper parameters are written to printer.cfg
- `zvd` shaper: configure `[input_shaper] shaper_type: zvd`; confirm Klipper
  starts without error and uses the ZVD filter

### Config implications
If `lava/printer.cfg` uses `shaper_type: zvd`, this must be preserved after
the CalibrationData migration.

### klipper-router / Extended Firmware overlay implications
If the overlay bundles calibration scripts, update `calibrate_shaper.py` and
`graph_accelerometer.py` to use the restored `name` parameter.

## Risk
**Medium.** The CalibrationData API is called from multiple places
(resonance_tester, scripts). Missing one call site will cause a `TypeError`
at runtime. The `zvd` shaper coefficients must be carried forward — if they
are lost during migration, users on ZVD shaper configs will silently fall back
to an incorrect filter.
