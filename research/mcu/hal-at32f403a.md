# AT32F403A HAL Library Analysis

Exhaustive analysis of the Artery AT32F403A/F407 Hardware Abstraction Layer as
vendored in this repository under `lib/at32f403a/`.

---

## Library Origin

| Field | Value |
|-------|-------|
| Vendor | Artery Microelectronics |
| Package | Official Board Support Package (BSP) SDK |
| Version | **2.1.6** (`0x02.01.06.00`) |
| Copyright | © Artery. All rights reserved. |
| License | Proprietary BSP — authorised for use with Artery MCUs only |
| Main header | `lib/at32f403a/at32f403a_407.h` (~36 KB) |
| Chip scope | AT32F403A **and** AT32F407 (selected by conditional compilation) |

The library uses a unified source tree for both chip variants.  F407-only
peripherals (e.g. Ethernet MAC) are guarded by `#ifdef AT32F407xx` or
equivalent preprocessor conditionals.

---

## Module Inventory

26 HAL modules reside in `lib/at32f403a/hal/inc/` (headers) and
`lib/at32f403a/hal/src/` (sources).

| # | Module | Files (`.c` / `.h`) | Peripheral | STM32 Analogue |
|---|--------|---------------------|------------|----------------|
| 1 | ACC | `at32f403a_407_acc` | Auto Clock Calibration | No direct equiv (CRS on STM32F0/L0) |
| 2 | ADC | `at32f403a_407_adc` | Analog-to-Digital Converter | `stm32f1xx_hal_adc` |
| 3 | BPR | `at32f403a_407_bpr` | Backup Registers | `stm32f1xx_hal_bkp` |
| 4 | CAN | `at32f403a_407_can` | CAN Bus Controller | `stm32f1xx_hal_can` |
| 5 | CRC | `at32f403a_407_crc` | CRC Calculator | `stm32f1xx_hal_crc` |
| 6 | CRM | `at32f403a_407_crm` | Clock & Reset Management | `stm32f1xx_hal_rcc` (1141 lines) |
| 7 | DAC | `at32f403a_407_dac` | Digital-to-Analog Converter | `stm32f1xx_hal_dac` |
| 8 | DEBUG | `at32f403a_407_debug` | Debug Support | `stm32f1xx_hal_dbgmcu` |
| 9 | DEF | `at32f403a_407_def` | Common Type Definitions | `stm32f1xx_hal_def` |
| 10 | DMA | `at32f403a_407_dma` | Direct Memory Access | `stm32f1xx_hal_dma` |
| 11 | EMAC | `at32f403a_407_emac` | Ethernet MAC (F407 only) | `stm32f4xx_hal_eth` |
| 12 | EXINT | `at32f403a_407_exint` | External Interrupt Controller | `stm32f1xx_hal_exti` |
| 13 | FLASH | `at32f403a_407_flash` | Flash Memory Controller | `stm32f1xx_hal_flash` |
| 14 | GPIO | `at32f403a_407_gpio` | General Purpose I/O | `stm32f1xx_hal_gpio` |
| 15 | I2C | `at32f403a_407_i2c` | I²C Bus | `stm32f1xx_hal_i2c` |
| 16 | MISC | `at32f403a_407_misc` | NVIC / Miscellaneous | `stm32f1xx_hal_cortex` |
| 17 | PWC | `at32f403a_407_pwc` | Power Control | `stm32f1xx_hal_pwr` |
| 18 | RTC | `at32f403a_407_rtc` | Real-Time Clock | `stm32f1xx_hal_rtc` |
| 19 | SDIO | `at32f403a_407_sdio` | SD/SDIO Interface | `stm32f1xx_hal_sd` |
| 20 | SPI | `at32f403a_407_spi` | SPI Bus | `stm32f1xx_hal_spi` |
| 21 | TMR | `at32f403a_407_tmr` | Timers (TMR1–14, TMR9–11) | `stm32f1xx_hal_tim` |
| 22 | USART | `at32f403a_407_usart` | UART / USART | `stm32f1xx_hal_uart` |
| 23 | USB | `at32f403a_407_usb` | USB Device (Full-Speed) | `stm32f1xx_hal_pcd` |
| 24 | WDT | `at32f403a_407_wdt` | Independent Watchdog | `stm32f1xx_hal_iwdg` |
| 25 | WWDT | `at32f403a_407_wwdt` | Window Watchdog | `stm32f1xx_hal_wwdg` |
| 26 | XMC | `at32f403a_407_xmc` | External Memory Controller | `stm32f1xx_hal_sram` / `_nor` |

