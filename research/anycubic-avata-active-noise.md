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
- KS1M GoKlipper SWU:
  - `/Users/justinh/Downloads/KS1M_2.6.9.6.swu`
  - Extracted root: `/private/tmp/ks1m-root-2696`
  - Host binaries:
    - `/private/tmp/ks1m-root-2696/app/gklib`
    - `/private/tmp/ks1m-root-2696/app/K3SysUi`
  - KS1M motor firmware:
    - `/private/tmp/ks1m-root-2696/motor_firmware_v1.5.98_20260129.bin`
    - size: 87281 bytes
    - sha256:
      `ee8a1b0e239adbf4cf9f3eb28db3268d58006cc9495f3d632906db0272d0b312`
  - Version file: `2.6.9.6`
  - `k3c` version log:
    - branch: `refactor/reactor`
    - commit: `982a1ece`

The motor firmware vector table has initial SP in SRAM and reset vector
`0x08008199`, so the blob is linked at `0x08008000`.  Ghidra imports at
`0x08000000` are still useful for relative code, but absolute data pointers
need the `0x8000` adjustment.

## Hardware Clues

The Kobra X board photo shows a dedicated Artery MCU:

- Marking: `AT32F403ARGT7`
- Same AT32F403A family as the U1 mainboard MCU.
- The Kobra X / KS1M-class boards have a separate motor-driver/control section,
  consistent with Anycubic putting the tight realtime waveform work on a motor
  MCU instead of the weak Linux SoC.

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

All inspected motor firmware versions contain EasyFlash env strings for
persistent calibration/storage:

| Key | KS1M v1.5.98 | Kobra X v1.6.01 | S1 Max v1.6.51 |
| --- | ---: | ---: | ---: |
| `error_rate` | `0x15060` | `0x16e80` | `0x17010` |
| `error_rate_index` | `0x1506b` | `0x16e8b` | `0x1701b` |
| `PowerDown_data` | `0x1507c` | `0x16e9c` | `0x1702c` |
| `X_Harmonic_Table` | `0x1508b` | `0x16eab` | `0x1703b` |
| `Y_Harmonic_Table` | `0x1509c` | `0x16ebc` | `0x1704c` |
| `Z_Harmonic_Table` | absent | `0x16ecd` | `0x1705d` |
| `posX` | `0x150dd` | `0x16f0e` | `0x1709e` |
| `posY` | `0x150e2` | `0x16f13` | `0x170a3` |
| `posZ` | `0x150e7` | `0x16f18` | `0x170a8` |

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

All inspected motor firmware versions contain a 512-entry float32 sine table:

| Firmware | File offset | Runtime address | Max error |
| --- | ---: | ---: | ---: |
| KS1M v1.5.98 | `0x14828` | `0x0801c828` | `3.3e-8` |
| Kobra X v1.6.01 | `0x16648` | `0x0801e648` | `3.3e-8` |
| S1 Max v1.6.51 | `0x167d8` | `0x0801e7d8` | `3.3e-8` |

- Entries: `512`

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

## KS1M GoKlipper Host Findings

KS1M is useful because it is not Avata: the host side is GoKlipper, but the
ANC surface is very similar.  The firmware config exposes a dedicated motor
section:

```ini
[motor_extra]
axes_map:x,y,z
axes_id:0,1,2
device_type:NF038

[motor_anc]
speed_range: 50,300
move_range: 50,300
amplitude: 50
move_count: 8
arc_move_count: 2
circle_center:175,175
radius:150
```

The Go host binary contains full path and symbol names for the ANC module:

- `/data/liuxiaobo/k3_sys38/1.0/k3c/internal/pkg/motion/motor_anc.go`
- `k3c/internal/pkg/motion.NewMotorAnc`
- `(*MotorAnc).cmd_ACTIVE_NOISE_REDUCTION`
- `(*MotorAnc).cmd_ACTIVE_NOISE_REDUCTION_ARC`
- `(*MotorAnc).cmd_ACTIVE_NOISE_REDUCTION_ENABLE`
- `(*MotorAnc).cmd_ACTIVE_NOISE_REDUCTION_START`
- `(*MotorAnc).cmd_motor_anc`
- `(*MotorAnc).cmd_motor_anc_arc`
- `(*MotorAnc).cmd_motor_anc_enable`
- `(*MotorAnc).cmd_motor_anc_result`
- `(*MotorAnc).motor_anc_axis`
- `(*MotorAnc).motor_anc_arc`
- `(*MotorAnc).build_config`

