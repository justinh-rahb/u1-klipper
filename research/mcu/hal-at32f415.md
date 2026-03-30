# AT32F415 HAL Library Analysis

## Library Origin

| Field | Value |
|-------|-------|
| Vendor | Artery Microelectronics (雅特力) |
| Package | Official Board Support Package (BSP) SDK |
| Version | **2.1.2** (`0x02.01.02.00`) |
| Copyright | © Artery. All rights reserved. |
| License | Proprietary BSP (not open-source) |
| Main Header | `lib/at32f415/at32f415.h` (~19 KB) |
| Variant Handling | Unified for all AT32F415 variants (no conditional compilation blocks like the F407 family) |

Version encoding from `lib/at32f415/at32f415.h` (lines 129–136):

```c
#define __AT32F415_LIBRARY_VERSION_MAJOR    (0x02)
#define __AT32F415_LIBRARY_VERSION_MIDDLE   (0x01)
#define __AT32F415_LIBRARY_VERSION_MINOR    (0x02)
#define __AT32F415_LIBRARY_VERSION_RC       (0x00)
```

---

## Module Inventory (22 HAL Modules)

The HAL layer lives under `lib/at32f415/hal/` with headers in `inc/` and sources in `src/`.

| # | Module | Header | Source | Peripheral | STM32 Analogue | Notes |
|---|--------|--------|--------|-----------|----------------|-------|
| 1 | ADC | `at32f415_adc.h` | `at32f415_adc.c` | Analog-to-Digital Converter | `stm32f1xx_hal_adc` | |
| 2 | CAN | `at32f415_can.h` | `at32f415_can.c` | CAN Bus | `stm32f1xx_hal_can` | |
| 3 | CMP | `at32f415_cmp.h` | `at32f415_cmp.c` | Analog Comparator | No F103 equivalent | **NEW** — not present in AT32F403A |
| 4 | CRC | `at32f415_crc.h` | `at32f415_crc.c` | CRC Engine | `stm32f1xx_hal_crc` | |
| 5 | CRM | `at32f415_crm.h` | `at32f415_crm.c` | Clock & Reset Management | `stm32f1xx_hal_rcc` | 916-line header |
| 6 | DEBUG | `at32f415_debug.h` | `at32f415_debug.c` | Debug Interface | `stm32f1xx_hal_dbgmcu` | |
| 7 | DEF | `at32f415_def.h` | — | Common Type Definitions | `stm32f1xx_hal_def` | Header only |
| 8 | DMA | `at32f415_dma.h` | `at32f415_dma.c` | DMA Controller | `stm32f1xx_hal_dma` | |
| 9 | ERTC | `at32f415_ertc.h` | `at32f415_ertc.c` | Enhanced RTC | `stm32f1xx_hal_rtc` | Renamed from RTC; superset API |
| 10 | EXINT | `at32f415_exint.h` | `at32f415_exint.c` | External Interrupt | `stm32f1xx_hal_exti` | |
| 11 | FLASH | `at32f415_flash.h` | `at32f415_flash.c` | Flash Memory Controller | `stm32f1xx_hal_flash` | |
| 12 | GPIO | `at32f415_gpio.h` | `at32f415_gpio.c` | General-Purpose I/O | `stm32f1xx_hal_gpio` | |
| 13 | I2C | `at32f415_i2c.h` | `at32f415_i2c.c` | I²C | `stm32f1xx_hal_i2c` | |
| 14 | MISC | `at32f415_misc.h` | `at32f415_misc.c` | NVIC / Misc Utilities | `stm32f1xx_hal_cortex` | |
| 15 | PWC | `at32f415_pwc.h` | `at32f415_pwc.c` | Power Control | `stm32f1xx_hal_pwr` | |
| 16 | SDIO | `at32f415_sdio.h` | `at32f415_sdio.c` | SD/SDIO Interface | `stm32f1xx_hal_sd` | |
| 17 | SPI | `at32f415_spi.h` | `at32f415_spi.c` | SPI | `stm32f1xx_hal_spi` | |
| 18 | TMR | `at32f415_tmr.h` | `at32f415_tmr.c` | Timers | `stm32f1xx_hal_tim` | |
| 19 | USART | `at32f415_usart.h` | `at32f415_usart.c` | UART / USART | `stm32f1xx_hal_uart` | |
| 20 | USB | `at32f415_usb.h` | — | USB Device + Host | `stm32f1xx_hal_pcd` | OTG Full-Speed capable; see USB Architecture below |
| 21 | WDT | `at32f415_wdt.h` | `at32f415_wdt.c` | Independent Watchdog | `stm32f1xx_hal_iwdg` | |
| 22 | WWDT | `at32f415_wwdt.h` | `at32f415_wwdt.c` | Window Watchdog | `stm32f1xx_hal_wwdg` | |

