# Anycubic Avata Active Noise Reduction Notes

Research date: 2026-07-08

This note captures the current reverse-engineering trail for Anycubic's
Kobra X / Kobra S1 Max active motor noise reduction.  The goal is to
understand what Anycubic implemented in its Klipper-like Avata stack and turn
the useful parts into a proper Klipper design for U1 X/Y TMC2240 direct-mode
control.

## Inputs

- Kobra X SWU: `/Users/justinh/Downloads/update.swu`
- Extracted root: `/private/tmp/kobrax-root`
- Host binaries:
  - `/private/tmp/kobrax-root/app/bin/avata_main`
  - `/private/tmp/kobrax-root/app/bin/avata_ui`
- Kobra X motor firmware:
  - `/private/tmp/kobrax-root/motor_firmware_v1.6.01_20260313.bin`
  - size: 95017 bytes
- Kobra S1 Max motor firmware:
  - `/Users/justinh/Downloads/motor_firmware_v1.6.51_20260427.bin`
  - size: 95425 bytes

The motor firmware vector table has initial SP in SRAM and reset vector
`0x08008199`, so the blob is linked at `0x08008000`.  Ghidra imports at
`0x08000000` are still useful for relative code, but absolute data pointers
need the `0x8000` adjustment.

## Hardware Clues

The Kobra X board photo shows a dedicated Artery MCU:

- Marking: `AT32F403ARGT7`
- Same AT32F403A family as the U1 mainboard MCU.
- The Kobra X/S1 board has a separate motor-driver/control section, consistent
  with Anycubic putting the tight realtime waveform work on a motor MCU instead
  of the weak Linux SoC.

The UI and host fault strings expose motor-MCU-specific errors:

- `fault_current_offset`
- `fault_current_amp_over_range`
- `fault_current_slope_over_range`
- `fault_stator_phase_missing`
- `fault_sync_pulse_period_wrong`
- `fault_sync_pulse_over_time`
- `fault_flash_data_loss`
- `fault_motor_step_loss`
- `fault_step_queue_overflow`

This points to a dedicated closed-loop-ish motor controller that owns current
waveform validation, sync pulse timing, step queue handling, flash persistence,
and step-loss detection.

## Avata Host Workflow

`avata_main` has a first-class `MotorAnc` module.  Relevant strings:

- `8MotorAnc`
- `ACTIVE_NOISE_REDUCTION_ENABLE {} {} {} {}`
- `ACTIVE_NOISE_REDUCTION_ENABLE AXIS=x IS_ARC=0 ENABLE=1`
- `ACTIVE_NOISE_REDUCTION_ENABLE AXIS=x IS_ARC=0 ENABLE=0`
- `ACTIVE_NOISE_REDUCTION_ENABLE AXIS=y IS_ARC=0 ENABLE=1`
- `ACTIVE_NOISE_REDUCTION_ENABLE AXIS=y IS_ARC=0  ENABLE=0`
- `ACTIVE_NOISE_REDUCTION_ENABLE AXIS=y IS_ARC=1  ENABLE=1`
- `ACTIVE_NOISE_REDUCTION_ENABLE AXIS=y IS_ARC=1  ENABLE=0`
- `ACTIVE_NOISE_REDUCTION AXIS={} SPEED={}`
- `ACTIVE_NOISE_REDUCTION_ARC AXIS={} SPEED={}`
- `active_noise_reduction_speed`
- `active_noise_reduction_count`

The config parser around `FUN_00f92950` reads:

| Key | Default / meaning |
| --- | --- |
| `speed_range` | `[5.0, 15.0]` |
| `move_range` | `[15.0, 50.0]` |
| `amplitude` | `5` |
| `move_count` | likely `3` |
| `arc_move_count` | `3` |
| `circle_center` | two-value vector |
| `radius` | `5.0` |

The command builders:

- `FUN_01002b38`: updates `active_noise_reduction_speed/count`, formats
  `ACTIVE_NOISE_REDUCTION AXIS={} SPEED={}`, dispatches through
  `FUN_01001338`.
- `FUN_01003938`: same as above, using the second speed/count field pair.
- Arc builders around `0x01006b40` and `0x01007f9c`: update the same workflow
  fields, format `ACTIVE_NOISE_REDUCTION_ARC AXIS={} SPEED={}`, dispatch
  through `FUN_01001338`.
- `FUN_01001338`: generic script/G-code dispatcher.  It logs/wraps the command
  as `script:{},is_notice:{},is_error:{}`, optionally notifies through a global
  callback, then sends it to the script execution path.
- `FUN_01016b94`: workflow status serialization includes
  `active_noise_reduction_speed` and `active_noise_reduction_count`.

The observed sequence is:

1. Enable X linear active-noise mode.
2. Run linear X sweeps over the configured speed/move/count range.
3. Disable X linear mode and enable Y linear mode.
4. Run linear Y sweeps.
5. Enable/disable Y arc mode and run arc sweeps.
6. Re-enable normal X/Y state after the calibration stages.

The host state-machine writes workflow/progress bytes near these transitions;
those look like UI state values, not motor protocol opcodes.

## Avata UI Workflow

`avata_ui` exposes active noise reduction as a first-class calibration:

- `active_noise_reduction`
- `_handle_req_active_noise_reduction`
- `ActiveNoiseReductionRequest`
- `ActiveNoiseReductionResponse`
- `WorkFlowActiveNoiseReduction`
- `/applink.AppLinkService/ActiveNoiseReduction`
- `ACTIVE_NOISE_REDUCTION_X`
- `ACTIVE_NOISE_REDUCTION_Y`
- `ACTIVE_NOISE_REDUCTION_Z`
- `ACTIVE_NOISE_REDUCTION_C`
- `GROUP_CALIBRATION_ACTIVE_NOISE_REDUCTION_*`
- `ACTIVE_NOISE_REDUCTION_WORK`
- `motor_mcu_version`
- `UPGRADE_MOTOR_MCU`

