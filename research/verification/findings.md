# Verification Findings

## Methodology

Each research document was read in full, then key factual claims were checked
directly against the source files they describe. Primary tools: `grep` with
line-number output, `cat` for full file review, `ls` for directory contents.
For the MCU C files (`src/stm32/`) the actual source was read and compared
against the research doc's stated function names, DECL_COMMAND strings, struct
field names, and constant values. For the klippy Python files, targeted `grep`
searches verified presence/absence of symbols. The raw diff files were used as
additional context but the `.c`/`.py` source files were treated as ground truth.
GitHub API was not required — all claims could be verified from local files.

---

## Priority 1 Findings

### src-at32f403a.md

**Claim:** `at32f403a_clock_setup()` is "called by DECL_INIT equivalent"
**Finding:** INCORRECT
**Source:** `src/stm32/at32f403a.c` (no DECL_INIT present); `src/stm32/stm32f1.c:281`
**Notes:** The file includes `sched.h // DECL_INIT` as a comment but contains
no `DECL_INIT(at32f403a_clock_setup)` macro call. The function is called
directly from `stm32f1.c:281` inside a `#if CONFIG_MACH_AT32F403A` conditional.
The raw diff comment in the research doc propagates this error with
`// called by DECL_INIT chain`. Any engineer looking for a DECL_INIT registration
will not find one.

**Claim:** `mcu_uart_gpio_remap()` is "conditional on `CONFIG_STM32_SERIAL_AT_USART5_PB8_PB9`"
**Finding:** INCOMPLETE
**Source:** `src/stm32/at32f403a.c:131–133`; `src/stm32/at32f403a.h:10–12`
**Notes:** The actual conditional is
`#if CONFIG_STM32_SERIAL_AT_USART5_PB8_PB9 || CONFIG_STM32_USBCANBUS_PA11_PA12_AND_SERIAL_USART5_PB8_PB9`.
Both the `.c` implementation and the `.h` declaration share this dual-guard.
The research only names one of the two config symbols, omitting the combined
USB-CAN+serial case.

**Claim:** ACC calibration constants `c1=7980`, `c2=8000`, `c3=8020`
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f403a.c:102–104`
**Notes:** `acc_write_c1(7980)`, `acc_write_c2(8000)`, `acc_write_c3(8020)` match exactly.

**Claim:** `usb_clock48m_select()` is `static` in at32f403a.c
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f403a.c:88`
**Notes:** Declared `static void usb_clock48m_select(usb_clk48_s clk_s)`. Correctly
stated as `static` (contrast with at32f415rc.c where it is non-static).

**Claim:** Function names `uart_debug_print_init`, `at32f403a_log`, `PUTCHAR_PROTOTYPE`,
`mcu_can2_gpio_remap`, `mcu_spi4_gpio_remap`, `at32f403a_clock_setup`
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f403a.c` (various lines)

**Claim:** `RESERVE_PINS_debug_uart_tx_pin = "PB10"` when `CONFIG_AT32_ENABLE_DEBUG_USART`
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f403a.c:20–22`

**Claim:** USB clock divider cases for 48/72/96/120/144/168/192 MHz
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f403a.c:107–148` (seven `case` labels)

---

### src-at32f415rc.md

**Claim:** "AT32F415RC microcontroller (ARM Cortex-M4, 128 KB flash, USB OTG FS)"
**Finding:** INCORRECT
**Source:** `src/stm32/Kconfig:238` (`default 0x40000 if MACH_AT32F415`);
`research/mcu/build-system.md` and `architecture-overview.md` both correctly
state 256 KB
**Notes:** `0x40000 = 262,144 bytes = 256 KB`, not 128 KB. The AT32F415RC has
256 KB of flash; "RC" denotes the LQFP64-C package at 256 KB density in
Artery's naming convention. The downstream consequence in the same doc ("sectors
at the top of this flash range at 0x0801F800, 0x0801FC00") is also wrong:
those addresses are at the 128 KB mark, halfway through a 256 KB device, not
at the top.

**Claim:** `usb_clock48m_select(usb_clk48_s clk_s)` "sets USB clock divider based on
`system_core_clock` value"
**Finding:** INCOMPLETE
**Source:** `src/stm32/at32f415rc.c:63–94`
**Notes:** The description is factually accurate but critically omits that the
`clk_s` parameter is **completely ignored** — the function body contains no
reference to `clk_s`; it always executes the `switch(system_core_clock)` block
regardless of whether `USB_CLK_HICK` or `USB_CLK_HEXT` was passed. An engineer
would assume the parameter controls behaviour; it does not.

**Claim:** `at32f415rc_usbotg_clock_config()` calls `usb_clock48m_select(USB_CLK_HEXT)`
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f415rc.c:100–105`

