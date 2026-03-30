# AT32 MCU Architecture Overview

## 1. Overview

This document describes the architecture of the AT32F403A and AT32F415 MCU support
in the Snapmaker U1 Klipper fork. Both Artery AT32 chips are integrated into the
existing STM32F1 code path through a "disguise" mechanism: they declare themselves
as STM32F1 MCU variants at the Kconfig level, inheriting the STM32F1 initialization
flow and CMSIS register definitions, while overriding chip-specific subsystems
(clocks, USB, peripheral HAL) with Artery's own HAL libraries. This approach
minimises the diff against upstream Klipper while supporting two chips that are
register-compatible with STM32F1 at the CMSIS level but diverge significantly in
clock tree, USB peripheral, and extended peripheral set.

---

## 2. The Disguise Mechanism

### 2.1 Kconfig MCU String Declaration

Each AT32 chip declares an STM32F1 MCU string, which the build system passes to the
compiler as a `-D` define. This activates the correct CMSIS header set:

```kconfig
# src/stm32/Kconfig, lines 203-204
config MCU
    default "stm32f105xc" if MACH_AT32F415
    default "stm32f103xe" if MACH_AT32F403A
```

- **AT32F415** masquerades as `stm32f105xc` (a Connectivity Line part with USB OTG).
- **AT32F403A** masquerades as `stm32f103xe` (a high-density part with USB FS).

The MCU string choice is deliberate: it selects the STM32F1 CMSIS variant whose
peripheral register layout most closely matches each AT32 chip's register map.

### 2.2 Compiler Defines and CMSIS Header Activation

The Makefile converts the MCU string to an uppercase define:

```makefile
# src/stm32/Makefile, line 21
MCU_UPPER := $(shell echo $(CONFIG_MCU) | tr a-z A-Z | tr X x)
```

This produces `STM32F105xC` or `STM32F103xE`, which is passed as `-D$(MCU_UPPER)`
(line 38). The STM32F1 CMSIS headers (`lib/stm32f1/`) use this define to gate
peripheral register definitions, making the AT32 chips appear as STM32F1 variants
to all code that uses CMSIS-style register access (`RCC->`, `GPIOA->`, `TIM1->`,
etc.).

In parallel, the Makefile also defines the actual AT32 part number:

```makefile
# src/stm32/Makefile, lines 26, 28
CFLAGS-$(CONFIG_MACH_AT32F403A) += -DAT32F407RCT7 -Ilib/at32f403a -Ilib/at32f403a/hal/inc
CFLAGS-$(CONFIG_MACH_AT32F415)  += -DAT32F415RCT7 -Ilib/at32f415 -Ilib/at32f415/hal/inc
```

This means **both** header sets are active simultaneously: STM32F1 CMSIS headers
provide base register definitions, while AT32 HAL headers provide vendor-specific
peripheral APIs (CRM, ACC, extended GPIO, extended timer, etc.).

### 2.3 CMSIS Header Coexistence

`lib/stm32f1/system_stm32f1xx.c` **is** compiled for both AT32 chips (Makefile
lines 55, 57). The STM32F1 CMSIS `stm32f1xx.h` brings in register definitions for
GPIO, timers, NVIC, and other base peripherals that are register-compatible between
STM32F1 and AT32F4x at the CMSIS abstraction level.

---

## 3. Build System Selection Logic

### 3.1 Kconfig Processor Selection

```kconfig
# src/stm32/Kconfig, lines 114-121
config MACH_AT32F415
    bool "AT32F415"
    select MACH_STM32F1
    select MACH_AT32F4x
config MACH_AT32F403A
    bool "AT32F403A"
    select MACH_STM32F1
    select MACH_AT32F4x
```

Both chips select **two** machine flags:

| Flag | Purpose |
|------|---------|
| `MACH_STM32F1` | Reuse the STM32F1 init flow, GPIO, timer, interrupt infrastructure |
| `MACH_AT32F4x` | Gate shared AT32-specific code (inductance coil, power loss, debug logging) |

`MACH_AT32F4x` is declared as a silent bool (lines 156-157) — it is never directly
user-selectable, only auto-selected by a processor choice.

### 3.2 USB Peripheral Selection

The AT32 chips have different USB hardware, and Kconfig explicitly routes them:

```kconfig
# src/stm32/Kconfig, line 161 — USB FS
config HAVE_STM32_USBFS
    default y if (MACH_STM32F1 || MACH_STM32F070) && !STM32_CLOCK_REF_INTERNAL && !MACH_AT32F415
```

