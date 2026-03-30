# AT32 Build System Integration

## Overview

The AT32F415 and AT32F403A are integrated into Klipper's existing STM32 build
system through a "disguise" strategy: both chips select `MACH_STM32F1` so they
inherit all STM32F1 infrastructure (linker scripts, flash tooling, shared
source files), while AT32-specific Kconfig symbols, compiler flags, and source
files layer on top. The user sees "AT32F415" and "AT32F403A" as first-class
entries in `menuconfig`; internally the build maps them to STM32 MCU strings
(`stm32f105xc` and `stm32f103xe` respectively) so that standard STM32 flash
tools work unchanged.

A shared selector `MACH_AT32F4x` groups behaviour common to both AT32 chips
(inductance coil sensing, power-loss detection) without duplicating Kconfig
logic.

---

## Kconfig Symbols

All AT32-related Kconfig entries live in `src/stm32/Kconfig`.

### Processor model entries

Added inside the existing `choice "Processor model"`:

```kconfig
config MACH_AT32F415
    bool "AT32F415"
    select MACH_STM32F1
    select MACH_AT32F4x

config MACH_AT32F403A
    bool "AT32F403A"
    select MACH_STM32F1
    select MACH_AT32F4x
```

Both chips select `MACH_STM32F1`, which brings in the STM32F1 source set, the
ARM Cortex-M linker script, and all STM32F1-gated peripherals. The additional
`MACH_AT32F4x` selector gates shared AT32-only sources.

### Shared selector

```kconfig
config MACH_AT32F4x
    bool
```

This is never user-visible; it is selected automatically by either AT32 chip.

### MCU string aliases

```kconfig
config MCU
    default "stm32f105xc" if MACH_AT32F415
    default "stm32f103xe" if MACH_AT32F403A
```

These aliases are consumed by the flash tooling (`scripts/flash_usb.py`,
`stm32flash`). Because the AT32 chips implement the same DFU/serial bootloader
protocol as STM32, standard STM32 flash tools work without modification.

### Clock frequencies

```kconfig
config CLOCK_FREQ
    default 144000000 if MACH_AT32F415   # 144 MHz
    default 240000000 if MACH_AT32F403A  # 240 MHz
```

Both values exceed the typical STM32F1 72 MHz ceiling, reflecting the AT32
parts' higher core clock capability.

### Flash and RAM sizes

```kconfig
config FLASH_SIZE
    default 0x40000 if MACH_AT32F415    # 256 KB
    default 0x40000 if MACH_AT32F403A   # 256 KB

config RAM_SIZE
    default 0x8000  if MACH_AT32F415    #  32 KB
    default 0x18000 if MACH_AT32F403A   #  96 KB
```

These values feed directly into the generic ARM Cortex-M linker script
(`generic/armcm_link.ld`) to define FLASH and RAM regions.

### USB routing

USB peripheral selection is critical because the AT32F415 has a USB-OTG
controller (not the USB-FS controller found on most STM32F1 parts):

```kconfig
config HAVE_STM32_USBFS
    default y if (MACH_STM32F1 || MACH_STM32F070) && !STM32_CLOCK_REF_INTERNAL && !MACH_AT32F415
    # AT32F415 explicitly EXCLUDED from USB-FS

config HAVE_STM32_USBOTG
    default y if MACH_STM32F2 || MACH_STM32F4 || MACH_STM32F7 || MACH_STM32H7 || MACH_AT32F415
    # AT32F415 explicitly ADDED to USB-OTG
```

The AT32F403A does not add itself to either USB symbol but participates in
USB-CAN bridging via a separate override:

```kconfig
config HAVE_STM32_USBCANBUS
    depends on !MACH_STM32F1 || MACH_AT32F403A
    # STM32F1 is normally excluded; AT32F403A overrides this exclusion
```

### CAN bus pin options extended

The AT32F403A is added alongside `MACH_STM32F4` for alternate CAN pin
mappings:

```kconfig
config STM32_CMENU_CANBUS_PB5_PB6
    depends on (HAVE_STM32_CANBUS && (MACH_STM32F4 || MACH_AT32F403A)) || ...

config STM32_CMENU_CANBUS_PB12_PB13
    depends on (HAVE_STM32_CANBUS && (MACH_STM32F4 || MACH_AT32F403A)) || ...
```

### AT32-specific serial and USB-CAN options

```kconfig
config STM32_SERIAL_AT_USART5_PB8_PB9
    bool "Serial (on arterytek_403A USART5 PB8/PB9)" if LOW_LEVEL_OPTIONS
    depends on MACH_AT32F403A
    select SERIAL

config STM32_USBCANBUS_PA11_PA12_AND_SERIAL_USART5_PB8_PB9
    bool "USB to CAN bus bridge (USB on PA11/PA12) and use Serial(PB8/PB9)..."
    depends on (HAVE_STM32_USBCANBUS && MACH_AT32F403A)
    select USBCANBUS
    select SERIAL
```

These expose hardware-specific USART5 routing on the AT32F403A. The combined
USB-CAN-plus-serial option enables running CAN bus bridge firmware while still
maintaining a debug serial port.

### Debug UART

```kconfig
config AT32_ENABLE_DEBUG_USART
    bool "Enable debug serial (Both AT32F415 and AT32F403A use PB10)"
    depends on (MACH_AT32F415 || MACH_AT32F403A) && LOW_LEVEL_OPTIONS
    default n
```

Both AT32 chips share the same debug USART pin (PB10). This is off by default
and only visible under `LOW_LEVEL_OPTIONS`.

### SWD disable

The existing SWD disable option is extended to include the AT32F403A:

```kconfig
config STM32F103GD_DISABLE_SWD
    depends on (MACH_STM32F103 || MACH_AT32F403A) && LOW_LEVEL_OPTIONS
```

### USB product suffix (`src/Kconfig`)

A new `USB_PRODUCT_SUFFIX` config is added in `src/Kconfig`:

```kconfig
config USB_PRODUCT_SUFFIX
    string "USB product suffix"
    default "-00000000000000-0000000000"
```

---

## menuconfig UX

From the user's perspective, the AT32 chips are first-class citizens in the
processor selection menu:

```
Processor model
  ( ) STM32F103
  ( ) STM32F207
  ...
  ( ) AT32F415
  ( ) AT32F403A
```

The user selects **AT32F415** or **AT32F403A** directly. They never need to
know about the internal STM32F1 mapping. Once selected, clock, flash, RAM,
USB, and communication options are automatically configured with appropriate
defaults.

AT32-specific menu items (debug UART, USART5 serial, combined USB-CAN+serial)
appear only when the corresponding AT32 chip is selected and `LOW_LEVEL_OPTIONS`
is enabled where applicable.

---

## Makefile Structure

All AT32-related Makefile additions are in `src/stm32/Makefile`.

### Directory includes

Each chip adds its own vendor HAL directories and USB stack directories:

```makefile
# AT32F415
dirs-$(CONFIG_MACH_AT32F415) += lib/at32f415
dirs-$(CONFIG_MACH_AT32F415) += lib/at32f415/hal/src
dirs-$(CONFIG_MACH_AT32F415) += lib/stm32f1
dirs-$(CONFIG_MACH_AT32F415) += lib/at32f415/usbd_class/cdc
dirs-$(CONFIG_MACH_AT32F415) += lib/at32f415/usb_drivers/src

# AT32F403A
dirs-$(CONFIG_MACH_AT32F403A) += lib/at32f403a
dirs-$(CONFIG_MACH_AT32F403A) += lib/at32f403a/hal/src
dirs-$(CONFIG_MACH_AT32F403A) += lib/at32f403a/usbd_class/cdc
dirs-$(CONFIG_MACH_AT32F403A) += lib/at32f403a/usbd_drivers/src
```