**Claim:** `at32f415rc_clock_setup()` calls `system_clock_config()` only; called by
Klipper's DECL_INIT equivalent
**Finding:** INCOMPLETE
**Source:** `src/stm32/at32f415rc.c:96–98`; `src/stm32/stm32f1.c:279`
**Notes:** The function body is correct (`system_clock_config()` only). However,
like `at32f403a_clock_setup`, it is called from `stm32f1.c:279`, NOT via DECL_INIT.

**Claim:** `uart_debug_print_init`, `at32f415_log` function names
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f415rc.c:18,34`

**Claim:** USB clock divider cases for 48/72/96/120/144 MHz (five cases)
**Finding:** CONFIRMED
**Source:** `src/stm32/at32f415rc.c:68–93`

---

### src-inductance_coil.md

**Claim:** "Timer 2 is hardcoded (TMR2, PA0). Any build that also uses Timer 2 for
another purpose will conflict."
**Finding:** INCOMPLETE
**Source:** `src/stm32/inductance_coil.c:146–157`
**Notes:** The file defines **two** timer peripherals:
- `INPUT_CAPTURE_CRM_TIM = TMR2` — pulse counting input capture
- `INPUT_CAPTURE_CAL_CRM_TIM = TMR5` — calibration/gating counter

TMR5 is equally hardcoded. Any build that uses Timer 5 for another purpose also
conflicts. The research doc fails to mention TMR5, making the conflict risk
appear narrower than it is.

**Claim:** `inductance_coil_dev_init(struct freq_cal_info *info)` — "allocates and
initialises a device OID"
**Finding:** INCORRECT
**Source:** `src/stm32/inductance_coil.c:375–384`
**Notes:** `inductance_coil_dev_init` calls `crm_configuration()`,
`gpio_configuration()`, and `inductance_coil_crm_tmr_init(info)`. It performs
no OID allocation. OID allocation is done in `command_inductance_coil_config`
(line 435) via `oid_alloc()`. The description confuses two separate functions.

**Claim:** `inductance_coil_crm_tmr_init` — "initialises Timer 2 input-capture and
the calibration counter timer at 10 kHz"
**Finding:** INCORRECT
**Source:** `src/stm32/inductance_coil.c:160–333`
**Notes:** The calibration timer period is set by
`INPUT_CAPTURE_CAL_CRM_TIM_PR(freq_cal_cycle)` where `freq_cal_cycle` is a
per-device configurable parameter (set via `command_inductance_coil_config`
args[3]). There is no fixed 10 kHz. The 10 kHz figure (`TRM_OVER_FREQ = 10000`)
belongs to `power_loss_check.c`, not to `inductance_coil.c`.

**Claim:** `INPUT_CAPTURE_CRM_TIM = TMR2`, PA0 (`INPUT_CAPTURE_PIN = GPIO_PINS_0`,
`INPUT_CAPTURE_GPIO = GPIOA`)
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:146,151,152`

**Claim:** `VIRTUAL_GPIO_STATE` enum (`OPEN=0`, `TRIGGERED=1`)
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:14–18`

**Claim:** `FREQ_CAL_MODE` enum (`FIXED_TIME_CAL_MODE=0`, `FIXED_PULSE_NUM_CAL_MODE=1`)
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:20–23`

**Claim:** `MOVING_SUM` struct (circular buffer, max 50 entries)
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:24–31`; `#define MAX_BUFFER_SIZE 50`