AT32F415 is **excluded** from USB FS because it uses USB OTG hardware instead:

```kconfig
# src/stm32/Kconfig, line 164 — USB OTG
config HAVE_STM32_USBOTG
    default y if MACH_STM32F2 || MACH_STM32F4 || MACH_STM32F7 || MACH_STM32H7 || MACH_AT32F415
```

AT32F403A uses USB FS (inherited from `MACH_STM32F1` default) and additionally
supports USB-CAN bridge mode:

```kconfig
# src/stm32/Kconfig, line 175 — USB CAN bus
config HAVE_STM32_USBCANBUS
    depends on !MACH_STM32F1 || MACH_AT32F403A
```

This `depends on` line means: USB CAN bus is available for all non-STM32F1 chips,
**plus** AT32F403A specifically (which otherwise inherits `MACH_STM32F1`'s exclusion).

### 3.3 Makefile Source Selection

The Makefile conditionally adds AT32 HAL sources and include paths:

```makefile
# src/stm32/Makefile, lines 17-18
dirs-$(CONFIG_MACH_AT32F415)  += lib/at32f415 lib/at32f415/hal/src lib/stm32f1 ...
dirs-$(CONFIG_MACH_AT32F403A) += lib/at32f403a lib/at32f403a/hal/src ...
```

AT32 HAL source files are added per-chip (lines 52-63), and shared AT32 modules
are added via the `MACH_AT32F4x` flag:

```makefile
# src/stm32/Makefile, line 64
src-$(CONFIG_MACH_AT32F4x) += stm32/inductance_coil.c stm32/power_loss_check.c
```

---

## 4. The Four New `src/stm32/` Files

### 4.1 `at32f403a.c` (185 lines)

Chip-specific initialisation for the AT32F403A:

- **`at32f403a_clock_setup()`** — Calls `system_clock_config()` (from
  `lib/at32f403a/at32f403a_407_clock.c`) to configure the 240 MHz PLL, then sets
  up USB 48 MHz from HICK with ACC calibration, and enables the USB peripheral clock.
- **`usb_clock48m_select()`** — Configures ACC (C1=7980, C2=8000, C3=8020) in
  HICKTRIM mode for USB clock recovery from HICK, or alternatively derives 48 MHz
  from SCLK via integer divider.
- **`uart_debug_print_init()`** — Configures USART3 TX on PB10 for debug logging.
- **`mcu_uart_gpio_remap()`** — Remaps UART5 via `UART5_GMUX_0001`.
- **`mcu_can2_gpio_remap()`** — Remaps CAN2 via `CAN2_GMUX_0001`.
- **`mcu_spi4_gpio_remap()`** — Remaps SPI4 via `SPI4_GMUX_0001`.

### 4.2 `at32f403a.h` (38 lines)

Function declarations for `at32f403a.c`, plus debug logging macros:

```c
#define LOG_E(format) at32f403a_log("[E]" TAG format)
#define LOG_W(format) at32f403a_log("[W]" TAG format)
#define LOG_I(format) at32f403a_log("[I]" TAG format)
#define LOG_V(format) at32f403a_log("[V]" TAG format)
```

Macros compile to no-ops when `CONFIG_MACH_AT32F403A` is not set.

### 4.3 `at32f415rc.c` (118 lines)

Chip-specific initialisation for the AT32F415:

- **`at32f415rc_clock_setup()`** — Calls `system_clock_config()` (from
  `lib/at32f415/at32f415_clock.c`) to configure the 144 MHz PLL.
- **`at32f415rc_usbotg_clock_config()`** — Enables OTG peripheral clock and
  derives USB 48 MHz from HEXT via divider (144 / 3 = 48 MHz). No ACC needed.
- **`uart_debug_print_init()`** — Configures USART3 TX on PB10 for debug logging.

### 4.4 `at32f415rc.h` (27 lines)

Function declarations for `at32f415rc.c`, plus the same LOG macro pattern (compiles
to no-ops when `CONFIG_MACH_AT32F415` is not set).

### 4.5 U1-Specific Hardware Modules

Two additional files are shared across both AT32 chips via `CONFIG_MACH_AT32F4x`:

- **`inductance_coil.c` (674 lines)** — Frequency measurement using timer input
  capture for inductive bed probing. Uses AT32 CRM and TMR HAL APIs with
  chip-specific `#if` blocks for timer and CRM peripheral differences.
- **`power_loss_check.c` (685 lines)** — Power loss detection using GPIO edge
  detection and timer input capture, with stepper motor position storage to flash.
  Chip-specific parameters include flash sector size, flash addresses, and
  detection GPIO pin assignments.

---

## 5. Clock Topology: AT32F403A (240 MHz)

Source: `lib/at32f403a/at32f403a_407_clock.c` → `system_clock_config()`

### 5.1 PLL Configuration

```
HEXT (8 MHz crystal)
  └─ HEXT_DIV_2 → 4 MHz
       └─ PLL_MULT_60 → 240 MHz SCLK
            ├─ AHB_DIV_1  → 240 MHz AHB
            ├─ APB1_DIV_2 → 120 MHz APB1
            └─ APB2_DIV_2 → 120 MHz APB2
```

### 5.2 Register-Level Sequence

```c
crm_reset();
crm_clock_source_enable(CRM_CLOCK_SOURCE_HEXT, TRUE);
// wait for HEXT stable
crm_pll_config(CRM_PLL_SOURCE_HEXT_DIV, CRM_PLL_MULT_60, CRM_PLL_OUTPUT_RANGE_GT72MHZ);
crm_hext_clock_div_set(CRM_HEXT_DIV_2);
crm_clock_source_enable(CRM_CLOCK_SOURCE_PLL, TRUE);
// wait for PLL stable
crm_ahb_div_set(CRM_AHB_DIV_1);
crm_apb2_div_set(CRM_APB2_DIV_2);
crm_apb1_div_set(CRM_APB1_DIV_2);
crm_auto_step_mode_enable(TRUE);           // gradual frequency ramp
crm_sysclk_switch(CRM_SCLK_PLL);
// wait for PLL as system clock source
crm_auto_step_mode_enable(FALSE);
system_core_clock_update();
```

Auto step mode is enabled **during** the PLL switch to ensure bus timing stability
while transitioning from the default clock to 240 MHz.

### 5.3 USB 48 MHz (HICK + ACC)

The AT32F403A derives its USB 48 MHz clock from the internal HICK oscillator,
calibrated by the ACC peripheral using USB SOF frames. See Section 7 for details.

### 5.4 Klipper CLOCK_FREQ

```kconfig
# src/stm32/Kconfig, line 224
default 240000000 if MACH_AT32F403A
```

`FREQ_PERIPH` (used for timer and UART baud rate calculations) is defined as
`CONFIG_CLOCK_FREQ / 2` = **120 MHz** (`src/stm32/stm32f1.c`, line 20).

---

## 6. Clock Topology: AT32F415RC (144 MHz)

Source: `lib/at32f415/at32f415_clock.c` → `system_clock_config()`

### 6.1 PLL Configuration

```
HEXT (8 MHz crystal)
  └─ PLL_SOURCE_HEXT_DIV (implied /2) → 4 MHz
       └─ PLL_MULT_36 → 144 MHz SCLK
            ├─ AHB_DIV_1  → 144 MHz AHB
            ├─ APB1_DIV_2 → 72 MHz APB1
            └─ APB2_DIV_2 → 72 MHz APB2
```

### 6.2 Register-Level Sequence

```c
crm_reset();
flash_psr_set(FLASH_WAIT_CYCLE_4);        // 4 wait states for 144 MHz
crm_clock_source_enable(CRM_CLOCK_SOURCE_HEXT, TRUE);
// wait for HEXT stable
crm_pll_config(CRM_PLL_SOURCE_HEXT_DIV, CRM_PLL_MULT_36);
crm_clock_source_enable(CRM_CLOCK_SOURCE_PLL, TRUE);
// wait for PLL stable
crm_ahb_div_set(CRM_AHB_DIV_1);
crm_apb2_div_set(CRM_APB2_DIV_2);
crm_apb1_div_set(CRM_APB1_DIV_2);
crm_auto_step_mode_enable(TRUE);
crm_sysclk_switch(CRM_SCLK_PLL);
// wait for PLL as system clock source
crm_auto_step_mode_enable(FALSE);
system_core_clock_update();
```

Key difference from F403A: flash wait cycles are explicitly set to 4
(`FLASH_WAIT_CYCLE_4`) before the clock switch, and the PLL config call takes
only two arguments (no output range parameter).

### 6.3 USB 48 MHz (HEXT Divider)

```c
// src/stm32/at32f415rc.c — at32f415rc_usbotg_clock_config()
crm_periph_clock_enable(OTG_CLOCK, TRUE);
usb_clock48m_select(USB_CLK_HEXT);
// at 144 MHz: crm_usb_clock_div_set(CRM_USB_DIV_3) → 144 / 3 = 48 MHz
```

The AT32F415 derives USB 48 MHz directly from the system clock via a fixed divider.
**No ACC peripheral is needed or available** — the AT32F415 HAL does not include
an ACC module (`at32f415_acc.h` does not exist).

### 6.4 Klipper CLOCK_FREQ

```kconfig
# src/stm32/Kconfig, line 223
default 144000000 if MACH_AT32F415
```

`FREQ_PERIPH` = **72 MHz**.

---

## 7. ACC (Auto Clock Calibration) Deep Dive

The ACC peripheral is exclusive to the AT32F403A. It trims the internal HICK
oscillator to produce a stable 48 MHz USB clock, using USB Start-of-Frame (SOF)
packets as a frequency reference.

### 7.1 How It Works

USB SOF packets arrive at exactly 1 kHz (every 1 ms). The ACC hardware counts HICK
clock cycles between consecutive SOF edges. At a perfect 48 MHz HICK (divided down
to 8 MHz internally), there should be exactly **8000 counts per SOF interval**.

The ACC continuously compares the actual count against three programmable boundaries:

```c
// src/stm32/at32f403a.c — usb_clock48m_select()
acc_write_c1(7980);   // lower bound
acc_write_c2(8000);   // target centre
acc_write_c3(8020);   // upper bound
```

| Register | Value | Meaning |
|----------|-------|---------|
| C1 | 7980 | If count < 7980, HICK is too slow → trim up aggressively |
| C2 | 8000 | Target count (8 MHz × 1 ms = 8000 cycles) |
| C3 | 8020 | If count > 8020, HICK is too fast → trim down aggressively |

Between C1 and C3, fine-grained trimming is applied proportionally.

### 7.2 Calibration Mode

```c
acc_calibration_mode_enable(ACC_CAL_HICKTRIM, TRUE);
```

`ACC_CAL_HICKTRIM` means the ACC continuously adjusts the HICK trim value (as
opposed to `ACC_CAL_HICKCAL` which would set a one-time calibration). HICKTRIM
provides ongoing compensation for temperature drift and supply voltage variation.

### 7.3 Clock Source Selection

```c
crm_usb_clock_source_select(CRM_USB_CLOCK_SOURCE_HICK);
crm_periph_clock_enable(CRM_ACC_PERIPH_CLOCK, TRUE);
```

The USB peripheral clock mux is switched to HICK (away from the PLL-derived path),
and the ACC peripheral clock is enabled so it can begin monitoring SOF timing.

### 7.4 Why HICK Instead of PLL?

The AT32F403A runs at 240 MHz. 240 is not evenly divisible by 48 (240 / 48 = 5.0 —
actually it is, but the available CRM dividers may not support an exact /5). The
`usb_clock48m_select()` function's PLL-derived path handles 48, 72, 96, 120, 144,
168, and 192 MHz — but not 240 MHz. Using HICK with ACC calibration sidesteps this
divider limitation entirely.

---

## 8. STM32 Code Reuse vs. AT32 Override

### 8.1 What Is Shared (STM32F1 Code Reused As-Is)

The following subsystems from `src/stm32/` work unmodified for AT32 chips because
they use CMSIS register definitions that are compatible:

- **GPIO** — `gpio_clock_enable()`, `gpio_peripheral()` in `stm32f1.c`
- **Timer infrastructure** — Timer setup, IRQ routing
- **NVIC / interrupt management** — Standard ARM Cortex-M NVIC
- **ADC** — `stm32/adc.c` is compiled for both AT32 chips
- **DMA** — DMA channel setup via CMSIS registers
- **System init** — `lib/stm32f1/system_stm32f1xx.c` is compiled for both

### 8.2 What Is Overridden (AT32-Specific Code)

| Subsystem | STM32F1 Path | AT32 Override |
|-----------|-------------|---------------|
| Clock setup | `clock_setup()` in `stm32f1.c` | `at32f403a_clock_setup()` / `at32f415rc_clock_setup()` called instead |
| USB FS | `usbfs.c` | AT32F403A: minor `#ifdef` for double-buffering flag |
| USB OTG | `usbotg.c` | AT32F415: custom OTG init path, VBUS sensing config |
| CAN | `can.c` | AT32F403A: CAN2 peripheral address, GPIO remap, IRQ names |
| SPI | `spi.c` | AT32F403A: SPI4 peripheral, pin remapping, bus table entries |
| CRM (Clock/Reset) | RCC registers | AT32 CRM HAL functions (crm_periph_clock_enable, etc.) |
| ACC | N/A | AT32F403A only — USB clock calibration |
| Flash | FLASH registers | AT32 flash HAL for power-loss stepper position storage |

### 8.3 The Clock Setup Override Mechanism

In `src/stm32/stm32f1.c`, the entire `clock_setup()` function is conditionally
compiled out for AT32 chips:

```c
// src/stm32/stm32f1.c, lines 54-97
#if CONFIG_MACH_AT32F415
    #include "at32f415rc.h"
#elif CONFIG_MACH_AT32F403A
    #include "at32f403a.h"
#else
static void
clock_setup(void)
{
    // ... standard STM32F1 PLL setup ...
}
#endif
```

And in the main init function:

```c
// src/stm32/stm32f1.c, lines 278-284
#if CONFIG_MACH_AT32F415
    at32f415rc_clock_setup();
#elif CONFIG_MACH_AT32F403A
    at32f403a_clock_setup();
#else
    clock_setup();
#endif
```

This means the standard STM32F1 `clock_setup()` function **does not exist** in
AT32 builds — it is replaced entirely by the AT32-specific version, not just
bypassed at runtime.

---

## 9. Modified Upstream Files

The following upstream Klipper files contain AT32-specific `#ifdef` blocks:

| File | Guard(s) Used | Changes |
|------|---------------|---------|
| `src/stm32/stm32f1.c` | `CONFIG_MACH_AT32F415`, `CONFIG_MACH_AT32F403A` | Clock setup function replaced with AT32-specific calls; AT32 header includes |
| `src/stm32/can.c` | `CONFIG_MACH_AT32F403A` | CAN2 peripheral base address definition, CAN2 GPIO remap call, CAN IRQ name mapping for CAN1/CAN2 |
| `src/stm32/spi.c` | `CONFIG_MACH_AT32F403A` | SPI4 peripheral base address and bus declaration, SPI3a alternate pins, SPI4 GPIO remap call, modified pin table entries |
| `src/stm32/usbfs.c` | `CONFIG_MACH_AT32F403A` | USB endpoint double-buffering flag handling (skip `USB_EP_KIND` write) |
| `src/stm32/usbotg.c` | `CONFIG_MACH_AT32F415` | GPIO pin/function defines bypassed (AT32F415 uses different OTG init), USB OTG clock enable path, VBUS sensing register config (`GCCFG` with `VBUSBSEN \| NOVBUSSENS`) |
| `src/stm32/Kconfig` | `MACH_AT32F415`, `MACH_AT32F403A`, `MACH_AT32F4x` | Processor choices, MCU string mapping, USB peripheral routing, clock frequency defaults |
| `src/stm32/Makefile` | `CONFIG_MACH_AT32F415`, `CONFIG_MACH_AT32F403A`, `CONFIG_MACH_AT32F4x` | Include paths, CFLAGS, HAL source files, chip-specific source files |

### 9.1 Detailed Change Descriptions

**`can.c`** — Adds CAN2 support for AT32F403A. CAN2 base address is defined
inline (`APB1PERIPH_BASE + 0x6800`). Separate `#if` blocks define `SOC_CAN`,
`FILTER_CAN`, and IRQ names for CAN1 vs CAN2 depending on the selected CAN pin
configuration. The `mcu_can2_gpio_remap()` function is called during CAN init when
PB5/PB6 pins are selected.

**`spi.c`** — Adds SPI3 alternate pins (SPI3a on PC10/PC11/PC12) and SPI4
(PE11/PE13/PE14) for AT32F403A. SPI4 base address is defined inline
(`APB1PERIPH_BASE + 0x4000`). The SPI bus table includes AT32F403A-specific entries
with different pin assignments (notably SPI2 uses PA10/PA11/PF1 instead of the
STM32F1 default). `mcu_spi4_gpio_remap()` is called when SPI4 is selected.

**`usbfs.c`** — A single guard skips the `USB_EP_KIND` write for AT32F403A,
working around a difference in the AT32's USB endpoint double-buffering register
behaviour.

**`usbotg.c`** — The AT32F415 OTG init path bypasses the standard STM32 GPIO
configuration and USB clock enable sequence. The VBUS sensing configuration uses
`USB_OTG_GCCFG_VBUSBSEN | USB_OTG_GCCFG_NOVBUSSENS` (both bits set), which differs
from both the STM32F4 path (`GOTGCTL` register) and the default STM32F2 path
(`NOVBUSSENS` only).