Note: AT32F415 includes `lib/stm32f1` as an additional directory; AT32F403A
does not. Both inherit STM32F1 sources through `MACH_STM32F1` regardless.

---

## Compiler Flags

```makefile
# AT32F415
CFLAGS-$(CONFIG_MACH_AT32F415) += -mcpu=cortex-m4
CFLAGS-$(CONFIG_MACH_AT32F415) += -DAT32F415RCT7
CFLAGS-$(CONFIG_MACH_AT32F415) += -Ilib/at32f415 -Ilib/at32f415/hal/inc
CFLAGS-$(CONFIG_MACH_AT32F415) += -Ilib/at32f415/usb_drivers/inc -Ilib/at32f415/usbd_class/cdc

# AT32F403A
CFLAGS-$(CONFIG_MACH_AT32F403A) += -mcpu=cortex-m4
CFLAGS-$(CONFIG_MACH_AT32F403A) += -DAT32F407RCT7
CFLAGS-$(CONFIG_MACH_AT32F403A) += -Ilib/at32f403a -Ilib/at32f403a/hal/inc
CFLAGS-$(CONFIG_MACH_AT32F403A) += -Ilib/at32f403a/usbd_drivers/inc -Ilib/at32f403a/usbd_class/cdc
```

### Key details

| Flag | AT32F415 | AT32F403A | Notes |
|------|----------|-----------|-------|
| `-mcpu` | `cortex-m4` | `cortex-m4` | Both are Cortex-M4 cores (STM32F1 is Cortex-M3) |
| `-D` define | `AT32F415RCT7` | `AT32F407RCT7` | Chip package defines for HAL header conditional compilation |
| HAL includes | `lib/at32f415/hal/inc` | `lib/at32f403a/hal/inc` | Separate vendor HAL per chip |
| USB includes | `usb_drivers/inc` | `usbd_drivers/inc` | Different USB driver stacks |

**Note on `-DAT32F407RCT7`:** The AT32F403A build defines `AT32F407RCT7` (not
`AT32F403ARCT7`). This is intentional — the Artery vendor HAL headers use the
F407 define for conditional compilation, and the F403A/F407 share the same
register definitions. This is the actual chip package define expected by the
HAL.

---

## Source File Selection

### Inherited STM32F1 sources (via `MACH_STM32F1`)

Both AT32 chips automatically get:

```makefile
src-$(CONFIG_MACH_STM32F1) += stm32/stm32f1.c generic/armcm_timer.c stm32/i2c.c
```

### Shared AT32 sources (via `MACH_AT32F4x`)

```makefile
src-$(CONFIG_MACH_AT32F4x) += stm32/inductance_coil.c stm32/power_loss_check.c
```

These are printer-specific features common to both AT32 chips (likely related
to the Elegoo Neptune series hardware).

### AT32F415-specific sources

```makefile
src-$(CONFIG_MACH_AT32F415) += stm32/at32f415rc.c
src-$(CONFIG_MACH_AT32F415) += stm32/adc.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/at32f415_clock.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/system_at32f415.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_usart.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_gpio.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_crm.c
src-$(CONFIG_MACH_AT32F415) += ../lib/stm32f1/system_stm32f1xx.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_tmr.c
src-$(CONFIG_MACH_AT32F415) += ../lib/at32f415/hal/src/at32f415_flash.c
```

Key observations:
- `at32f415rc.c` is the chip-specific init code (clock setup, GPIO defaults)
- Pulls in both `system_at32f415.c` (AT32 system init) and `system_stm32f1xx.c`
  (STM32F1 system stubs)
- HAL drivers for USART, GPIO, CRM (clock/reset), timer, and flash

### AT32F403A-specific sources