### Additional Support Files

| File | Location | Purpose |
|------|----------|---------|
| `at32f403a_407_clock.c/.h` | `lib/at32f403a/` | `system_clock_config()` — 240 MHz PLL setup |
| `at32f403a_407_conf.h` | `lib/at32f403a/` | Feature-gate header (enables/disables HAL modules) |
| `at32f403a_407_int.c/.h` | `lib/at32f403a/` | Default IRQ handler stubs |
| `system_at32f403a_407.c/.h` | `lib/at32f403a/` | CMSIS `SystemInit()` / `SystemCoreClockUpdate()` |
| `startup_at32f403a_407.s` | `lib/at32f403a/` | ARM Cortex-M4 reset & vector table (assembly) |
| `usb_conf.h` | `lib/at32f403a/` | USB stack configuration knobs |

### Linker Scripts (6 variants)

```
lib/at32f403a/AT32F403AxC_FLASH.ld   (256 KB flash)
lib/at32f403a/AT32F403AxE_FLASH.ld   (512 KB flash)
lib/at32f403a/AT32F403AxG_FLASH.ld   (1024 KB flash)
lib/at32f403a/AT32F407xC_FLASH.ld
lib/at32f403a/AT32F407xE_FLASH.ld
lib/at32f403a/AT32F407xG_FLASH.ld
```

### USB Device Classes

Located under `lib/at32f403a/usbd_class/`:

`audio`, `audio_hid`, `cdc`, `composite_cdc_keyboard`, `composite_cdc_msc`,
`custom_hid`, `hid_iap`, `keyboard`, `mouse`, `msc`, `printer`

### USB Device Drivers

Located under `lib/at32f403a/usbd_drivers/`:

`usbd_core`, `usbd_int`, `usbd_sdr`

---

## What Klipper Actually Uses

The `Makefile` (`src/at32f403a/Makefile`) pulls in only a subset of the HAL.
Every other module is dead library weight carried in the tree but never
compiled into the firmware.

### Compiled HAL Sources

| HAL Source | Klipper Consumer | Purpose |
|------------|-----------------|---------|
| `at32f403a_407_clock.c` | Board init | `system_clock_config()` — configures HEXT → PLL → 240 MHz SCLK |
| `system_at32f403a_407.c` | CMSIS startup | `SystemInit()` — early clock / vector table setup |
| `at32f403a_407_crm.c` | Multiple drivers | Peripheral clock gating, PLL configuration, bus dividers |
| `at32f403a_407_tmr.c` | `armcm_timer.c` | Hardware timer for stepper step-event scheduling |
| `at32f403a_407_gpio.c` | GPIO driver | Pin mode, speed, pull, alternate-function configuration |
| `at32f403a_407_flash.c` | `power_loss_check.c` | Flash erase/program for stepper-position persistence |
| `at32f403a_407_usart.c` | Serial driver | Debug UART, host serial communication |
| `at32f403a_407_acc.c` | `at32f403a.c` | ACC calibration to lock HICK to USB SOF (see below) |
| USB CDC class (`usbd_class/cdc/`) | USB serial | CDC-ACM virtual COM port for Klipper host link |
| USB device drivers (`usbd_drivers/`) | USB stack | Core enumeration, interrupt handling, standard device requests |

### Unused HAL Modules (Dead Weight)

The following 18 HAL modules are present in the source tree but are **never
compiled** into a Klipper firmware image.  Klipper either does not need the
peripheral or provides its own register-level driver in `src/stm32/`.