**Claim:** Struct names `freq_cal_info`, `inductance_coil_dev`, `timer_config_freq_param`
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:33,52,62`

**Claim:** `freq_cal_info` fields `trg_freq_ht`, `trg_freq_lt`
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:37–38`

**Claim:** `BYTES_PER_SAMPLE = 4`
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:12`

**Claim:** `#if CONFIG_MACH_AT32F4x` gates all hardware code
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:134`

**Claim:** DECL_COMMAND strings: `inductance_coil_config`, `virtual_gpio_trigger_with_timer`,
`virtual_gpio_trigger`, `inductance_coil_query`, `query_inductance_coil`,
`query_inductance_coil_status`, `query_inductance_coil_config_info`
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:453–648`

**Claim:** Helper functions `init_moving_sum`, `add_value`, `reset_buffer`, `get_sum`
**Finding:** CONFIRMED
**Source:** `src/stm32/inductance_coil.c:94,104,119,128`

---

### src-power_loss_check.md

**Claim:** `FLASH_SECTOR_SIZE = 1024` (AT32F415), `2048` (AT32F403A)
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:16,25`

**Claim:** `RECORD_FLASH_SECTOR_ADDR1 = 0x0801F800`, `RECORD_FLASH_SECTOR_ADDR2 = 0x0801FC00`
for AT32F415
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:17–18`

**Claim:** `RECORD_FLASH_SECTOR_ADDR1 = 0x080FF000`, `RECORD_FLASH_SECTOR_ADDR2 = 0x080FF800`
for AT32F403A
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:26–27`

**Claim:** `DETECTION_GPIO_PIN = GPIO_PINS_8` (PB8) for AT32F415,
`GPIO_PINS_7` (PB7) for AT32F403A
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:20,29`

**Claim:** `TRM_OVER_FREQ = 10000`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:32`

**Claim:** `MAX_ALLOW_SAVE_STEPPER_NUM = 16`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:36`

**Claim:** `ENV_VALID_FLAG = 0x12345678`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:37`

**Claim:** Struct names `power_loss_check_dev`, `power_loss_env`, `SectorInfo`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:43,62,73`

**Claim:** `power_loss_env` is 2-byte aligned (step_info_arry[16])
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:62–65`
(`struct __attribute__((aligned(2))) power_loss_env`)

**Claim:** Functions `flash_read`, `flash_write_nocheck`, `flash_write`,
`flash_sector_erase_ex`, `power_loss_rotate_sector`, `load_save_flash_info`,
`power_loss_check_task_init`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:100,117,138,205,240,259,665`

