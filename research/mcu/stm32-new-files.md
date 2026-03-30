# New Files Added to `src/stm32/` in Snapmaker U1 Klipper Fork

This document catalogues the six new source files added to the `src/stm32/`
directory, which do not exist in upstream Klipper.  Four files provide AT32 MCU
board-level initialisation; two files implement novel hardware modules.

## Summary Table

| File | Lines | Category | Purpose |
|------|------:|----------|---------|
| `at32f403a.c` | 184 | AT32 board init | Clock, USB, debug UART, GPIO remaps for AT32F403A |
| `at32f403a.h` | 38 | AT32 header | Declarations + LOG macros for AT32F403A |
| `at32f415rc.c` | 118 | AT32 board init | Clock, USB OTG, debug UART for AT32F415RC |
| `at32f415rc.h` | 26 | AT32 header | Declarations + LOG macros for AT32F415RC |
| `inductance_coil.c` | 674 | Hardware module | Inductive bed-probe frequency measurement |
| `inductance_coil.h` | 6 | Hardware module header | Minimal header for inductance_coil.c |
| `power_loss_check.c` | 685 | Hardware module | Power-loss detection + stepper position flash save |

---

## at32f403a.c (184 lines)

### Upstream Counterpart

Modelled after the `clock_setup()` function in `stm32f1.c`.  It replaces the
clock-setup path when `CONFIG_MACH_AT32F403A` is defined.  `stm32f1.c`
conditionally includes this file's header and calls `at32f403a_clock_setup()`
instead of its own `clock_setup()`.

### Purpose

Board-level initialisation for the AT32F403A MCU.  Configures the 240 MHz
system clock via HEXT → PLL × 60, sets up a USB 48 MHz clock from HICK using
ACC (Auto Clock Calibration) locked to the USB SOF signal, initialises debug
UART on PB10 / USART3, and provides GPIO remap functions for UART5 (PB8/PB9),
CAN2, and SPI4.

### Key Functions

| Function | Role |
|----------|------|
| `at32f403a_clock_setup()` | Calls `system_clock_config()`, then `usb_clock48m_select(USB_CLK_HICK)`, and enables the USB peripheral clock. |
| `usb_clock48m_select()` | Configures ACC C1/C2/C3 boundaries (7980 / 8000 / 8020) for HICK calibration, or sets USB clock divider based on `SystemCoreClock` for HEXT mode. |
| `uart_debug_print_init()` | USART3 debug output at a specified baud rate on PB10. |
| `at32f403a_log()` | Character-by-character UART output for debug logging. |
| `mcu_uart_gpio_remap()` | `UART5_GMUX_0001` remap for PB8/PB9. |
| `mcu_can2_gpio_remap()` | `CAN2_GMUX_0001` remap. |
| `mcu_spi4_gpio_remap()` | `SPI4_GMUX_0001` remap. |
| `PUTCHAR_PROTOTYPE` | `printf` redirection (GCC `__io_putchar` / Clang `fputc`). |

### Key Divergences from STM32 Equivalent

1. STM32F1 `clock_setup()` configures 72 MHz; this configures **240 MHz** via
   PLL × 60.
2. USB clock uses **ACC + HICK** instead of PLL-derived division.
3. GPIO remapping uses AT32-specific **GMUX registers** (not STM32's AFIO).
4. Debug UART uses AT32 HAL functions (`crm_periph_clock_enable`, `gpio_init`,
   `usart_init`) instead of direct register writes.

### Integration Points

- Called from `stm32f1.c` `armcm_main()` via
  `#elif CONFIG_MACH_AT32F403A` guard.
- `at32f403a.h` included by `stm32f1.c` when AT32F403A is selected.
- GPIO remap functions called from `can.c`, `spi.c`, `serial.c` as `extern`
  declarations.
- `DECL_CONSTANT_STR("RESERVE_PINS_debug_uart_tx_pin", "PB10")` reserves pin
  in Klipper.

### Upstream Contributability

**Moderate.**  The core clock setup is clean and well-structured.  Would need:

- Removal of debug UART (not standard Klipper practice for MCU firmware).
- Clean separation of remap functions into the peripheral files that use them.
- Would work alongside existing upstream PR #6626 (which adds AT32F415/F413
  with a lighter approach).
- The ACC implementation is novel and valuable for upstream.

---

## at32f403a.h (38 lines)

### Upstream Counterpart

None directly.  Analogous to how `stm32f0.c` / `stm32f4.c` have `internal.h`
declarations.

### Purpose

Header providing function declarations for `at32f403a.c` and `LOG_E` / `LOG_W`
/ `LOG_I` / `LOG_V` debug-logging macros that compile to `at32f403a_log()`
calls when `CONFIG_MACH_AT32F403A` is defined, or to empty statements
otherwise.

### Key Divergences

- `LOG` macros are not standard Klipper practice.
- TAG-based prefix system for categorised logging.

### Integration Points

- Included by `stm32f1.c`, `can.c` (for GPIO remap declarations).
- `LOG` macros usable from any file that includes this header.

### Upstream Contributability

**Low** standalone value.  Would likely be merged into a combined AT32 header
or removed (logging macros).

---

## at32f415rc.c (118 lines)

### Upstream Counterpart

Same pattern as `at32f403a.c` — replaces the `stm32f1.c` `clock_setup()` path
when `CONFIG_MACH_AT32F415` is defined.

### Purpose

Board-level initialisation for the AT32F415RC MCU.  Configures 144 MHz system
clock via HEXT → PLL × 36, sets up USB OTG 48 MHz clock from HEXT divider
(144 / 3 = 48), and provides debug UART on PB10 / USART3.

### Key Functions