### Peripherals Absent vs AT32F403A

The AT32F415 is a smaller, cost-reduced part. These peripherals found on the
F403A are **not present**:

- **ACC** — Auto Clock Calibration (USB clock comes from HEXT divider instead)
- **BPR** — Backup Registers
- **DAC** — Digital-to-Analog Converter
- **EMAC** — Ethernet MAC
- **XMC** — External Memory Controller

---

## Additional (Non-HAL) Files

Beyond the 22 HAL modules, the `lib/at32f415/` directory contains supporting files at the root level:

| File | Purpose |
|------|---------|
| `at32f415.h` | Master device header — register definitions, memory map, all peripheral base addresses |
| `at32f415_clock.c` / `.h` | Board-level clock configuration; provides `system_clock_config()` for 144 MHz PLL setup |
| `at32f415_conf.h` | HAL module include selector; enables/disables individual HAL modules via `#include` |
| `at32f415_int.c` / `.h` | Interrupt handler stubs (Cortex-M4 exception vectors) |
| `system_at32f415.c` / `.h` | CMSIS-mandated `SystemInit()` and `SystemCoreClockUpdate()` |
| `usb_conf.h` | USB stack configuration (endpoint count, FIFO sizes, class selection) |

**Not included in the library directory:**
- No startup assembly (`.s`) file — provided externally or by the build system
- No linker scripts (`.ld`) — Klipper supplies its own via `src/stm32/`

---

## USB Architecture

The AT32F415 uses a **USB OTG Full-Speed** (OTGFS1) peripheral, distinct from the
basic USB FS register-based peripheral found on the AT32F403A. The library provides
a complete USB stack with both Device and Host class implementations.

### USB Driver Layer (`usb_drivers/`)

Core transport and protocol handling:

| File | Role |
|------|------|
| `usb_core.c/.h` | OTG core initialization, FIFO management, endpoint primitives |
| `usb_std.h` | USB standard descriptor and request definitions |
| `usbd_core.c/.h` | Device-mode core (enumeration state machine, EP0 handling) |
| `usbd_int.c/.h` | Device-mode interrupt handler (SOF, SETUP, IN/OUT token dispatch) |
| `usbd_sdr.c/.h` | Standard Device Request handler (GET_DESCRIPTOR, SET_ADDRESS, etc.) |
| `usbh_core.c/.h` | Host-mode core (port management, device enumeration) |
| `usbh_ctrl.c/.h` | Host-mode control transfer engine |
| `usbh_int.c/.h` | Host-mode interrupt handler |

### USB Device Classes (`usbd_class/`)

Pre-built device class implementations:

| Class Directory | Description |
|----------------|-------------|
| `audio/` | USB Audio (UAC) |
| `audio_hid/` | Composite Audio + HID |
| `cdc/` | CDC-ACM (Virtual COM Port) — **used by Klipper** |
| `composite_cdc_keyboard/` | Composite CDC + HID Keyboard |
| `composite_cdc_msc/` | Composite CDC + Mass Storage |
| `custom_hid/` | Custom HID device |
| `hid_iap/` | HID-based In-Application Programming |
| `keyboard/` | HID Keyboard |
| `mouse/` | HID Mouse |
| `msc/` | Mass Storage Class (BOT) |
| `printer/` | USB Printer Class |
| `winusb/` | WinUSB (vendor-specific with WCID) |

### USB Host Classes (`usbh_class/`)

| Class Directory | Description |
|----------------|-------------|
| `usbh_cdc/` | CDC host (communicate with CDC devices) |
| `usbh_hid/` | HID host (keyboard + mouse support) |
| `usbh_msc/` | Mass Storage host |

---

## What Klipper Actually Uses

From `src/stm32/Makefile` lines 52–56, only a subset of the HAL is compiled
for `CONFIG_MACH_AT32F415` builds:

### Compiled HAL Modules (6 of 22)

```makefile
# src/stm32/Makefile lines 52-56
src-$(CONFIG_MACH_AT32F415) += stm32/at32f415rc.c stm32/adc.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/at32f415_clock.c ../lib/at32f415/system_at32f415.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_usart.c ../lib/at32f415/hal/src/at32f415_gpio.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_crm.c ../lib/stm32f1/system_stm32f1xx.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_tmr.c ../lib/at32f415/hal/src/at32f415_flash.c
```

