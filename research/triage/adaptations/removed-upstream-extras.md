# Removed Upstream Extras — Restore from Upstream

## Tier
Drop

## Fork Change Summary
The fork is missing 14 upstream extras modules that exist in current upstream
Klipper `HEAD`. These were present in the upstream Klipper version the fork was
based on (or added to upstream after the fork diverged), but were never
incorporated into the fork — likely because none of them are used by U1 hardware.
Their absence means any user config referencing these sections will fail to load.

The affected modules are:

| ID | Module | Upstream File | Why Absent |
|----|--------|--------------|------------|
| C22 | `ads1220` | `klippy/extras/ads1220.py` | No ADS1220 on U1 |
| C23 | `ads1x1x` | `klippy/extras/ads1x1x.py` | No ADS1x1x on U1 |
| C24 | `bmi160` | `klippy/extras/bmi160.py` | No BMI160 on U1 |
| C25 | `canbus_stats` | `klippy/extras/canbus_stats.py` | No CAN bus on U1 |
| C26 | `garbage_collection` | `klippy/extras/garbage_collection.py` | Not auto-loaded in fork's toolhead |
| C27 | `hx71x` | `klippy/extras/hx71x.py` | No HX71x on U1 |
| C28 | `icm20948` | `klippy/extras/icm20948.py` | No ICM-20948 on U1 |
| C29 | `lis3dh` | `klippy/extras/lis3dh.py` | No LIS3DH on U1 |
| C30 | `load_cell` | `klippy/extras/load_cell.py` | No load cell on U1 |
| C31 | `load_cell_probe` | `klippy/extras/load_cell_probe.py` | No load cell probe on U1 |
| C33 | `static_pwm_clock` | `klippy/extras/static_pwm_clock.py` | Not used on U1 |
| C34 | `temperature_probe` | `klippy/extras/temperature_probe.py` | Not used on U1 |
| C35 | `trigger_analog` | `klippy/extras/trigger_analog.py` | Not used; eddy current dep |
| C36 | `static_digital_output` | `klippy/extras/static_digital_output.py` | Not used on U1 |

`motion_queuing.py` (C32) is covered separately because its restoration is
coupled to the `toolhead.py` adaptation (Adapt item B3).

## Upstream Solution
All 14 files listed above are present in upstream Klipper `HEAD` (`2f05309d`).
They can be copied verbatim.

Notable dependency chains:
- `load_cell_probe.py` depends on `load_cell.py` and `probe.py` — since `probe.py`
  was modified in the fork (item C3), restoring `load_cell_probe.py` may require
  adopting upstream's `ProbeResult` changes first (Adapt item C3).
- `trigger_analog.py` is used by `probe_eddy_current.py` — both should be
  restored together (Adapt item C6).
- `garbage_collection.py` is auto-loaded by upstream's `toolhead.py` but **not**
  by the fork's `toolhead.py`. Restoring the file is safe; whether to auto-load
  it is a separate decision.

## Migration Path

1. **Copy each file verbatim** from upstream `klippy/extras/<module>.py` into the fork.
2. **Handle dependency order:**
   - Restore `trigger_analog.py` before tackling `probe_eddy_current.py` (Adapt C6).
   - Restore `load_cell.py` and `load_cell_probe.py` together, after probe.py adaptation (Adapt C3).
   - `garbage_collection.py`: restore the file; decide separately whether to add it to `toolhead.py`'s default module list.
3. **Testing checkpoint:** Start Klipper with the U1 `lava/printer.cfg`. The restored modules should load without error (they are not referenced by the config, so they simply register themselves as loadable extras). Verify no import errors.

### Config implications
None for U1 production config — none of these modules are referenced in
`lava/printer.cfg`. However, any downstream user who has added these sections
to a custom overlay config will benefit from their presence.

### klipper-router / Extended Firmware overlay implications
None — these are extras not loaded by the U1 config.

## Risk
**Low.** These are additive file restores. No U1 code references them. The only
risk is import-time errors if any restored module has an upstream dependency
that conflicts with the fork's modified Python environment (e.g., `msgspec`,
`bulk_sensor`). Review each module's imports before restoring:
- `ads1220.py`, `ads1x1x.py`, `hx71x.py` — depend on `bus.py` (present in fork)
- `bmi160.py`, `icm20948.py`, `lis3dh.py` — depend on `bus.py` and `bulk_sensor.py`; restore `bulk_sensor.py` first if absent
- `load_cell.py` — depends on `bulk_sensor.py` and `probe.py`
- `garbage_collection.py` — standard library only