The Go `.gopclntab` metadata gives concrete function PCs:

| Function | PC |
| --- | ---: |
| `NewMotorAnc` | `0x527d90` |
| `cmd_motor_anc_start` | `0x5287b4` |
| `do_motor_anc_start` | `0x528a54` |
| `motor_anc_axis` | `0x528f0c` |
| `motor_anc_arc` | `0x52904c` |
| `Get_status` | `0x5291d8` |
| `build_config` | `0x5294b0` |
| `cmd_ACTIVE_NOISE_REDUCTION` | `0x529670` |
| `cmd_motor_anc` | `0x529794` |
| `cmd_ACTIVE_NOISE_REDUCTION_ARC` | `0x52a498` |
| `cmd_motor_anc_arc` | `0x52a52c` |
| `cmd_ACTIVE_NOISE_REDUCTION_ENABLE` | `0x52a834` |
| `cmd_motor_anc_enable` | `0x52a9a0` |
| `Load_config_motor_anc` | `0x52ac38` |

The same binary exposes Klipper-style MCU command format strings:

- `motor_anc_state oid=%c axis=%c state=%c speed=%hu`
- `motor_anc_enable oid=%c axis=%c is_arc=%c enable=%c`
- `move_count oid=%c queue_size=%c x_use=%c y_use=%c z_use=%c`
- `query_move_count_cmd`
- `get_move_count_event`
- `query_sensor_end_cmd`
- `motion/motor_anc_result`

It also has debug strings that look like thin send/receive plumbing:

- `[MotorAnc] motor_anc_state_cmd - OID: %d, AxisIndex: %d, State: %d, Speed: %f`
- `[MotorAnc] motor_anc_enable_cmd - OID: %d, AxisIndex: %d, IsArc: %d, Enable: %d`

Targeted disassembly supports the thin-shim read:

- `cmd_ACTIVE_NOISE_REDUCTION` parses `AXIS` and `SPEED`, then calls
  `cmd_motor_anc`.
- `cmd_ACTIVE_NOISE_REDUCTION_ARC` parses arc parameters and calls
  `cmd_motor_anc_arc`.
- `cmd_ACTIVE_NOISE_REDUCTION_ENABLE` parses `AXIS`, `IS_ARC`, and `ENABLE`,
  then calls `cmd_motor_anc_enable`.
- `motor_anc_axis` loops over `move_count`/speed and calls `cmd_motor_anc`.
- `motor_anc_arc` loops over arc moves and calls `cmd_motor_anc_arc`.
- `cmd_motor_anc_enable` formats/sends `motor_anc_enable oid=%c axis=%c
  is_arc=%c enable=%c` and emits the `[MotorAnc] motor_anc_enable_cmd` debug
  string.
- `cmd_motor_anc` formats/sends `motor_anc_state oid=%c axis=%c state=%c
  speed=%hu` and emits the `[MotorAnc] motor_anc_state_cmd` debug string.
- `cmd_motor_anc_arc` also references `G3 I%v J%v F%v`, so the arc stage
  appears to be host-generated motion plus motor-MCU state commands, with no
  evidence of a host-side DSP solve in this path.

The host binary does contain FFT, PSD, and vector math code, but those symbols
are under `k3c/internal/pkg/motion/vibration`:

- `ShaperCalibrate._psd`
- `ShaperCalibrate.Calc_freq_response`
- `ShaperCalibrate.Fit_shaper`
- `common/utils/maths.Rfft`
- `common/utils/maths.Rfftfreq`
- `common/utils/maths.Conjugate`
- `common/utils/maths.Outer`
- `common/utils/maths.Arange`

So far there is no string/symbol evidence that `motor_anc.go` performs
host-side harmonic fitting, DFT, or waveform synthesis.  The obvious read is
that GoKlipper parses config and G-code, runs the sweep workflow, sends compact
state/enable commands to the motor MCU, and listens for queue/sensor/result
events.

The KS1M UI also treats ANC as a separate calibration surface:

- `motion/motor_anc`
- `MotorAncToolsFeedback`
- `MotorAncGuideFeedback`
- "Active noise reduction is about to begin."
- "Active noise reduction is in progress"
- "Active noise reduction has completed."

This strongly corroborates the "thin host shim, smart motor MCU" model.

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