| Source File | Origin | Purpose |
|-------------|--------|---------|
| `stm32/at32f415rc.c` | Klipper (`src/stm32/`) | Clock setup wrapper, USB clock config, debug UART init |
| `stm32/adc.c` | Klipper (`src/stm32/`) | Shared ADC driver (uses direct register access, not ADC HAL) |
| `at32f415_clock.c` | Library (root) | `system_clock_config()` — configures 144 MHz PLL from HEXT |
| `system_at32f415.c` | Library (root) | CMSIS `SystemInit()` |
| `at32f415_usart.c` | HAL | USART peripheral driver |
| `at32f415_gpio.c` | HAL | GPIO peripheral driver |
| `at32f415_crm.c` | HAL | Clock & Reset Management (peripheral clock gating) |
| `at32f415_tmr.c` | HAL | Timer peripheral driver |
| `at32f415_flash.c` | HAL | Flash controller (used by `power_loss_check.c`) |
| `system_stm32f1xx.c` | STM32F1 lib | STM32F1 CMSIS init — **also compiled** for compatibility shim |

### USB Integration

USB uses the Klipper OTG driver (`src/stm32/usbotg.c`), **not** the USB FS driver:

```
# From Kconfig lines 160-166
config HAVE_STM32_USBFS
    default y if (MACH_STM32F1 || MACH_STM32F070) && ... && !MACH_AT32F415  # explicitly excluded

config HAVE_STM32_USBOTG
    default y if ... || MACH_AT32F415  # explicitly included
```

The USB CDC class files and USB core drivers from `lib/at32f415/usb_drivers/` and
`lib/at32f415/usbd_class/cdc/` are also compiled when USB is enabled.

### Klipper-Side Wrapper Functions (`src/stm32/at32f415rc.c`)

This file provides 5 functions bridging Klipper's STM32 abstractions to AT32 hardware:

| Function | Purpose |
|----------|---------|
| `at32f415_log()` | Debug UART output |
| `uart_debug_print_init()` | Initializes debug UART peripheral |
| `usb_clock48m_select()` | Derives 48 MHz USB clock from system clock (144/3 or 96/2) |
| `at32f415rc_clock_setup()` | Calls `system_clock_config()` from the library |
| `at32f415rc_usbotg_clock_config()` | Enables OTG peripheral clock and selects USB 48 MHz source |

### Unused HAL Modules (16 of 22)

These HAL modules ship with the library but are **never compiled** into Klipper:

> ADC (HAL version), CAN, CMP, CRC, DEBUG, DEF (header-only), DMA, ERTC,
> EXINT, I2C, MISC, PWC, SDIO, SPI, WDT, WWDT

Klipper accesses ADC, SPI, I2C, and DMA through its own register-level drivers
in `src/stm32/` rather than through the AT32 HAL.

---

## Key Differences from AT32F403A

### 1. USB Clock Source — No ACC

The AT32F403A uses an **ACC** (Auto Clock Calibration) peripheral to trim an
internal RC oscillator to 48 MHz for USB. The AT32F415 **lacks ACC entirely** and
instead derives the USB clock from the HEXT crystal via a fixed divider:

- At 144 MHz system clock: `144 / 3 = 48 MHz`
- At 96 MHz system clock: `96 / 2 = 48 MHz`

This is handled by `usb_clock48m_select()` in `at32f415rc.c`.

### 2. USB OTG vs USB FS

| Aspect | AT32F403A | AT32F415 |
|--------|-----------|----------|
| Peripheral | USB FS (register-based) | USB OTG Full-Speed (OTGFS1) |
| Klipper driver | `usbfs.c` | `usbotg.c` |
| Kconfig flag | `HAVE_STM32_USBFS` | `HAVE_STM32_USBOTG` |
| Endpoint handling | Packet buffer memory | FIFO-based with DMA |

### 3. CRM Header Size

The CRM (clock/reset) header is **225 lines shorter** on the AT32F415 (916 lines)
compared to the AT32F403A (1141 lines), reflecting the reduced peripheral set
requiring fewer clock gate definitions.

### 4. CMP Peripheral (AT32F415 Only)

The AT32F415 includes an **analog comparator** (CMP) module that the AT32F403A
does not have. Not used by Klipper.

### 5. ERTC vs RTC

The AT32F415 uses an **Enhanced RTC** (ERTC) with a richer feature set (calendar,
alarms, timestamps) compared to the basic RTC on the AT32F403A. Not used by Klipper.