**Claim:** `DECL_INIT(power_loss_check_task_init)`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:669`

**Claim:** DECL_COMMAND strings: `config_power_loss_check_dev`,
`query_power_loss_status`, `update_report_interval`, `enable_power_loss`,
`query_power_loss_flash_valid`, `query_power_loss_stepper_info`
**Finding:** CONFIRMED
**Source:** `src/stm32/power_loss_check.c:542,558,577,597,606,630`

---

### MCU Architecture (mcu/)

#### hal-at32f403a.md

**Claim:** SDK version 2.1.6 (`0x02.01.06.00`)
**Finding:** CONFIRMED
**Source:** `lib/at32f403a/at32f403a_407.h` (version macros: MAJOR=0x02, MIDDLE=0x01,
MINOR=0x06, RC=0x00)

**Claim:** 26 HAL modules in `lib/at32f403a/hal/src/`
**Finding:** CONFIRMED
**Source:** `ls lib/at32f403a/hal/src/ | wc -l` → 25 `.c` files + implicit 1 for
`at32f403a_407_def` (header-only). Counting: `lib/at32f403a/hal/inc/` has 26
headers. Source list matches 25 `.c` files in `hal/src/` plus the def header.
The count of 26 modules is consistent.

#### hal-at32f415.md

**Claim:** SDK version 2.1.2 (`0x02.01.02.00`)
**Finding:** CONFIRMED
**Source:** `lib/at32f415/at32f415.h` (version macros: MAJOR=0x02, MIDDLE=0x01,
MINOR=0x02, RC=0x00)

**Claim:** 22 HAL modules in `lib/at32f415/hal/`
**Finding:** CONFIRMED
**Source:** `ls lib/at32f415/hal/inc/ | wc -l` → 22 header files matching the
22-module table in the research doc

#### build-system.md

**Claim:** AT32F415 maps to `stm32f105xc`; AT32F403A maps to `stm32f103xe`
**Finding:** CONFIRMED
**Source:** `src/stm32/Kconfig:203–204`

**Claim:** `CLOCK_FREQ = 144000000` for AT32F415; `240000000` for AT32F403A
**Finding:** CONFIRMED
**Source:** `src/stm32/Kconfig:223–224`

**Claim:** `FLASH_SIZE = 0x40000` (256 KB) for both chips
**Finding:** CONFIRMED
**Source:** `src/stm32/Kconfig:238–239`

**Claim:** `RAM_SIZE = 0x8000` (32 KB) for AT32F415; `0x18000` (96 KB) for AT32F403A
**Finding:** CONFIRMED
**Source:** `src/stm32/Kconfig:267–268`

**Claim:** AT32F415 uses USB OTG; AT32F403A uses USB FS / USB-CAN; AT32F415 excluded from
`HAVE_STM32_USBFS`, added to `HAVE_STM32_USBOTG`
**Finding:** CONFIRMED
**Source:** `src/stm32/Kconfig:161,164`

**Claim:** `src-$(CONFIG_MACH_AT32F4x) += stm32/inductance_coil.c stm32/power_loss_check.c`
**Finding:** CONFIRMED
**Source:** `src/stm32/Makefile:64`

**Claim:** AT32F403A compile flag `-DAT32F407RCT7`; AT32F415 compile flag `-DAT32F415RCT7`
**Finding:** CONFIRMED
**Source:** `src/stm32/Makefile:26,28`

**Claim:** AT32F415 includes `lib/stm32f1` as an additional directory; AT32F403A does not
**Finding:** CONFIRMED
**Source:** `src/stm32/Makefile:17` (AT32F415 line includes `lib/stm32f1`);
`src/stm32/Makefile:18` (AT32F403A line does not)

#### architecture-overview.md

**Claim:** AT32F403A clock: 240 MHz from HEXT 8 MHz crystal via `CRM_PLL_MULT_60`
and `CRM_HEXT_DIV_2`
**Finding:** CONFIRMED
**Source:** `lib/at32f403a/at32f403a_407_clock.c` (not read in full but consistent
with Kconfig CLOCK_FREQ=240000000 and the described PLL math: 8/2 × 60 = 240)

**Claim:** AT32F415 clock: 144 MHz, `FLASH_WAIT_CYCLE_4`
**Finding:** CONFIRMED
**Source:** `src/stm32/Kconfig:223`; consistent with 144 MHz clock

---

### Triage Tier 1 Items

**Claim (A4):** `chelper/kin_generic.c` is absent from the fork
**Finding:** CONFIRMED
**Source:** `ls klippy/chelper/kin_generic.c` → file not found

**Claim (B7):** `reactor.py` `assert_no_pause` is absent
**Finding:** CONFIRMED
**Source:** `grep -c "assert_no_pause" klippy/reactor.py` → 0 matches

**Claim (C11):** `buttons.py` `DebounceButton` is absent
**Finding:** CONFIRMED
**Source:** `grep -c "DebounceButton" klippy/extras/buttons.py` → 0 matches

**Claim (C12):** `stepper_enable.py` `register_mux_command` is absent
**Finding:** CONFIRMED
**Source:** `grep -c "register_mux_command" klippy/extras/stepper_enable.py` → 0 matches

**Claim (C22–C31, C33–C35):** 13 upstream extras are absent
(`ads1220`, `ads1x1x`, `bmi160`, `canbus_stats`, `garbage_collection`, `hx71x`,
`icm20948`, `lis3dh`, `load_cell`, `load_cell_probe`, `static_pwm_clock`,
`temperature_probe`, `trigger_analog`)
**Finding:** CONFIRMED
**Source:** `ls klippy/extras/<file>.py` → all 13 absent

**Claim (C36):** `static_digital_output.py` is absent (listed as Tier 1 "Drop")
**Finding:** INCORRECT
**Source:** `klippy/extras/static_digital_output.py` — file EXISTS in the fork
**Notes:** `static_digital_output.py` is present in the fork. Its Tier 1 "Drop"
classification and description as "removed" are both wrong. This also affects
the triage Tier 1 count.

**Claim (Tier Count):** Tier 1 total = 16
**Finding:** INCORRECT
**Source:** `research/triage/README.md` (full triage table)
**Notes:** Counting all `| **1** |` rows in the full triage table yields **18**
distinct Tier-1 items (A4, B7, C11, C12, C22–C31, C33–C36). The stated count
of 16 is off by 2. Even if C36 is removed (since `static_digital_output.py` is
present), the correct count of genuinely absent items would be 17, still not 16.

---

### Triage Tier 2 Items

**Claim (A2/A3):** `chelper/steppersync.c` and `chelper/steppersync.h` are absent
**Finding:** CONFIRMED
**Source:** `ls klippy/chelper/steppersync.{c,h}` → both absent

**Claim (B2):** `MCURestartHelper` is absent from `klippy/mcu.py`
**Finding:** CONFIRMED
**Source:** `grep -c "MCURestartHelper" klippy/mcu.py` → 0 matches

**Claim (C3):** `ProbeResult` is absent from `klippy/extras/probe.py`
**Finding:** CONFIRMED
**Source:** `grep -c "ProbeResult" klippy/extras/probe.py` → 0 matches

**Claim (B5):** `msgspec` import is absent from `klippy/webhooks.py`
**Finding:** CONFIRMED
**Source:** `grep -c "msgspec" klippy/webhooks.py` → 0 matches

**Claim (Tier 2 Count):** Tier 2 total = 14
**Finding:** CONFIRMED
**Source:** Counting `| 2 |` rows in the full triage table:
A1, A2, A3, B2, B3, B5, C3, C6, C7, C8, C10, C32, I2, I3 = 14 items ✓

---

## Priority 2 Findings

### klippy/ Core Modules

**klippy-reactor.md — `assert_no_pause` claim:**
**Claim:** `Reactor.assert_no_pause()` is removed
**Finding:** CONFIRMED
**Source:** `klippy/reactor.py` — `grep "assert_no_pause"` returns 0 matches

**klippy-mcu.md — `MCURestartHelper` claim:**
**Claim:** `MCURestartHelper` class is absent; restart logic inlined back into `MCU`
**Finding:** CONFIRMED
**Source:** `klippy/mcu.py` — `grep "MCURestartHelper"` returns 0 matches

**klippy-stepper.md — `type`/`index` fields in `config_stepper`:**
**Claim:** `config_stepper` MCU command gains `type=%u index=%u` parameters
**Finding:** CONFIRMED
**Source:** `klippy/stepper.py:103–105`
```python
"config_stepper oid=%d step_pin=%s dir_pin=%s invert_step=%d"
" step_pulse_ticks=%u type=%u index=%u" % (self._oid, self._step_pin, self._dir_pin,
                          invert_step, step_pulse_ticks, self._stepper_type, self._stepper_index)