> ADC (own driver in `stm32/adc.c`), BPR, CAN (own driver in `stm32/can.c`),
> CRC, DAC, DEBUG, DMA, EMAC, EXINT, I2C (own driver in `stm32/i2c.c`),
> MISC, PWC, RTC, SDIO, SPI (own driver in `stm32/spi.c`), WDT, WWDT, XMC

This is a deliberate design choice: Klipper's STM32 backend already contains
lean, timing-critical register-level implementations for ADC, CAN, I2C, and
SPI.  Using the vendor HAL for those would add overhead and an unnecessary
abstraction layer.

---

## ACC Implementation Detail

The **Auto Clock Calibration** peripheral is unique to the AT32 family and has
no equivalent on STM32F103.  It is used in this firmware to provide a
crystal-free 48 MHz USB clock source derived from the internal HICK oscillator.

### Code Path

`src/at32f403a/at32f403a.c`, lines 98–159 — `usb_clock48m_select()`:

```
When USB_CLK_HICK is selected:
  1. Enable ACC peripheral clock via CRM
  2. Write calibration boundary registers:
       C1 = 7980   (lower bound)
       C2 = 8000   (target count)
       C3 = 8020   (upper bound)
  3. Enable calibration:
       acc_calibration_mode_enable(ACC_CAL_HICKTRIM, TRUE)
```

### How It Works

The ACC hardware counts HICK oscillation cycles between consecutive USB
Start-of-Frame (SOF) packets, which arrive exactly every 1 ms on a compliant
USB bus.

| Parameter | Value | Meaning |
|-----------|-------|---------|
| C2 (target) | 8000 | At exactly 8 MHz, 8000 cycles fit in 1 ms |
| C1 (lower) | 7980 | −20 counts → −0.25 % below target |
| C3 (upper) | 8020 | +20 counts → +0.25 % above target |

If the measured count drifts outside the C1–C3 window, the ACC automatically
adjusts the HICK trim register to bring it back.  This forms a closed-loop
frequency-locked loop that continuously keeps the internal oscillator within
±0.25 % of 8 MHz.

### Why This Architecture

The AT32F403A derives its USB 48 MHz clock from HICK (internal oscillator)
rather than from the main PLL chain.  The system PLL path is:

```
HEXT crystal → PLL (up to 60×) → 240 MHz SCLK
```

The USB clock path is independent:

```
HICK (8 MHz) → ×6 multiplier → 48 MHz → USB peripheral
ACC calibrates HICK against USB SOF ──┘
```

This means the two clock domains are **decoupled**.  The external crystal
(HEXT) drives the CPU at 240 MHz; the ACC ensures USB timing is stable even
though it originates from an internal RC oscillator.

> **Important correction:** some community documentation claims the AT32F403A
> eliminates the need for an external crystal entirely.  This is **incorrect**
> for Klipper's configuration.  HEXT (external crystal) **is** used for the
> 240 MHz system PLL.  The ACC provides a crystal-free **USB** clock source
> only — it does not replace HEXT for the core clock.

---

## Key Register-Level Divergences from STM32

The AT32F403A is register-compatible with the STM32F103 in broad strokes, but
diverges in naming, layout, and capability in several critical areas.  These
divergences explain why `src/at32f403a/` exists as a separate port rather than
being folded entirely into `src/stm32/`.

### 1. CRM vs RCC — Clock & Reset Naming

| Concept | STM32 (RCC) | AT32 (CRM) |
|---------|-------------|------------|
| Peripheral name | RCC | CRM |
| AHB enable register | `RCC_AHBENR` | `CRM_AHBEN` |
| APB2 enable register | `RCC_APB2ENR` | `CRM_APB2EN` |
| PLL config register | `RCC_CFGR` | `CRM_CFG` |

Same general function, different register names and bit positions throughout.

### 2. ACC — No STM32F103 Equivalent

STM32F0/L0 series parts have **CRS** (Clock Recovery System), which is
conceptually similar (locks an internal oscillator to USB SOF), but the
register interface is completely different.  STM32F103 has no equivalent at
all.

