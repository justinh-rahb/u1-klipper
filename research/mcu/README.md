# AT32 MCU C Source Analysis — Summary Report

## Scope

This analysis covers the AT32 MCU implementation in the Snapmaker U1 Klipper fork, focusing on the C source layer (`src/stm32/` additions and modifications) and the two AT32 HAL libraries (`lib/at32f403a/`, `lib/at32f415/`).

### By the Numbers

| Category | Files | Lines |
|----------|------:|------:|
| New `src/stm32/` files | 7 | 1,731 |
| Modified `src/stm32/` files | 7 | +196 / −49 |
| Modified `src/` files (non-stm32) | 10 | ~250 |
| AT32F403A HAL library | ~123 | ~52,000 |
| AT32F415 HAL library | ~132 | ~51,500 |
| **Total new/modified lines** | **~279** | **~105,700** |

The HAL libraries account for 98% of the new code by volume but are largely dead weight — Klipper uses only ~10 modules from each library.

---

## The Disguise in Full

The AT32 MCUs are presented to the Klipper build system as STM32 variants:

| Actual MCU | Kconfig Entry | MCU String Alias | Clock | Role |
|-----------|---------------|-----------------|-------|------|
| AT32F403A (Cortex-M4, 240 MHz) | `MACH_AT32F403A` | `stm32f103xe` | 240 MHz | Main board |
| AT32F415RC (Cortex-M4, 144 MHz) | `MACH_AT32F415` | `stm32f105xc` | 144 MHz | Extruder heads |

**Where the disguise holds:**
- CMSIS core compatibility: Both AT32 chips are Cortex-M4 and accept the STM32 CMSIS infrastructure (interrupts, systick, NVIC)
- GPIO register layout: Compatible enough that Klipper's `gpio.c` works without modification
- Timer architecture: AT32 TMR peripherals are register-compatible with STM32 TIM at the level Klipper uses
- Memory map structure: APB1/APB2/AHB bus layout follows the STM32 pattern
- Linker script: The generic `armcm_link.ld` works with AT32 memory sizes from Kconfig
- Flash/serial bootloader: AT32 implements STM32-compatible DFU and UART boot protocols

**Where the disguise breaks down (requiring real implementation work):**
- Clock management: CRM (AT32) vs RCC (STM32) — different register names and bit positions. Full AT32 HAL CRM module needed.
- PLL configuration: AT32 PLL supports up to 60× multiplier for 240 MHz; STM32F103 max is 16× for 72 MHz. Entirely different clock setup code path required.
- USB peripheral: AT32F403A has a different USB FS register for double-buffering (skips EP_KIND write). AT32F415 uses OTG rather than the FS peripheral its STM32F105 alias implies.
- ACC (Auto Clock Calibration): AT32F403A-specific peripheral with no STM32F103 equivalent. Used to derive USB 48 MHz from internal oscillator via USB SOF locking.
- GPIO remapping: AT32 uses GMUX (GPIO Multiplexer) registers instead of STM32's AFIO remapping. Required new remap functions for UART5, CAN2, SPI4.
- CAN interrupts: AT32F403A uses `CAN1_SE_IRQn` (not `CAN1_SCE_IRQn`); CAN2 IRQ numbers differ and must be manually defined.
- SPI pin assignments: AT32F403A SPI4 uses PE11 for MOSI (STM32 uses PE12)
- Flash sector size: AT32F403A uses 2048-byte sectors (vs 1024 on STM32F103); AT32F415 uses 1024-byte sectors
- USART naming: AT32 uses `UART5` (not `USART5`), different flag names (`USART_TDBE_FLAG` vs `TXE`)

---

## Key Findings Beyond What Was Already Known

1. **The HEXT crystal is NOT eliminated.** The AT32F403A uses an external crystal (HEXT) for its 240 MHz PLL. The ACC provides a crystal-free USB clock by calibrating the internal HICK oscillator against USB SOF — but the system clock still requires a crystal. Prior characterization suggesting crystal elimination was overstated.

2. **System clock and USB clock are independent domains.** On the AT32F403A, the 240 MHz system clock (HEXT→PLL) and 48 MHz USB clock (HICK→ACC) are separate clock trees. USB disconnection does not affect step timing. This is a deliberate architectural choice in the AT32F403A.

3. **The AT32F415 is simpler.** It derives USB 48 MHz from HEXT via divider (144/3=48), has no ACC peripheral, and is overall a cleaner integration. The AT32F415 is the more promising upstream contribution candidate.

4. **Novel hardware modules are U1-specific.** `inductance_coil.c` (674 lines) and `power_loss_check.c` (685 lines) implement inductive bed probing and power loss recovery using AT32 timer capture and flash storage. These are product features, not AT32 platform support.

5. **An upstream PR already exists.** Klipper3d/klipper PR #6626 adds AT32F415/F413 support with a lighter approach (120 MHz, inline stm32f1.c modifications, no separate HAL libraries). Coordination with that effort is the pragmatic upstream path.

