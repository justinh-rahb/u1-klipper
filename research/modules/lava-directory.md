# lava/ — Snapmaker U1 Production Configuration Directory

## Summary
The `lava/` directory is entirely fork-exclusive and contains the complete production configuration for the Snapmaker U1 multi-material 3D printer. It includes the main `printer.cfg` (the actual running configuration used on U1 devices), the Fluidd UI configuration (`fluidd.cfg`), an XYZ offset calibration workflow script (`xyz_offset_calibration.cfg`), and three pre-built Klipper firmware `.config` files for the U1's three microcontrollers. None of these files exist in upstream Klipper; they are the definitive reference for how all fork-exclusive modules are wired together on real hardware.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No `lava/` directory | Complete production printer config | U1 ships with this config pre-installed |
| No AT32 MCU firmware configs | `at32f403a_config`, `at32f415_config`, `klippy_mcu_config` | AT32 MCUs are U1-specific hardware |

---

## `lava/printer.cfg`

**96 configuration sections** covering the full U1 hardware. Key structure:

### MCU Configuration
| Section | MCU | Connection | Purpose |
|---------|-----|-----------|---------|
| `[mcu]` | AT32F403A | `/dev/ttyS6`, 460800 baud | Main motion controller board |
| `[mcu host]` | Linux (AArch64 SoC) | `/tmp/klipper_host_mcu` | Host MCU for GPIO/SPI access |
| `[mcu e0]`–`[mcu e3]` | AT32F415RC × 4 | USB by-path (`xhci-hcd.0.auto`) | Per-extruder MCUs (T0–T3) |

### Motion System
- `kinematics: corexy` with `max_velocity: 500`, `max_accel: 20000`, `max_z_velocity: 30`
- X: `position_max: 271`, sensorless homing via `tmc2240_stepper_x:virtual_endstop`
- Y: `position_max: 335`, sensorless homing via `tmc2240_stepper_y:virtual_endstop`
- Z: `position_max: 275`, sensorless homing via `tmc2209_stepper_z:virtual_endstop`
- All axes use `homing_precise_corexy` for improved sensorless accuracy

### Extruder System (× 4, T0–T3)
Each extruder (`extruder`, `extruder1`, `extruder2`, `extruder3`) has:
- `[tmc2209 extruderN]` — stepper driver on `[mcu eN]`
- `[park_detector extruderN]` — detects if tool is parked
- `[fan_generic eN_fan]`, `[heater_fan eN_nozzle_fan]` — cooling fans
- `[output_pin eN_heat_sw]` — heater power switch
- `[filament_motion_sensor eN_filament]` — motion-based runout
- `[filament_entangle_detect eN_filament]` — tangle detection
- `[inductance_coil extruderN]` — inductive Z probe
- `[lis2dw eN_lis2dw]` — accelerometer for resonance testing
- `[power_loss_check eN]` — per-extruder power loss state flash

### Connectivity & Peripherals
- `[mqtt]` — Snapmaker app communication
- `[timelapse]` with `frame_rate: 24`
- `[fm175xx_reader]` — NFC reader on SoC SPI bus 2 with 4 channels (2 on SoC SPI, 2 on extra SPI)
- `[filament_detect]` — filament presence across all slots
- `[flow_calibrator]` — extrusion multiplier calibration
- `[resonance_tester]`/`[input_shaper]` — vibration compensation
- `[adc_current_sensor I_AD]` — current monitoring
- `[purifier]` — air filtration control

### Bed & Enclosure
- `[heater_bed]`, `[verify_heater heater_bed]`
- `[temperature_sensor cavity]`, `[fan_generic cavity_fan]`, `[led cavity_led]`
- `[bed_mesh]`, `[auto_screws_tilt_adjust]`

### Power Loss Recovery
- `[power_loss_check]` — main board PLR
- `[gcode_macro _PL_SAVE_VARIABLE]` — PLR state G-code variable block

### G-code Macros
| Macro | Purpose |
|-------|---------|
| `AUTO_BED_MESH_CALIBRATE` | Automated bed levelling sequence |
| `SHAKE_Z` | Z-axis vibration for self-check |
| `SENSORLESS_HOME_X/Y/Z` | Sensorless homing sequences |
| `_HOMING_PRECISE_COREXY_ADVANCED` | Advanced homing with stall detection |
| `_CLIENT_VARIABLE` | Fluidd/KlipperScreen variable overrides |
| `_FILAMENT_FEED_VARIABLE` | Filament feed system parameters |

### Filament Feed System
- `[filament_feed left]` / `[filament_feed right]` — filament loader motors
- `[filament_parameters]` — per-material configuration
- `[defect_detection]` — print defect detection integration

---

## `lava/fluidd.cfg`