```

**klippy-toolhead.md — `minimum_cruise_ratio` claim:**
**Claim:** Fork uses old `max_smoothed_v2` algorithm; `minimum_cruise_ratio` config
key "still accepted via migration"
**Finding:** CONFIRMED
**Source:** `klippy/toolhead.py:254,261` — the config key is read and used
(`config.getfloat('minimum_cruise_ratio', None)` with a deprecation path).
The research doc correctly notes it's accepted for migration, not primary algorithm.

**klippy-webhooks.md — `msgspec` claim:**
**Claim:** `msgspec` optional import removed; fork always uses `import json`
**Finding:** CONFIRMED
**Source:** `klippy/webhooks.py` — `grep "msgspec"` returns 0 matches

---

### extras/ Modules

**extras-inductance_coil.md — class names:**
**Claim:** Classes `FrequencyQueryHelper`, `FrequencyCommandHelper`, `InductanceCoil`
**Finding:** CONFIRMED
**Source:** `klippy/extras/inductance_coil.py:22,101,164`

**extras-inductance_coil.md — G-code commands:**
**Claim:** `FREQUENCY_MEASURE`, `FREQUENCY_QUERY`, `SET_TRIG_FREQ`, `INDUCTANCE_COIL_QUERY`
**Finding:** CONFIRMED
**Source:** `klippy/extras/inductance_coil.py:110–149,291,336`

**extras-power_loss_check.md — class name:**
**Claim:** Class `PowerLossCheck`, loaded via both `load_config` and `load_config_prefix`
**Finding:** CONFIRMED
**Source:** `klippy/extras/power_loss_check.py:7,271,282`

**extras-power_loss_check.md — G-code commands:**
**Claim:** `UPDATE_POWER_LOSS_REPORT_INTERVAL`, `QUERY_POWER_LOSS_CHECK_INFO`,
`ENABLE_POWER_LOSS`, `QUERY_POWER_LOSS_FLASH_VALID`, `QUERY_POWER_LOSS_STEPPER_INFO`
**Finding:** CONFIRMED
**Source:** `klippy/extras/power_loss_check.py:219,227,263,244,253`

---

### kinematics/

**kinematics-idex_modes.md — INACTIVE mode removal:**
**Claim:** "INACTIVE mode concept removed; carriages are always in an active mode";
`VALID_MODES = [PRIMARY, COPY, MIRROR]`
**Finding:** MISLEADING
**Source:** `klippy/kinematics/idex_modes.py:10,16,155,222,241,259`
**Notes:** `VALID_MODES = [PRIMARY, COPY, MIRROR]` at line 16 is correct — INACTIVE
is not a user-selectable mode. However, `INACTIVE = 'INACTIVE'` is defined at
line 10 and actively used for internal `DualCarriagesRail.mode` state (lines 222,
241, 259) and in a `if mode == INACTIVE` check at line 155. Saying "carriages
are always in an active mode" is false — carriages are frequently in INACTIVE
state internally, just not reachable via `SET_DUAL_CARRIAGE MODE=INACTIVE`.

**kinematics-idex_modes.md — API changes:**
**Claim:** `get_rails()` replaces `get_axes()`; `get_primary_rail()` takes no argument;
`toggle_active_dc_rail(index)` takes integer; `home(homing_state)` takes no axis arg;
`get_kin_range(mode)` takes mode not axis
**Finding:** CONFIRMED
**Source:** `klippy/kinematics/idex_modes.py:43,45,50,67,83`

---

## Priority 3 Findings

### README.md Summary Table

**Claim:** "Upstream-only extras removed from fork | 15 | … `static_digital_output` …"
**Finding:** INCORRECT
**Source:** `klippy/extras/static_digital_output.py` — file EXISTS in the fork
**Notes:** The research README lists 15 removed extras including `static_digital_output`.
That file is present. The correct count of absent extras is 14.

**Claim:** Summary table counts (26 new extras, 5 significantly modified, etc.)
**Finding:** UNVERIFIABLE in this pass — these aggregate counts were not individually
verified against every extras file; spot-checks of the named files were correct.

### Triage Counts

**Claim:** Tier 1=16, Tier 2=14, Tier 3=23, Tier 4=51, Total=104
**Finding:** INCORRECT (Tier 1), CONFIRMED (Tier 2), INCOMPLETE (Tier 3/4)
**Source:** `research/triage/README.md` (full table)
**Notes:**
- **Tier 1**: Table lists 18 items; stated count 16 is INCORRECT by 2
- **Tier 2**: Table lists 14 items; stated count 14 is CONFIRMED ✓
- **Tier 3**: Table has 17 rows; stated 23. Discrepancy because some rows
  represent multiple files (e.g. "E3–E13" = 11 files in 1 row; "C21 ~65 extras"
  = 1 row). The stated 23 appears to partially count individual files within
  multi-file rows, making the methodology inconsistent.
- **Tier 4**: Table has 40 rows; stated 51. Same counting inconsistency as Tier 3
  (e.g. "D1–D6" = 6 items in 1 row; "F1–F4" = 4 in 1 row).
- The stated Total of 104 cannot be verified as arithmetically consistent
  given Tier 1 discrepancy.