6. **HAL library license needs scrutiny.** Both AT32 HAL libraries carry Artery's proprietary BSP license. While it authorizes use with Artery MCUs, the GPL interaction for Klipper distribution needs legal review before upstream submission.

---

## Load-Bearing Changes

The following cannot be removed without breaking U1 hardware:

| Component | Why It's Essential |
|-----------|-------------------|
| `at32f403a.c` + clock config | Initializes 240 MHz PLL, ACC for USB, and peripheral clocks |
| `at32f415rc.c` + clock config | Initializes 144 MHz PLL and USB OTG clock |
| AT32 HAL CRM/GPIO/TMR/FLASH/USART/ACC modules | Called by the clock setup and init code |
| Kconfig CLOCK_FREQ (240/144 MHz) | Host uses this for all tick-based timing |
| Kconfig FLASH_SIZE/RAM_SIZE entries | Linker script memory map depends on these |
| `can.c` AT32F403A CAN2 conditionals | CAN bus communication with extruder heads |
| `usbotg.c` AT32F415 conditionals | USB communication on extruder heads |
| `usbfs.c` AT32F403A conditional | USB FS double-buffer fix |
| `stm32f1.c` AT32 clock dispatch | Routes to AT32-specific clock_setup() |
| `inductance_coil.c` | Inductive bed probing (core U1 feature) |
| `power_loss_check.c` | Power loss recovery (core U1 feature) |

---

## Contribution Candidates

**High viability (upstream with minor cleanup):**
- AT32F415 Kconfig entries + at32f415rc.c (coordinate with PR #6626)
- `usbotg.c` AT32F415 conditionals
- HAL library subset (CRM, GPIO, TMR, FLASH, USART — ~10 files)

**Moderate viability (needs work):**
- AT32F403A Kconfig + at32f403a.c (ACC implementation is novel but complex)
- `can.c` CAN2 support (AT32-specific IRQ definitions)
- `spi.c` SPI4 pin differences

**Not suitable for upstream:**
- `inductance_coil.c/h` — product-specific hardware
- `power_loss_check.c` — product-specific feature
- `stepper.c` modifications — power loss tracking
- Debug UART and LOG macros — not Klipper practice

---

## Open Questions

1. **ACC convergence time:** The code enables ACC calibration but does not wait for convergence. How quickly does ACC lock to USB SOF? Is there a startup window where USB timing is unstable?

2. **AT32F407RCT7 define:** The Makefile defines `-DAT32F407RCT7` for AT32F403A builds. This selects the F407 variant in the shared HAL headers. Is the actual chip an F403A or F407? The chip naming is ambiguous.

3. **Flash wear leveling:** `power_loss_check.c` uses two alternating flash sectors for stepper position storage. What is the expected write frequency and flash endurance impact?

4. **system_core_clock vs SystemCoreClock:** AT32F415 code uses lowercase `system_core_clock` (AT32 convention) while F403A uses `SystemCoreClock` (CMSIS convention). Is this intentional or a bug?

5. **Linker scripts unused:** `lib/at32f403a/linker/` contains 6 linker scripts that are never referenced by the build. Are they relevant for standalone AT32 development?

6. **CAN2 IRQ numbers:** The manual IRQ definitions (68, 69, 70, 71) in `can.c` for AT32F403A CAN2 — are these from the AT32 datasheet or determined empirically?

---

## Document Index

| Document | Description |
|----------|-------------|
| [architecture-overview.md](architecture-overview.md) | Disguise mechanism, clock topology, build system selection |
| [hal-at32f403a.md](hal-at32f403a.md) | AT32F403A HAL library: origin, modules, ACC, divergences |
| [hal-at32f415.md](hal-at32f415.md) | AT32F415 HAL library: origin, modules, USB OTG, differences |
| [stm32-new-files.md](stm32-new-files.md) | Six new src/stm32/ files: purpose, integration, contributability |
| [build-system.md](build-system.md) | Kconfig, Makefile, compiler flags, linker, flash tooling |
| [timing-protocol.md](timing-protocol.md) | Clock reporting, step timing, USB stability, protocol |
| [upstream-path.md](upstream-path.md) | Upstream contribution assessment, PR #6626 coordination |
| [python-c-crossref.md](python-c-crossref.md) | Python-C reconciliation, command mapping, workaround analysis |
| [../raw/mcu-src-stm32.diff](../raw/mcu-src-stm32.diff) | Raw diff of src/stm32/ changes |
| [../raw/mcu-lib-at32f403a.diff](../raw/mcu-lib-at32f403a.diff) | Raw diff of lib/at32f403a/ (full library) |
| [../raw/mcu-lib-at32f415.diff](../raw/mcu-lib-at32f415.diff) | Raw diff of lib/at32f415/ (full library) |
| [../raw/mcu-build.diff](../raw/mcu-build.diff) | Raw diff of Makefile, Kconfig, scripts/ |
| [../raw/mcu-name-status.diff](../raw/mcu-name-status.diff) | File manifest (name-status) for src/ and lib/ |
