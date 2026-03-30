# Hardware Libraries (lib/at32f403a, lib/at32f415, lib/rp2040)

## Summary
The fork adds two complete Artery Technology HAL (Hardware Abstraction Layer) libraries for the AT32 microcontrollers used in Snapmaker U1 hardware: `lib/at32f403a/` for the main board MCU and `lib/at32f415/` for the extruder head MCUs. These libraries provide the low-level peripheral drivers that Klipper's `src/stm32/` MCU code calls. The fork also patches `lib/rp2040/` with a minor change. None of these library directories exist in upstream Klipper.

---

## `lib/at32f403a/` — AT32F403A/407 HAL Library

### Summary
Complete Artery Technology HAL for the **AT32F403A/407** family (used as the U1 main board MCU). The AT32F403A is an STM32F103-compatible MCU from Artery Technology featuring up to 240 MHz clock, 256 KB flash, 96 KB RAM, and hardware-accelerated USB. The library provides peripheral drivers, startup code, linker scripts, and clock configuration.

### Contents
```
lib/at32f403a/
├── at32f403a_407.h              # Master include file
├── at32f403a_407_clock.c/h      # PLL/clock configuration (240 MHz via ACC)
├── at32f403a_407_conf.h         # HAL configuration switches
├── at32f403a_407_int.c/h        # Interrupt vector table
├── startup_at32f403a_407.s      # ARM assembly startup (CMSIS-compatible)
├── system_at32f403a_407.c/h     # SystemInit(), SystemCoreClock
├── usb_conf.h                   # USB device configuration
├── hal/
│   ├── inc/                     # HAL peripheral headers
│   └── src/                     # HAL peripheral drivers:
│       ├── at32f403a_407_acc.c  # Auto Clock Calibration (ACC) peripheral
│       ├── at32f403a_407_adc.c  # ADC driver
│       ├── at32f403a_407_bpr.c  # Battery-powered registers
│       ├── at32f403a_407_can.c  # CAN bus driver
│       ├── at32f403a_407_crc.c  # CRC calculation
│       ├── at32f403a_407_crm.c  # Clock and Reset Management
│       ├── at32f403a_407_dac.c  # DAC driver
│       ├── at32f403a_407_debug.c # Debug/CoreSight
│       ├── at32f403a_407_dma.c  # DMA controller
│       ├── at32f403a_407_emac.c # Ethernet MAC (AT32F407 only)
│       ├── at32f403a_407_exint.c # External interrupt
│       ├── at32f403a_407_flash.c # Flash erase/program (used by power_loss_check)
│       ├── at32f403a_407_gpio.c  # GPIO
│       ├── at32f403a_407_i2c.c  # I2C master/slave
│       ├── at32f403a_407_misc.c  # NVIC/SysTick
│       ├── at32f403a_407_pwc.c  # Power control
│       ├── at32f403a_407_rtc.c  # Real-time clock
│       ├── at32f403a_407_sdio.c # SDIO
│       ├── at32f403a_407_spi.c  # SPI master/slave
│       ├── at32f403a_407_tmr.c  # Timer (used by inductance_coil)
│       ├── at32f403a_407_usart.c # UART/USART
│       └── ...
├── linker/
│   ├── AT32F403AxC_FLASH.ld     # 256 KB flash linker script
│   ├── AT32F403AxE_FLASH.ld     # 512 KB variant
│   ├── AT32F403AxG_FLASH.ld     # 1024 KB variant
│   ├── AT32F407xC_FLASH.ld      # F407 256 KB variant
│   └── ...
├── usbd_class/                  # USB device class drivers (CDC, HID)
└── usbd_drivers/                # USB device stack
```

### Integration with Klipper
- `src/stm32/at32f403a.c` includes `at32f403a_407.h` and calls `at32f403a_407_clock.c` functions to initialise the 240 MHz PLL with ACC auto-calibration
- `src/stm32/inductance_coil.c` uses `at32f403a_407_tmr.c` for Timer2 frequency counting
- `src/stm32/power_loss_check.c` uses `at32f403a_407_flash.c` for wear-levelled state storage
- The Klipper build system (`lava/at32f403a_config`) selects `CONFIG_BOARD_DIRECTORY="stm32"` and uses `CONFIG_MCU="stm32f103xe"` — the AT32 is treated as STM32F103xe-compatible by the Klipper build, but the AT32-specific `at32f403a.c` overrides clock init and peripheral remapping