### 6. Flash Sector Size

| Parameter | AT32F415 | AT32F403A |
|-----------|----------|-----------|
| Sector size | **1024 bytes** (1 KB) | 2048 bytes (2 KB) |
| Total flash | 256 KB (`0x40000`) | Up to 1 MB |
| Total RAM | 32 KB (`0x8000`) | 96 KB (`0x18000`) |

From `src/stm32/power_loss_check.c` (lines 12–19):

```c
#if CONFIG_MACH_AT32F415
  #define FLASH_SECTOR_SIZE  1024
```

### 7. Peripheral Availability Summary

| Peripheral | AT32F403A | AT32F415 |
|-----------|-----------|----------|
| ACC | ✓ | ✗ |
| BPR | ✓ | ✗ |
| CMP | ✗ | ✓ |
| DAC | ✓ | ✗ |
| EMAC | ✓ | ✗ |
| ERTC | ✗ (has RTC) | ✓ |
| USB OTG | ✗ (has USB FS) | ✓ |
| XMC | ✓ | ✗ |

---

## Register Divergences

The AT32F415 masquerades as an STM32F105 in Klipper's build system
(`MCU = stm32f105xc`), which activates STM32F105-specific CMSIS defines and allows
reuse of the OTG code path. However, several register-level differences require
explicit handling.

### 1. USB OTG GCCFG Register

The AT32F415 uses a `GCCFG` (General Core Configuration) register with **VBUS
sensing** control bits. Klipper needs `VBUSBSEN` and `NOVBUSSENS` flags to disable
VBUS sensing on boards without a VBUS detection circuit.

Because the AT32 headers use Artery-specific names (not STM32-compatible names),
Klipper manually defines the STM32-compatible bit in `src/stm32/usbotg.c`
(lines 37–39):

```c
#define USB_OTG_GCCFG_NOVBUSSENS_Pos     (21U)
#define USB_OTG_GCCFG_NOVBUSSENS_Msk     (0x1UL << USB_OTG_GCCFG_NOVBUSSENS_Pos)
#define USB_OTG_GCCFG_NOVBUSSENS          USB_OTG_GCCFG_NOVBUSSENS_Msk
```

The real STM32F105 also has OTG, which is why the `stm32f105xc` alias works — but
the bit-level definitions differ enough to require this manual override.

### 2. OTG Clock Enable Path

| Aspect | STM32F105 | AT32F415 |
|--------|-----------|----------|
| Clock enable register | `RCC_AHB2ENR` bit `OTGFSEN` | CRM module with `OTG_CLOCK` constant |
| Enable function | Direct RCC register write | `at32f415rc_usbotg_clock_config()` wrapper |
| 48 MHz source | PLL-derived via RCC | HEXT divider via `usb_clock48m_select()` |

### 3. GPIO Alternate Function

USB D+/D− pins use **AF10** on the AT32F415 (`GPIO_FUNCTION(10)` in `usbotg.c`
line 44), mapping to PA11 (D−) and PA12 (D+). This is consistent with the OTG
peripheral's pin assignment.

### 4. STM32F1 CMSIS Compatibility Shim

Klipper compiles `lib/stm32f1/system_stm32f1xx.c` alongside the AT32 system files.
This provides STM32F1 CMSIS symbols (e.g., `SystemCoreClock`) that other shared
Klipper STM32 code references. The AT32F415's `system_at32f415.c` provides the
actual hardware initialization; the STM32F1 file acts as a compatibility layer.

---

## AT32F415 in the U1 Architecture

| Property | Value |
|----------|-------|
| Role | Extruder head MCU (toolhead boards) |
| Communication | CAN bus (or USB-CAN bridge to host) |
| Core clock | **144 MHz** (2× the 72 MHz of the STM32F105 it impersonates) |
| MCU identity string | `stm32f105xc` |
| Kconfig machine | `MACH_AT32F415` |
| USB mode | OTG Full-Speed (`HAVE_STM32_USBOTG = y`) |
| USB FS mode | Explicitly excluded (`!MACH_AT32F415` in `HAVE_STM32_USBFS`) |
| Flash | 256 KB (`0x40000`) |
| RAM | 32 KB (`0x8000`) |
| Flash sector | 1024 bytes |

The STM32F105 alias is deliberate: the F105 is one of the few STM32F1-family
parts with USB OTG support, so its CMSIS headers provide the correct OTG register
definitions that the AT32F415's OTG peripheral is register-compatible with (modulo
the divergences documented above).