### 3. GPIO GMUX — Extended Alternate-Function Multiplexing

AT32 adds **GMUX** registers that extend GPIO alternate-function mapping
beyond what STM32's AFIO remap bits provide.  This is why the port defines
dedicated remap helpers:

- `mcu_uart_gpio_remap()` — in `src/at32f403a/at32f403a.c`
- `mcu_can2_gpio_remap()` — in `src/at32f403a/at32f403a.c`
- `mcu_spi4_gpio_remap()` — in `src/at32f403a/at32f403a.c`

### 4. USART Flag & Instance Naming

| Concept | STM32 | AT32 |
|---------|-------|------|
| 5th UART instance | `USART5` | `UART5` |
| TX buffer empty flag | `USART_FLAG_TXE` | `USART_TDBE_FLAG` |
| Transmission complete flag | `USART_FLAG_TC` | `USART_TDC_FLAG` |

### 5. Timer Peripheral Naming

AT32 uses **TMR** (e.g. `TMR1`, `TMR2`) where STM32 uses **TIM** (`TIM1`,
`TIM2`).  At the CMSIS register level the layouts are compatible, but all
symbolic names differ.

### 6. Flash Sector Size

| Chip | Sector (page) size |
|------|--------------------|
| STM32F103 | 1024 bytes |
| AT32F403A | **2048 bytes** |

This directly affects `power_loss_check.c`, which must erase and write at
sector granularity when persisting stepper positions to flash.

### 7. USB Endpoint Double-Buffered Mode

The AT32F403A **omits** the `USB_EP_KIND` dummy write that STM32F1 requires
when toggling double-buffered endpoint mode.  This divergence is handled in
`src/stm32/usbfs.c`.

### 8. CAN IRQ Naming

| IRQ | STM32 | AT32 |
|-----|-------|------|
| CAN1 status-change/error | `CAN1_SCE_IRQn` | `CAN1_SE_IRQn` |
| CAN2 TX | (standard define) | Must be manually defined as IRQ **69** |
| CAN2 RX0 | (standard define) | Must be manually defined as IRQ **70** |
| CAN2 RX1 | (standard define) | Must be manually defined as IRQ **68** |
| CAN2 SE | (standard define) | Must be manually defined as IRQ **71** |

### 9. PLL Multiplier Range

| Chip | Max PLL multiplier | Max SCLK |
|------|--------------------|----------|
| STM32F103 | ×16 | 72 MHz |
| AT32F403A | **×60** | **240 MHz** |

The AT32 CRM HAL exposes multiplier values up to `CRM_PLL_MULT_60` to support
this.

### 10. Auto Step Mode (CRM)

AT32-specific CRM feature that allows safe PLL frequency switching without
glitches.  Not present in STM32 RCC at all.  Used during clock initialisation
in `at32f403a_407_clock.c`.

---

## Implications for This Port

### Build Size

Only 10 of 26 HAL modules (plus USB class/driver files) are compiled.  The
remaining 18 modules contribute zero bytes to the firmware binary but do add
maintenance surface area to the vendored tree.

### Maintenance Boundary

The HAL is consumed **as-is** from Artery's BSP SDK v2.1.6.  Modifications to
files under `lib/at32f403a/hal/` should be avoided; any workarounds belong in
the Klipper port layer (`src/at32f403a/` or `src/stm32/`).

### STM32 Code Reuse

Despite the naming differences, Klipper reuses a significant portion of its
`src/stm32/` backend for the AT32F403A.  The `src/at32f403a/` directory
contains only the board-init glue, remap helpers, and `Makefile`
additions — the actual peripheral drivers (ADC, CAN, I2C, SPI, USB, timers)
are shared with the STM32 port and operate at the register level, bypassing
the vendor HAL entirely for those peripherals.

### Clock Architecture

The dual-domain clock design (HEXT→PLL for core, HICK→ACC for USB) is a key
architectural difference from STM32F103, where both system and USB clocks
derive from the same PLL.  This must be kept in mind when modifying clock
initialisation code — the two paths are independent and must be configured
separately.