Standard Fluidd UI client macro definitions (pause/resume/cancel/start G-codes). This is the community-standard `fluidd.cfg` included by the U1 config. Identical to the upstream Fluidd community file — no U1-specific changes.

---

## `lava/xyz_offset_calibration.cfg`

**Extruder nozzle XYZ offset calibration workflow.** Contains a sequence of G-code macros for semi-automated calibration of extruder-to-extruder offsets:

- `_EXTRUDER_OFFSET_ACTION_PRESTART` — initialise calibration session (heat, home, clean)
- `_EXTRUDER_OFFSET_ACTION_PREHEAT` — heat nozzles for calibration
- `_EXTRUDER_OFFSET_ACTION_PREHOMING` — home axes before calibration
- `_EXTRUDER_OFFSET_ACTION_AUTO_CLEAN` / `_EXTRUDER_OFFSET_ACTION_MANUAL_CLEAN` — nozzle wipe
- `_EXTRUDER_OFFSET_ACTION_HEAT` / `_EXTRUDER_OFFSET_ACTION_WAIT_COOL` — thermal management
- `_EXTRUDER_OFFSET_ACTION_PROBE_CALIBRATE` — measure nozzle height offset for T0–T3
- `_EXTRUDER_OFFSET_ACTION_DETECT_PLATE` — detect build plate presence
- `_EXTRUDER_OFFSET_ACTION_EXIT` — finalise and save offsets

All macros accept `TOOL_ID=T0|T1|T2|T3` parameter. The sequence is designed for the 4-extruder U1 but each step can be called individually.

---

## `lava/at32f403a_config`

Klipper `.config` file for the **AT32F403A main board MCU**. Key settings:

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CONFIG_MACH_STM32=y` | STM32-compatible build | AT32F403A uses STM32-compatible HAL |
| `CONFIG_MCU="stm32f103xe"` | Identifies as STM32F103 | AT32F403A is pin/peripheral compatible |
| `CONFIG_CLOCK_FREQ=240000000` | 240 MHz | AT32F403A maximum clock (vs 72 MHz for real STM32F103) |
| `CONFIG_SERIAL=y` | UART communication | Connects to host at 460800 baud |
| `CONFIG_FLASH_SIZE=0x40000` | 256 KB flash | AT32F403A flash size |
| `CONFIG_RAM_SIZE=0x18000` | 96 KB RAM | AT32F403A RAM size |

---

## `lava/at32f415_config`

Klipper `.config` file for the **AT32F415RC extruder MCUs** (one per extruder head).

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CONFIG_MACH_STM32=y` | STM32-compatible | AT32F415 uses STM32-compatible HAL |
| `CONFIG_MCU="stm32f105xc"` | Identifies as STM32F105 | AT32F415 is peripheral-compatible |
| `CONFIG_CLOCK_FREQ=144000000` | 144 MHz | AT32F415 maximum clock |
| `CONFIG_USBSERIAL=y` | USB CDC serial | Connects to host via USB |
| `CONFIG_FLASH_SIZE=0x40000` | 256 KB flash | AT32F415RC flash |
| `CONFIG_RAM_SIZE=0x8000` | 32 KB RAM | AT32F415RC RAM |

---

## `lava/klippy_mcu_config`

Klipper `.config` file for the **Linux host MCU** (runs on the U1 SoC itself).

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CONFIG_MACH_LINUX=y` | Linux process MCU | Runs as user-space process |
| `CONFIG_CLOCK_FREQ=50000000` | 50 MHz (nominal) | Linux MCU soft clock |
| `CONFIG_WANT_GPIO_BITBANGING=y` | Software GPIO | Required for SPI NFC reader |
| `CONFIG_USB_VENDOR_ID=0x1d50` | OpenMoko VID | Standard Klipper USB identity |

---

## Risks / Compatibility Notes
- The `lava/printer.cfg` references fork-exclusive config sections (`[mqtt]`, `[timelapse]`, `[fm175xx_reader]`, `[filament_detect]`, `[inductance_coil *]`, `[park_detector *]`, `[power_loss_check *]`, `[homing_precise_corexy]`, etc.) — **this config cannot run on upstream Klipper** without removing all U1-specific sections
- The AT32F403A is identified as `stm32f103xe` in the config — if Klipper upstream adds stricter MCU type validation, this alias may break
- The `CONFIG_CLOCK_FREQ=240000000` for AT32F403A is 3× higher than a real STM32F103; timing-sensitive code must account for this
- NFC reader (fm175xx_reader) requires SoC SPI device node access (`/dev/spidev2.0`, `/dev/spidev2.1`) — Linux kernel must have SPI enabled in device tree
- USB by-path addresses for extruder MCUs (`platform-xhci-hcd.0.auto-usb-0:1.N:1.0`) are hardware-specific and will differ on any other system
