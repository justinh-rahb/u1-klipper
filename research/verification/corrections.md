# Corrections

Issues classified as INCORRECT, INCOMPLETE, or MISLEADING. Each entry gives
the original text, what the code actually says, and the source location.

---

## src-at32f403a.md

### at32f403a_clock_setup is not registered via DECL_INIT

**Finding:** INCORRECT
**Original text (Summary section):**
> `at32f403a_clock_setup()` called by `DECL_INIT` equivalent to set system clock and USB clock

**Original text (Raw Diff comment):**
```c
+void at32f403a_clock_setup(void);  // called by DECL_INIT chain
```

**Corrected text:**
`at32f403a_clock_setup()` is called from `src/stm32/stm32f1.c:281` inside a
`#elif CONFIG_MACH_AT32F403A` conditional block. There is **no** `DECL_INIT`
registration for this function anywhere in `at32f403a.c`. The file includes
`sched.h // DECL_INIT` as an include comment but that include is for other
purposes. The correct description is:
> `at32f403a_clock_setup()` — called directly from the `stm32f1.c` init path
> at `src/stm32/stm32f1.c:281` when `CONFIG_MACH_AT32F403A` is set.

**Source:** `src/stm32/at32f403a.c` (no DECL_INIT present); `src/stm32/stm32f1.c:279–284`

---

### mcu_uart_gpio_remap() conditional is incomplete

**Finding:** INCOMPLETE
**Original text:**
> `mcu_uart_gpio_remap()` — enables `UART5_GMUX_0001` remap (conditional on
> `CONFIG_STM32_SERIAL_AT_USART5_PB8_PB9`).

**Corrected text:**
> `mcu_uart_gpio_remap()` — enables `UART5_GMUX_0001` remap (conditional on
> `CONFIG_STM32_SERIAL_AT_USART5_PB8_PB9 || CONFIG_STM32_USBCANBUS_PA11_PA12_AND_SERIAL_USART5_PB8_PB9`).
> Both the `.c` implementation and the `.h` forward declaration share this dual guard.

**Source:** `src/stm32/at32f403a.c:131–133`; `src/stm32/at32f403a.h:10–12`

---

## src-at32f415rc.md

### AT32F415RC flash size is 256 KB, not 128 KB

**Finding:** INCORRECT
**Original text (Summary):**
> A fork-exclusive C source file providing board-level initialisation for the
> **Artery AT32F415RC** microcontroller (ARM Cortex-M4, **128 KB flash**, USB OTG FS).

**Original text (Risks section):**
> The AT32F415RC has only 128 KB of flash. The `power_loss_check.c` file defines
> two 1 KB flash sectors at the top of this flash range (`0x0801F800`, `0x0801FC00`);
> any build that approaches 128 KB will corrupt the power-loss data.

**Corrected text:**
> A fork-exclusive C source file providing board-level initialisation for the
> **Artery AT32F415RC** microcontroller (ARM Cortex-M4, **256 KB flash**, USB OTG FS).

The Kconfig explicitly sets `default 0x40000 if MACH_AT32F415` for `FLASH_SIZE`,
and `0x40000 = 262,144 bytes = 256 KB`. The AT32F415RC uses the Artery naming
convention where "R" = LQFP64 package and "C" indicates 256 KB flash density.

The risk note is also incorrect: `0x0801F800` and `0x0801FC00` are at the
128 KB offset from flash start (`0x08000000`), placing them in the **middle**
of a 256 KB device, not at the top. The correct risk note is:
> The `power_loss_check.c` sectors (`0x0801F800`, `0x0801FC00`) sit at the
> 128 KB boundary, halfway through the 256 KB flash. Any build exceeding 128 KB
> will overwrite the power-loss data sectors.

**Source:** `src/stm32/Kconfig:238` (`default 0x40000 if MACH_AT32F415`);
`research/mcu/build-system.md` and `research/mcu/architecture-overview.md`
both correctly state 256 KB.

---

### usb_clock48m_select clk_s parameter is silently ignored