User-facing strings confirm the calibration intent:

- "Measure the subtle differences of each motor to run the active noise
  calibration algorithm."
- "Active noise reduction, do not touch it"
- "Vibration Detecting, please do not touch the printer"

The abnormal-result messages mention X/Y vibration compensation and belt
tension / accelerometer wiring, which strongly suggests an accelerometer-based
acceptance check even if the actual correction is stored on the motor MCU.

## Motor Firmware Findings

Both motor firmware versions contain EasyFlash env strings for persistent
calibration/storage:

| Key | v1.6.01 file offset | v1.6.51 file offset |
| --- | ---: | ---: |
| `error_rate` | `0x16e80` | `0x17010` |
| `error_rate_index` | `0x16e8b` | `0x1701b` |
| `PowerDown_data` | `0x16e9c` | `0x1702c` |
| `X_Harmonic_Table` | `0x16eab` | `0x1703b` |
| `Y_Harmonic_Table` | `0x16ebc` | `0x1704c` |
| `Z_Harmonic_Table` | `0x16ecd` | `0x1705d` |
| `posX` | `0x16f0e` | `0x1709e` |
| `posY` | `0x16f13` | `0x170a3` |
| `posZ` | `0x16f18` | `0x170a8` |

Runtime addresses use base `0x08008000`, so the v1.6.51 strings are at
`0x0801f010` and onward.

`FUN_08001320` reads:

- `error_rate_index` as a 1-byte value.
- `error_rate` as a `0x120` byte buffer.
- It loops modulo `0x48` (`72`), implying `0x120 = 72 * 4`.

Working interpretation: `error_rate` stores a ring or history of 72
32-bit values, indexed by `error_rate_index`.

The harmonic table strings have no simple PC-relative xrefs in the current
Ghidra import, but with the correct base a pointer to `X_Harmonic_Table`
appears in the blob at file offset `0x173d6`.  `posX/Y/Z` appear in a compact
descriptor table around file offset `0x16790`.

## Waveform Table

The v1.6.51 motor firmware contains a 512-entry float32 sine table:

- File offset: `0x167d8`
- Runtime address: `0x0801e7d8`
- Entries: `512`
- Max error vs `sin(2*pi*i/512)`: about `3.3e-8`

Key samples:

| Index | Value |
| ---: | ---: |
| 0 | `0.0` |
| 128 | `1.0` |
| 256 | `0.0` |
| 384 | `-1.0` |
| 511 | `-0.01227154` |

This is probably the electrical phase waveform basis used by the motor MCU.
The 512-sample resolution is a concrete design clue for a Klipper-side
implementation.

## Current Working Model

Anycubic's system appears to split responsibilities like this:

1. Avata host/UI owns the calibration workflow, progress, and user prompts.
2. Avata host emits script/G-code-like commands:
   - `ACTIVE_NOISE_REDUCTION_ENABLE ...`
   - `ACTIVE_NOISE_REDUCTION ...`
   - `ACTIVE_NOISE_REDUCTION_ARC ...`
3. Motion is driven through linear and arc sweeps over configured speed/count
   ranges.
4. The motor MCU owns realtime current waveform shaping and persistent
   harmonic/error tables.
5. The final artifacts are likely stored as EasyFlash env records:
   - `X_Harmonic_Table`
   - `Y_Harmonic_Table`
   - `Z_Harmonic_Table`
   - `error_rate`

This is very close in spirit to Bambu/Prusa active motor noise calibration:
measure vibration while exciting the axis, fit a periodic correction, and
apply the correction in realtime to the motor phase/current waveform.

## Implications for Proper Klipper on U1

U1 can implement the same class of feature without Anycubic's separate motor
MCU because X/Y use TMC2240 and support `DIRECT_MODE`.  The hard part is
realtime synchronization with Klipper step generation.

Suggested path:

1. Measurement layer:
   - Use the existing U1 LIS2DW accelerometer path for vibration amplitude.
   - Keep SG4 readback as a slow fallback/debug channel.
   - Run linear X/Y sweeps and optional arc sweeps over a speed range similar
     to Anycubic's `[5, 15]`.
2. Analysis layer:
   - Extend the current circular-mean/fundamental estimator into explicit DFT
     bins.
   - Prioritize harmonics 2 and 4, matching Prusa's production findings.
   - Store `{harmonic, magnitude, phase}` per axis and direction.
3. Runtime layer:
   - Generate a 512- or 1024-entry corrected current LUT:
     `delta(theta) = sum(a_n * sin(n*theta + phi_n))`.
   - Apply corrected `(I_A, I_B)` through TMC2240 `DIRECT_MODE` in sync with
     the stepper phase.
   - Prototype with low-speed calibration moves first; then decide whether the
     MCU can own the direct-mode waveform updates tightly enough for printing.
4. Persistence:
   - Store correction tables in Klipper config or a separate calibration blob.
   - Use names that mirror the concept, not Anycubic's env keys:
     `x_harmonic_table`, `y_harmonic_table`, per-direction variants if needed.

Open questions:

- What is the exact binary layout of `X_Harmonic_Table` in EasyFlash after a
  completed calibration?
- Does Anycubic store coefficients, a full LUT, or compressed error-rate data?
- Are linear and arc calibrations fitting separate models, or is arc only an
  acceptance/stability test?
- What motor-MCU command payload ultimately corresponds to Avata's
  `ACTIVE_NOISE_REDUCTION_*` script commands?