### Key Differences from STM32F103
The AT32F403A is pin/peripheral compatible with STM32F103 but adds:
- **ACC (Auto Clock Calibration)** peripheral — allows USB-trimmed 240 MHz clock without external crystal
- **Extended flash** — dual-bank flash with larger sectors, used by `power_loss_check.c`
- **Additional UART/SPI/CAN peripherals** — enables CAN2 on PA12/PB12, SPI4, UART5
- **240 MHz max clock** — requires Klipper timing calculations to account for 3× higher MCU frequency

---

## `lib/at32f415/` — AT32F415RC HAL Library

### Summary
Complete Artery Technology HAL for the **AT32F415** family (used as U1 extruder head MCUs, one per extruder). The AT32F415RC is an STM32F105-compatible MCU featuring 144 MHz clock, 256 KB flash, 32 KB RAM, and USB OTG. Each extruder head (T0–T3) has one AT32F415RC.

### Contents
```
lib/at32f415/
├── at32f415.h                   # Master include
├── at32f415_clock.c/h           # PLL config (144 MHz via USB OTG PLL)
├── at32f415_conf.h              # HAL configuration switches
├── at32f415_int.c/h             # Interrupt vector table
├── system_at32f415.c/h          # SystemInit()
├── usb_conf.h                   # USB device/host configuration
├── hal/
│   ├── inc/                     # Headers for AT32F415 peripherals
│   └── src/                     # Peripheral drivers (ADC, CAN, CRM, DMA,
│                                #   EXINT, FLASH, GPIO, I2C, MISC, PWC,
│                                #   SPI, TMR, USART, etc.)
├── usb_drivers/                 # USB OTG device stack (lower level)
├── usbd_class/                  # USB CDC, HID classes
├── usbh_class/                  # USB host class (Host mode capability)
└── startup / linker scripts
```

### Integration with Klipper
- `src/stm32/at32f415rc.c` includes `at32f415.h` and uses `at32f415_clock.c` to initialise USB OTG PLL at 144 MHz
- The Klipper build uses `CONFIG_MCU="stm32f105xc"` (STM32F105 compatible) and `CONFIG_USBSERIAL=y` — each extruder head communicates with the SoC host over USB CDC serial
- AT32F415 has no EMAC (no Ethernet); the HAL is smaller than AT32F403A
- USB host capability (`usbh_class/`) is present in the HAL but unused by Klipper firmware

---

## `lib/rp2040/` — RP2040 Library Patch

The fork includes a small patch file `lib/rp2040/rp2040.patch` applied to the upstream RP2040 library. This appears to be a minor build compatibility fix. The RP2040 library itself is otherwise identical to upstream; the patch adjusts linker script handling for the fork's build environment.

**Note:** The U1 does not use an RP2040; this patch is likely a carry-over from development tooling or a build system compatibility fix.

---

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No AT32 HAL libraries | `lib/at32f403a/`, `lib/at32f415/` added | U1 uses Artery AT32 MCUs |
| RP2040 library unpatched | `rp2040.patch` applied | Build environment compatibility |

## Additions
- `lib/at32f403a/` — 50+ HAL source files + linker scripts + USB stack
- `lib/at32f415/` — 40+ HAL source files + linker scripts + USB OTG stack + USB host

## Risks / Compatibility Notes
- The AT32 HAL libraries are proprietary Artery Technology code — license must be verified before redistribution (they appear to use a permissive BSD-like license based on standard embedded HAL practices)
- `CONFIG_MCU="stm32f103xe"` / `"stm32f105xc"` aliases work only because AT32 is register-compatible; any upstream Klipper change that adds AT32-specific register differences would require updating these aliases
- The 240 MHz / 144 MHz clock speeds require that all Klipper timing constants that depend on MCU frequency are correctly calculated — errors would cause stepper timing glitches
- USB by-path addressing in `lava/printer.cfg` is tied to the specific USB hub topology of the U1 PCB assembly