**Finding:** INCOMPLETE
**Original text:**
> `usb_clock48m_select(usb_clk48_s clk_s)` — sets USB clock divider based on
> `system_core_clock` value (48/72/96/120/144 MHz → `CRM_USB_DIV_1` through
> `CRM_USB_DIV_3`).

**Corrected text:**
> `usb_clock48m_select(usb_clk48_s clk_s)` — **ignores `clk_s` entirely**.
> The function body is a single `switch(system_core_clock)` block; the `clk_s`
> parameter is never referenced. Regardless of whether `USB_CLK_HICK` or
> `USB_CLK_HEXT` is passed, the function always executes the same divider-select
> code. The parameter exists for API compatibility with `at32f403a.c`'s version
> of the function, which does branch on `clk_s`.

**Source:** `src/stm32/at32f415rc.c:63–94` (function body contains no reference to `clk_s`)

---

### at32f415rc_clock_setup called from stm32f1.c, not DECL_INIT

**Finding:** INCOMPLETE
**Original text:**
> `at32f415rc_clock_setup()` — calls `system_clock_config()` only; called by
> Klipper's `DECL_INIT` equivalent.

**Corrected text:**
> `at32f415rc_clock_setup()` — calls `system_clock_config()` only; called
> directly from `src/stm32/stm32f1.c:279` inside a `#if CONFIG_MACH_AT32F415`
> block, not via DECL_INIT.

**Source:** `src/stm32/stm32f1.c:279`

---

## src-inductance_coil.md

### Timer 5 (TMR5) is also hardcoded — not just Timer 2

**Finding:** INCOMPLETE
**Original text:**
> Timer 2 is hardcoded (`TMR2`, PA0). Any build that also uses Timer 2 for
> another purpose will conflict.

**Corrected text:**
> **Two timers are hardcoded**: Timer 2 (`TMR2`) for pulse counting input capture
> and Timer 5 (`TMR5`) for calibration gating. Any build that uses Timer 2 **or**
> Timer 5 for another purpose will conflict.
>
> Defined in `inductance_coil.c`:
> ```c
> #define INPUT_CAPTURE_CRM_TIM          TMR2   // line 146 — pulse count capture
> #define INPUT_CAPTURE_CAL_CRM_TIM      TMR5   // line 157 — calibration gate timer
> ```

**Source:** `src/stm32/inductance_coil.c:146,157`

---

### inductance_coil_dev_init does not allocate an OID

**Finding:** INCORRECT
**Original text:**
> `inductance_coil_dev_init(struct freq_cal_info *info)` — allocates and
> initialises a device OID.

**Corrected text:**
> `inductance_coil_dev_init(struct freq_cal_info *info)` — initialises the CRM
> peripheral clocks (`crm_configuration()`), configures GPIO (`gpio_configuration()`),
> and initialises the timer (`inductance_coil_crm_tmr_init(info)`). It performs
> **no OID allocation**. OID allocation is done separately in
> `command_inductance_coil_config()` at line 435 via `oid_alloc()`.

**Source:** `src/stm32/inductance_coil.c:375–384,435`

---

### Calibration timer frequency is configurable, not fixed at 10 kHz

**Finding:** INCORRECT
**Original text:**
> `inductance_coil_crm_tmr_init(struct freq_cal_info *info)` — initialises Timer 2
> input-capture and the calibration counter timer at 10 kHz.

**Corrected text:**
> `inductance_coil_crm_tmr_init(struct freq_cal_info *info)` — initialises Timer 2
> (TMR2) for input capture and Timer 5 (TMR5) as a calibration gating counter.
> The calibration timer period is set by:
> ```c
> tmp_pr_value = INPUT_CAPTURE_CAL_CRM_TIM_PR(g_freq_cal_info.freq_cal_cycle);
> // expands to: CONFIG_CLOCK_FREQ / INPUT_CAPTURE_CAL_CRM_DIV * freq_cal_cycle - 1
> ```
> `freq_cal_cycle` is a configurable parameter passed via `inductance_coil_config`
> MCU command (arg index 3, in microseconds). The timer is **not** fixed at 10 kHz.
>
> The 10 kHz figure (`TRM_OVER_FREQ = 10000`) belongs to `power_loss_check.c` (line 32),
> not to `inductance_coil.c`.

