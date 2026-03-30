# scripts — Restore calibrate_shaper.py and graph_accelerometer.py API

## Tier
Adapt

## Fork Change Summary
The fork's `scripts/calibrate_shaper.py` and `scripts/graph_accelerometer.py`
were modified to match the fork's simplified `CalibrationData` API in
`klippy/extras/shaper_calibrate.py` (item C10):
- `name` parameter removed from `process_accelerometer_data()` calls
- `data_sets` iteration changed to work with integer count

These are offline post-processing scripts that run on a host machine to process
resonance test data and generate shaper configuration recommendations.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides:
- `scripts/calibrate_shaper.py` — calls `CalibrationData(name, freq_bins, ...)`
- `scripts/graph_accelerometer.py` — same

Both scripts work with the named dataset API.

## Migration Path

This migration is directly coupled to the `shaper_calibrate.py` adaptation
(item C10). Complete that migration first, then:

1. **Restore `scripts/calibrate_shaper.py`** to the upstream version. The
   primary change is restoring `name` parameter in `process_accelerometer_data()`
   calls and `CalibrationData` construction.
2. **Restore `scripts/graph_accelerometer.py`** similarly.
3. **Preserve `zvd` shaper** references if the fork's scripts include `zvd` in
   the list of shapers to fit — carry this forward from the fork.
4. **Testing checkpoint:** Run `calibrate_shaper.py` against a captured
   resonance CSV file (e.g. from U1 hardware or a test fixture). Confirm it
   generates a `[input_shaper]` recommendation.

### Config implications
None — these are offline scripts not loaded by Klipper at runtime.

### klipper-router / Extended Firmware overlay implications
If the overlay bundles scripts, update them together.

## Risk
**Low.** Offline scripts only; no runtime impact. The only risk is that a user
who has generated resonance data with the fork's scripts (no `name` column)
cannot process it with the restored scripts. Document this in the migration notes.