```makefile
src-$(CONFIG_MACH_AT32F403A) += stm32/at32f403a.c
src-$(CONFIG_MACH_AT32F403A) += stm32/adc.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/stm32f1/system_stm32f1xx.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/at32f403a_407_clock.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/system_at32f403a_407.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/hal/src/at32f403a_407_crm.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/hal/src/at32f403a_407_tmr.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/hal/src/at32f403a_407_gpio.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/hal/src/at32f403a_407_flash.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/hal/src/at32f403a_407_usart.c
src-$(CONFIG_MACH_AT32F403A) += ../lib/at32f403a/hal/src/at32f403a_407_acc.c
```

Key observations:
- The F403A HAL files all use `at32f403a_407_` prefix (shared API with F407)
- Includes `at32f403a_407_acc.c` (auto-clock-calibration) — not present in F415
- Also pulls in `system_stm32f1xx.c` for STM32F1 compatibility stubs

### Source file summary

| Source category | AT32F415 | AT32F403A | Notes |
|-----------------|----------|-----------|-------|
| Chip init | `at32f415rc.c` | `at32f403a.c` | Clock, GPIO, peripheral setup |
| ADC | `adc.c` (shared) | `adc.c` (shared) | Same STM32 ADC driver |
| Clock config | `at32f415_clock.c` | `at32f403a_407_clock.c` | Chip-specific PLL setup |
| System init | `system_at32f415.c` | `system_at32f403a_407.c` | Startup/vector table |
| STM32F1 stubs | `system_stm32f1xx.c` | `system_stm32f1xx.c` | Compatibility layer |
| HAL GPIO | `at32f415_gpio.c` | `at32f403a_407_gpio.c` | — |
| HAL USART | `at32f415_usart.c` | `at32f403a_407_usart.c` | — |
| HAL CRM | `at32f415_crm.c` | `at32f403a_407_crm.c` | Clock/reset management |
| HAL Timer | `at32f415_tmr.c` | `at32f403a_407_tmr.c` | — |
| HAL Flash | `at32f415_flash.c` | `at32f403a_407_flash.c` | — |
| HAL ACC | — | `at32f403a_407_acc.c` | Auto clock calibration |
| Shared AT32 | `inductance_coil.c` | `inductance_coil.c` | Via `MACH_AT32F4x` |
| Shared AT32 | `power_loss_check.c` | `power_loss_check.c` | Via `MACH_AT32F4x` |
| Inherited STM32F1 | `stm32f1.c`, `armcm_timer.c`, `i2c.c` | same | Via `MACH_STM32F1` |

---

## Linker Configuration

The AT32 builds use the **same linker script** as all other ARM Cortex-M
targets in Klipper:

```
generic/armcm_link.ld
```

The memory map is defined entirely by Kconfig symbols:

| Symbol | AT32F415 | AT32F403A |
|--------|----------|-----------|
| `FLASH_SIZE` | `0x40000` (256 KB) | `0x40000` (256 KB) |
| `RAM_SIZE` | `0x8000` (32 KB) | `0x18000` (96 KB) |
| `RAM_START` | inherited default | inherited default |
| `FLASH_APPLICATION_ADDRESS` | inherited default | inherited default |

No AT32-specific linker scripts are used by the build system. The directory
`lib/at32f403a/linker/` contains 6 standalone `.ld` files from the vendor SDK,
but none are referenced by the Makefile or any build target.

---

## Flash Tooling

AT32 flashing uses the **exact same tools** as STM32:

| Method | Command | Tool |
|--------|---------|------|
| `make flash` | `scripts/flash_usb.py` | Uses `CONFIG_MCU` string |
| `make serialflash` | `stm32flash` | Serial bootloader |

The `CONFIG_MCU` values (`stm32f105xc` for AT32F415, `stm32f103xe` for
AT32F403A) cause the flash tools to treat the chip as a standard STM32. This
works because:

1. AT32 chips implement the same DFU bootloader protocol as STM32
2. AT32 chips implement the same serial (USART) bootloader protocol as STM32
3. The flash memory layout is compatible with STM32 expectations

No AT32-specific flash tools, scripts, or protocols are needed. The STM32
"disguise" in `CONFIG_MCU` is sufficient for all flashing operations.