**Source:** `src/stm32/inductance_coil.c:160–162,332`; `src/stm32/power_loss_check.c:32`

---

## kinematics-idex_modes.md

### INACTIVE is defined and used internally — not fully removed

**Finding:** MISLEADING
**Original text:**
> `VALID_MODES = [INACTIVE, PRIMARY, COPY, MIRROR]` | `VALID_MODES = [PRIMARY, COPY, MIRROR]`
> | `INACTIVE` mode concept removed; carriages are always in an active mode

**Corrected text:**
> `VALID_MODES = [PRIMARY, COPY, MIRROR]` — `INACTIVE` is removed from the
> user-selectable mode list (this is correct).
>
> However, `INACTIVE = 'INACTIVE'` is still **defined** at line 10 and
> **actively used** for internal `DualCarriagesRail.mode` state:
> - Line 155: `if mode == INACTIVE:` (mode check in `get_kin_range`)
> - Line 222: `self.mode = (INACTIVE, PRIMARY)[active]` (init state depends on active flag)
> - Line 241: `return self.mode != INACTIVE` (is_active check)
> - Line 259: `self.mode = INACTIVE` (deactivation in `inactivate()`)
>
> Carriages can and do enter `INACTIVE` state internally (e.g., when the
> non-primary carriage is parked). The accurate description is: `INACTIVE` is
> not a user-configurable mode, but remains an internal state that carriages
> transition through.

**Source:** `klippy/kinematics/idex_modes.py:10,155,222,241,259`

---

## research/triage/README.md

### C36 static_digital_output.py is present in the fork, not removed

**Finding:** INCORRECT
**Original text:**
> | C36 | `static_digital_output.py` — removed | **1** | [removed-upstream-extras.md](…) |

And in the Quick Wins summary:
> | **C22–C31, C33–C36** | 14 upstream extras absent | …

**Corrected text:**
> `static_digital_output.py` is **present** in the fork at
> `klippy/extras/static_digital_output.py`. It should not be listed as "removed"
> and its action item "Copy from upstream" has already been completed (or was
> never removed). C36 should be reclassified from Tier 1 to Tier 4 (Keep) or
> removed from the triage table entirely.

**Source:** `klippy/extras/static_digital_output.py` (file exists)

---

### Tier 1 count is 18, not 16

**Finding:** INCORRECT
**Original text:**
> | **1** | Drop | **16** | Upstream fully covers this; fork patch can be removed |

**Corrected text:**
The full triage table contains **18** items marked `**1**`:
A4, B7, C11, C12, C22, C23, C24, C25, C26, C27, C28, C29, C30, C31, C33, C34,
C35, C36 = 18.

The stated count of 16 understates by 2. If C36 is removed (since
`static_digital_output.py` is present), the correct Tier-1 count of genuinely
"absent" items is **17**. Either way, 16 is wrong.

**Source:** `research/triage/README.md` (full table; count of `| **1** |` rows)

---

## research/README.md

### Removed-extras count is 14, not 15

**Finding:** INCORRECT
**Original text:**
> | **Upstream-only extras removed from fork** | 15 | `ads1220`, `ads1x1x`, `bmi160`,
> `canbus_stats`, `garbage_collection`, `hx71x`, `icm20948`, `lis3dh`, `load_cell`,
> `load_cell_probe`, `motion_queuing`, `static_pwm_clock`, `temperature_probe`,
> `trigger_analog`, `static_digital_output` |

**Corrected text:**
> | **Upstream-only extras removed from fork** | 14 | (list above minus `static_digital_output`) |
>
> `static_digital_output.py` exists in `klippy/extras/`. The correct count is 14.
> Note: `motion_queuing` is included in this list and is absent from the fork,
> though it is classified as Tier 2 (Adapt) not Tier 1 (Drop) in the triage doc.

**Source:** `klippy/extras/static_digital_output.py` (file exists)