This is very close in spirit to Bambu-style active motor noise calibration:
measure vibration while exciting the axis, fit a periodic correction, and
apply the correction in realtime to the motor phase/current waveform.  It is
also adjacent to Prusa's current-level phase-stepping work, while remaining
separate from Prusa's more common trajectory-level Input Shaper workflow.

## Architecture Comparison

Three vendors converge on similar "quiet motor" marketing with three
genuinely different implementations:

- **Bambu**: appears to avoid the same TMC-black-box constraint for this
  feature.  If their motion controller owns the relevant current-control path,
  harmonic correction can be integrated into math already happening in that
  timing domain.  No obvious bolt-on protocol seam is exposed.
- **Prusa**: TMC drivers plus Marlin-derived firmware.  Their public
  ecosystem has both trajectory-level Input Shaper work and current-level
  phase-stepping work.  The important architectural distinction here is that
  the driver interface and motion code live in the same MCU domain, so this
  class of current shaping does not inherently require a separate motor MCU.
- **Anycubic**: TMC as a black box, no clean hook for arbitrary current
  vectors short of DIRECT_MODE streaming.  Rather than fight determinism
  on the main GD32F303 (already carrying gcode, step generation, comms,
  UI), the harmonic correction runs on a separate motor MCU that owns
  that timing domain outright.

## Third-Party IP Hypothesis

Several signals suggest the motor-MCU firmware isn't Anycubic's own DSP
work but an integrated third-party module:

- **MCU choice is out of pattern.**  Anycubic reaches for the GD32F303
  almost universally.  Picking an Artery AT32F403A only for the motor
  subsystem, with the datasheet highlighting DSP instructions "for
  efficient signal processing", reads more like a vendor bringing their
  own reference firmware on pinned silicon than a deliberate Anycubic
  architecture choice.
- **Naming is generic.**  `motoranc` and `MotorAnc` don't match the rest
  of the Anycubic namespace conventions — looks like the internals of a
  wrapped vendor SDK that didn't get renamed.
- **Code style differs.**  The seam between `avata_main` and the
  motor-MCU protocol reads like an IP boundary, not an internal API
  Anycubic designed.
- **KS1M backport is the strongest evidence.**  ANC was ported to a
  single EOL K3-line printer (KS1M, Go-based) alongside the K4/Avata
  (C++).  Writing a DFT/harmonic-fit/waveform-shaping pipeline twice,
  in two languages, for one obsolete SKU, is a lot of engineering for
  questionable ROI.  But if the intelligence lives on the motor MCU and
  both host stacks are just command/protocol shims, "adding support"
  collapses to wiring up UART commands.  Cheaply explains both the
  backport and the consistent quality across product lines that share
  basically nothing else architecturally.

**Testable prediction**: if this theory is right, the ANC-related code
paths in the KS1M Go host and the Avata C++ host should look suspiciously
thin and near-identical in structure — command marshaling and status
parsing, no actual math.  If either host contains real harmonic-fitting
logic, the theory is falsified.

The KS1M `gklib` pass supports this prediction: ANC has its own Go module and
MCU command strings, while the obvious signal-processing code belongs to
input-shaper/resonance calibration, not `motor_anc.go`.

The practical consequence for U1: we're not reverse-engineering a
coherent Anycubic design philosophy, we're reverse-engineering a chip
vendor's demo that got slotted into the product.  Our own implementation
doesn't owe it any structural resemblance — the split we choose can
follow what fits Klipper's execution model, not what fit Anycubic's IP
integration constraints.

## Implications for Proper Klipper on U1

U1 can implement the same class of feature without Anycubic's separate motor
MCU because X/Y use TMC2240 and support `DIRECT_MODE`.  The hard part is
realtime synchronization with Klipper step generation.  Prusa's shipping
DIRECT_MODE-style current work on Marlin-derived firmware is a decent
existence proof that this is viable in a shared-domain architecture —
Klipper's MCU-side timing model, built around precise scheduled events,
is arguably better suited to it than Marlin's, not worse.

Note also the trust boundary: interfacing with an Anycubic motor MCU
would mean handing realtime current control to a black box running its
own fault-monitoring and control law, with no visibility into either.
That is a materially different risk profile than a LUT we compute and
load ourselves — worth remembering if the topic of piggybacking on
Anycubic hardware ever comes up.

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
- Decompile the KS1M `MotorAnc` Go functions enough to confirm call flow and
  payload construction.  Current string/symbol evidence already points to a
  thin command/protocol shim, but this would firm up the exact sequence.
