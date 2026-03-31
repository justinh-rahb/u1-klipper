# Verification Summary

## Statistics

- **Total claims verified:** 83
- **CONFIRMED:** 64 (77%)
- **INCORRECT:** 8 (10%)
- **INCOMPLETE:** 6 (7%)
- **MISLEADING:** 1 (1%)
- **UNVERIFIABLE:** 4 (5%)

---

## Document Confidence Assessments

| Document | Claims Checked | Issues Found | Confidence |
|----------|---------------|--------------|------------|
| `src-at32f403a.md` | 10 | 2 (INCORRECT×1, INCOMPLETE×1) | Medium |
| `src-at32f415rc.md` | 8 | 3 (INCORRECT×1, INCOMPLETE×2) | Medium |
| `src-inductance_coil.md` | 12 | 3 (INCORRECT×2, INCOMPLETE×1) | Medium |
| `src-power_loss_check.md` | 12 | 0 | High |
| `mcu/hal-at32f403a.md` | 3 | 0 | High |
| `mcu/hal-at32f415.md` | 3 | 0 | High |
| `mcu/build-system.md` | 8 | 0 | High |
| `mcu/architecture-overview.md` | 3 | 0 | High |
| `triage/README.md` (Tier 1) | 18 | 2 (INCORRECT×2) | Medium |
| `triage/README.md` (Tier 2) | 5 | 0 | High |
| `triage/README.md` (counts) | 5 | 2 (INCORRECT×2) | Low |
| `klippy-reactor.md` | 1 | 0 | High |
| `klippy-mcu.md` | 1 | 0 | High |
| `klippy-stepper.md` | 1 | 0 | High |
| `klippy-toolhead.md` | 1 | 0 | High |
| `klippy-webhooks.md` | 1 | 0 | High |
| `extras-inductance_coil.md` | 3 | 0 | High |
| `extras-power_loss_check.md` | 3 | 0 | High |
| `kinematics-idex_modes.md` | 5 | 1 (MISLEADING×1) | Medium |
| `research/README.md` | 2 | 1 (INCORRECT×1) | Medium |

---

## Most Significant Errors

These INCORRECT findings would cause real engineering harm if acted on without correction:

### 1. `src-at32f415rc.md` — Flash size stated as 128 KB; actual is 256 KB
**File:** `research/modules/src-at32f415rc.md`
**Impact:** **HIGH.** Any engineer sizing firmware, allocating flash sectors, or
evaluating flash wear from the research doc will design for 128 KB and be wrong
about the available headroom by 2×. The companion claim that power-loss flash
sectors `0x0801F800`/`0x0801FC00` are "at the top of the flash range" is also
wrong — they sit at the 128 KB halfway point of a 256 KB device.
**Correct value:** 256 KB (`FLASH_SIZE = 0x40000`), per `src/stm32/Kconfig:238`.

### 2. `src-at32f403a.md` — at32f403a_clock_setup described as DECL_INIT; it is not
**File:** `research/modules/src-at32f403a.md`
**Impact:** **MEDIUM.** An engineer searching for the boot-time initialization
sequence will look for a DECL_INIT registration that does not exist. The actual
call site is `src/stm32/stm32f1.c:281`. If this error propagates to an upstream
contribution or integration guide, it will misdirect debugging of initialization
ordering issues.
**Correct call site:** `src/stm32/stm32f1.c:279–284` (conditional block).

### 3. `src-inductance_coil.md` — Calibration timer described as "10 kHz"; it is configurable
**File:** `research/modules/src-inductance_coil.md`
**Impact:** **MEDIUM.** The 10 kHz figure (from `power_loss_check.c`) should not
appear in inductance_coil.c documentation. An engineer configuring frequency
measurement parameters or debugging timer conflicts would use the wrong reference
frequency. The calibration timer period is determined by the `freq_cal_cycle`
command parameter.

### 4. `src-inductance_coil.md` — TMR5 (Timer 5) omitted from timer conflict analysis
**File:** `research/modules/src-inductance_coil.md`
**Impact:** **MEDIUM.** The doc warns about Timer 2 conflicts only. A firmware
integrator adding a new peripheral that uses Timer 5 will not be warned, and the
resulting conflict (both peripherals competing for `INPUT_CAPTURE_CAL_CRM_TIM`)
will manifest as timing errors.

### 5. `triage/README.md` — C36 `static_digital_output.py` listed as absent (Tier 1 Drop)
**File:** `research/triage/README.md`
**Impact:** **LOW-MEDIUM.** An engineer acting on this triage item will attempt
to "copy from upstream" a file that already exists in the fork. At worst this
would silently overwrite a fork-modified version of the file with the upstream
version, discarding any U1-specific changes in it.

### 6. `src-at32f415rc.md` / `src-at32f403a.md` — usb_clock48m_select parameter ignored
**File:** `research/modules/src-at32f415rc.md`
**Impact:** **LOW.** The `clk_s` parameter of `at32f415rc.c`'s
`usb_clock48m_select()` is completely unused. The docs describe the function as
"setting USB clock divider based on system_core_clock" (correct) but omit that
the parameter is dead code. This could mislead a developer attempting to add HICK
fallback support to the AT32F415 by passing `USB_CLK_HICK` — the parameter will
be silently ignored.

---

## Recommended Follow-up

### Documents that can be trusted (High confidence, no issues found):
- `src-power_loss_check.md` — all constants, structs, functions, and MCU commands confirmed
- `mcu/hal-at32f403a.md` — SDK version, module count confirmed
- `mcu/hal-at32f415.md` — SDK version, module count confirmed
- `mcu/build-system.md` — all Kconfig/Makefile claims confirmed
- `mcu/architecture-overview.md` — clock topology, MCU string claims confirmed
- `klippy-*.md` core module docs — all spot-checked claims confirmed
- `extras-inductance_coil.md`, `extras-power_loss_check.md` — class/command names confirmed
- Triage Tier 2 items — all four absence claims confirmed

### Documents needing correction before use:
- **`src-at32f415rc.md`** — Flash size error (128→256 KB) and `usb_clock48m_select`
  parameter note must be corrected before this document is used for firmware
  integration work.
- **`src-at32f403a.md`** — DECL_INIT description and `mcu_uart_gpio_remap` guard
  must be corrected.
- **`src-inductance_coil.md`** — TMR5 addition, calibration timer frequency, and
  `inductance_coil_dev_init` description all require correction.
- **`triage/README.md`** — C36 classification and Tier 1 count must be corrected;
  Tier 3/4 counts methodology should be clarified (row count vs file count).
- **`research/README.md`** — Removed-extras count must be updated from 15 to 14.

### Documents needing a second verification pass:
- `kinematics-idex_modes.md` — The INACTIVE mode finding may propagate to
  related kinematics docs. Check whether other kinematics docs also describe
  INACTIVE as "removed" when it is used internally.
- Triage Tier 3/4 counts — The counting methodology (rows vs individual files)
  is inconsistent. A full reconciliation would require enumerating every file
  implied by multi-file rows like "D1–D6", "E3–E13", "C21 ~65 extras".
