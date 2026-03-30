# mcu.py — Restore MCURestartHelper, DummyResponse, and ADC Batch

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/mcu.py` differs from upstream by approximately 500 lines.
The primary divergences are:

1. **`MCURestartHelper` absent**: Upstream extracted MCU restart/reset logic
   into a `MCURestartHelper` class (line 656). The fork's older `mcu.py` inlines
   this logic differently or lacks it entirely.
2. **`DummyResponse` class**: Upstream `DummyResponse` (line 26) is a minimal
   stand-in for serial responses during MCU startup. The fork may have a different
   or absent implementation.
3. **ADC batch infrastructure**: Upstream uses a batch ADC read system; the
   fork's version differs.
4. **General API drift**: ~500 lines of accumulated upstream refactors
   (error handling, MCU reset sequences, ADC scheduling) that the fork never
   received.

The fork's `mcu.py` changes appear to be entirely passive snapshot divergence —
no U1-specific MCU features were added to `mcu.py` itself (U1-specific MCU
features are in `klippy/klippy.py` and `src/stm32/` firmware files).

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides a modernised `klippy/mcu.py` with:
- `DummyResponse` at line 26: minimal no-op response handler used during startup
- `MCURestartHelper` at line 656: encapsulates MCU restart state machine (soft
  reset, hard reset via GPIO, firmware update detection)
- Batch ADC read scheduling via `MCU_ADC_batch`
- Improved error handling in serial connect/disconnect paths

## Migration Path

1. **Diff the fork's `mcu.py` against upstream** to identify which sections
   have been dropped vs modified. Given that no U1-specific features live in
   `mcu.py`, the goal is to **replace** the fork's version with upstream's version,
   then layer any fork-specific adaptations.
2. **Identify fork-specific additions** in `mcu.py` (if any). Based on the
   research, the fork's `klippy.py` (item B1) handles MCU power rail management
   via event handlers — these do not require changes in `mcu.py` itself.
3. **Replace `klippy/mcu.py`** with the upstream version.
4. **Check `klippy/klippy.py`** (B1) event handler registration — the fork's
   klippy.py registers `mcu:connect` and shutdown events. Verify these still
   fire correctly with the upstream `mcu.py`.
5. **Check `klippy/stepper.py`** (B6) — the fork adds `type`/`index` fields
   to stepper MCU commands. Verify these additions are compatible with the
   upstream `mcu.py` command registration API.
6. **Testing checkpoints:**
   - Cold start with no MCU: confirm `DummyResponse` path works
   - Normal start with AT32F403A: confirm MCU connects and boots
   - Soft restart (`FIRMWARE_RESTART`): confirm `MCURestartHelper` restart sequence completes
   - ADC sensors: confirm temperature sensors read correctly

### Config implications
None.

### klipper-router / Extended Firmware overlay implications
None — `mcu.py` is not part of the overlay.

## Risk
**Medium.** `mcu.py` is critical infrastructure but the migration is a
replacement rather than a patch. The risk is that the upstream version assumes
certain serial protocol features that differ between STM32 and AT32 MCUs. The
AT32 MCUs are declared as `stm32f103xe`/`stm32f105xc` to the Klipper build
system, so the MCU protocol should be identical at the Python layer. The main
risk is that the fork's `klippy.py` power management event handlers expect a
specific MCU startup event ordering that differs in the upstream `mcu.py`.
Test cold start and warm restart thoroughly.
