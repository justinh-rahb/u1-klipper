# Snapmaker U1 Klipper Fork — Full Analysis

## MCU C Source Analysis (AT32)

The Snapmaker U1 Klipper fork uses Artery Technology AT32 MCUs that are disguised as STM32 variants to the Klipper build system. This section documents the complete C-layer implementation.

### Architecture

The U1 uses two AT32 MCUs:

- **AT32F403A** (main board): 240 MHz Cortex-M4, declared as `stm32f103xe` to the build system. Uses HEXT crystal → PLL×60 for system clock, and ACC (Auto Clock Calibration) locked to USB SOF for 48 MHz USB clock from internal HICK oscillator.

- **AT32F415RC** (extruder heads): 144 MHz Cortex-M4, declared as `stm32f105xc`. Uses HEXT → PLL×36 for system clock and HEXT÷3 for 48 MHz USB OTG clock.

Both MCUs select `MACH_STM32F1` in Kconfig, inheriting the STM32F1 code path, but are dispatched to AT32-specific clock setup via `#if CONFIG_MACH_AT32F415` / `#elif CONFIG_MACH_AT32F403A` guards in `stm32f1.c`.

### HAL Libraries

Two official Artery SDK HAL libraries are included:
- `lib/at32f403a/` — SDK v2.1.6, 26 peripheral modules (~123 files)
- `lib/at32f415/` — SDK v2.1.2, 22 peripheral modules (~132 files)

Klipper uses approximately 10 modules from each (CRM, GPIO, TMR, FLASH, USART, ACC for F403A, plus USB drivers). The remainder is dead library weight.

### New MCU Firmware Files

| File | Lines | Purpose |
|------|------:|---------|
| `at32f403a.c` | 184 | Clock setup (240 MHz), ACC config, debug UART, GPIO remaps |
| `at32f403a.h` | 38 | Declarations, LOG macros |
| `at32f415rc.c` | 118 | Clock setup (144 MHz), USB OTG clock, debug UART |
| `at32f415rc.h` | 26 | Declarations, LOG macros |
| `inductance_coil.c` | 674 | Inductive bed probing via timer frequency measurement |
| `inductance_coil.h` | 6 | Header |
| `power_loss_check.c` | 685 | Power loss detection and stepper position flash storage |

### Modified Upstream Files

Seven `src/stm32/` files were modified with AT32 conditionals:
- `stm32f1.c` — Clock setup dispatch to AT32 functions
- `can.c` — CAN2 support, AT32 IRQ definitions, GPIO remap
- `spi.c` — SPI4 pin differences, GPIO remap
- `serial.c` — UART5 on PB8/PB9 option
- `usbfs.c` — EP_KIND skip for AT32F403A double-buffering
- `usbotg.c` — AT32F415 OTG configuration, GCCFG register
- `Kconfig` / `Makefile` — AT32 processor entries, source lists, flags

### Timing and Protocol

The Klipper MCU command protocol is unchanged. AT32 changes are entirely at the HAL level. CLOCK_FREQ is correctly reported as 240/144 MHz, and the Python host handles non-standard frequencies transparently via `seconds_to_clock()`.

The AT32F403A's ACC/SOF clock calibration only affects USB timing, not step timing (system clock is crystal-based). USB disconnect does not impact stepper operation.

### Upstream Path

An open upstream PR (Klipper3d/klipper#6626) adds AT32F415/F413 support at 120 MHz with a lighter approach. The most pragmatic contribution path is to coordinate with that effort, using this fork's explicit Kconfig approach while trimming the HAL libraries to minimum required modules.

### Detailed Documents

See [`/research/mcu/README.md`](mcu/README.md) for the complete document index.