| Function | Role |
|----------|------|
| `at32f415rc_clock_setup()` | Calls `system_clock_config()` (USB clock setup is separate). |
| `at32f415rc_usbotg_clock_config()` | Enables `OTG_CLOCK`, calls `usb_clock48m_select(USB_CLK_HEXT)`. |
| `usb_clock48m_select()` | Sets `crm_usb_clock_div` based on `system_core_clock` (144 MHz → `CRM_USB_DIV_3`). |
| `uart_debug_print_init()` | Same USART3 / PB10 debug setup as F403A. |
| `at32f415_log()` | Debug output function. |

### Key Divergences from STM32 Equivalent

1. Configures **144 MHz** instead of 72 MHz.
2. USB clock from HEXT divider (no ACC needed — F415 lacks the ACC
   peripheral).
3. Flash wait cycles explicitly set to **4** (needed at 144 MHz).
4. USB OTG clock separated from system clock setup (called from `usbotg.c`).
5. Uses `system_core_clock` (lowercase, AT32 global) instead of
   `SystemCoreClock` (CMSIS standard).

### Integration Points

- `at32f415rc_clock_setup()` called from `stm32f1.c` `armcm_main()`.
- `at32f415rc_usbotg_clock_config()` called from `usbotg.c` USB init path.
- `at32f415rc.h` included by `usbotg.c` when AT32F415 is selected.

### Upstream Contributability

**High.**  This is the cleaner of the two MCU files.  The existing upstream
PR #6626 adds AT32F415 support with a lighter-touch approach (modifying
`stm32f1.c` directly rather than creating a separate file).  This fork's
approach is more modular but would need reconciling with PR #6626's approach.

---

## at32f415rc.h (26 lines)

### Upstream Counterpart

None directly.  Same pattern as `at32f403a.h`.

### Purpose

Header for `at32f415rc.c`.  Function declarations and `LOG_E` / `LOG_W` /
`LOG_I` / `LOG_V` macros gated on `CONFIG_MACH_AT32F415`.

### Upstream Contributability

**Low** standalone value — same reasoning as `at32f403a.h`.

---

## inductance_coil.c (674 lines) + inductance_coil.h (6 lines)

### Upstream Counterpart

None.  Entirely novel Klipper MCU module.

### Purpose

Implements hardware-based frequency measurement using AT32 timer input capture
for inductive bed probing.  Measures the resonant frequency of an inductance
coil (LC circuit) near the print-bed surface.  The frequency changes with
proximity to metal, enabling contactless Z-probing.  Uses timer capture to
count oscillation periods over configurable time windows.

### Key Features

- **Dual calibration modes:** `FIXED_TIME_CAL_MODE` and
  `FIXED_PULSE_NUM_CAL_MODE`.
- Configurable calibration window (1–50 samples).
- Virtual GPIO trigger output with configurable frequency thresholds.
- Bulk sensor data interface (uses `sensor_bulk.h` framework).
- MCU commands: `inductance_coil_config`, `virtual_gpio_trigger_with_timer`,
  `virtual_gpio_trigger`, `inductance_coil_query`,
  `query_inductance_coil`, `query_inductance_coil_status`,
  `query_inductance_coil_config_info`.

### Key Divergences

Novel code — no STM32 equivalent.  Uses AT32 HAL functions for timer
configuration.

### Integration Points

- Compiled for both AT32F403A and AT32F415 (gated on `CONFIG_MACH_AT32F4x`).
- Python counterpart: `klippy/extras/inductance_coil.py` (433 lines).
- Python probe integration: `klippy/extras/probe_inductance_coil.py`
  (2005 lines).
- Comment in Python (`inductance_coil.py` line 371):
  `# Currently only supports AT32415 PA0`.
- Heater fan pauses during probing (`heater_fan.py` listens for
  `inductance_coil` events).

### Upstream Contributability

**Low** for upstream Klipper mainline.  This is U1-specific hardware.
However, it demonstrates a pattern for inductive probing that could inspire a
generic upstream implementation.  The `sensor_bulk` integration is clean and
follows Klipper conventions.

---

## power_loss_check.c (685 lines)

### Upstream Counterpart

None.  Entirely novel Klipper MCU module.

### Purpose

Hardware-based power-loss detection with automatic stepper position persistence
to flash.  Monitors a GPIO pin (PB8 on F415, PB7 on F403A) using timer-based
duty-cycle measurement to detect voltage drops indicating power failure.  When
power loss is detected, immediately saves stepper positions to designated flash
sectors for recovery after power restoration.

### Key Features

- Timer-based PWM duty-cycle measurement for voltage monitoring.
- Configurable trigger time, duty threshold, debounce.
- **Dual flash sector scheme** (two alternating sectors for wear levelling):
  - F415: `0x0801F800` / `0x0801FC00` (1024-byte sectors).
  - F403A: `0x080FF000` / `0x080FF800` (2048-byte sectors).
- Stepper position storage for X / Y / Z / extruder.
- MCU commands: `config_power_loss_check_dev`, `query_power_loss_status`,
  `update_report_interval`, `enable_power_loss`,
  `query_power_loss_flash_valid`, `query_power_loss_stepper_info`.

### Integration Points

- Compiled for both AT32 chips (`CONFIG_MACH_AT32F4x`).
- Includes `stepper.h` for `get_all_stepper_info()`.
- Python counterpart: `klippy/extras/power_loss_check.py` (291 lines).
- Recovery integration: `klippy/extras/virtual_sdcard.py` (extensive
  power-loss recovery logic).
- Stepper tracking: `klippy/stepper.py` has `power_loss_need_save_steppers`
  list.

### Upstream Contributability

**Very low** for mainline.  Power-loss recovery is a product-specific feature
with complex system integration.  The flash storage approach is interesting but
tightly coupled to specific flash addresses and sector sizes.
