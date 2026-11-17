# Experimental Snapmaker U1 phase-stepping port

Base: Snapmaker/u1-klipper `93cb12faebf6e74c51bbc5f0be66e95124af14c8`
(published firmware 2.0.0).
Phase implementation: Hannott/kalico `22fb535` (`feat/phase-stepping`).

This is a local, build-tested prototype. No printer has been flashed or
hardware-tested. Published 2.0.0 is not an exact reproduction of the installed
private MCU revision `3ebf909a`.

## Hardware path

The stock U1 config uses TMC2240 on hardware SPI: X uses SPI2/PB12 CS;
Y uses SPI4/PE12 CS. Z and extruder UART drivers are not phase-stepping targets.
The AT32F403A mainboard runs the coil updates from the scheduler and sends
them by DMA SPI (`CONFIG_PHASE_STEPPING_AT32_DMA`) at **20,000 updates/second**
(`CONFIG_PHASE_STEPPING_FREQ`; 10,000 before this default changed). At 20 kHz
an update of both motors takes under 5 us of each 50 us tick, timer irqs-off
stretches stay at about 6 us (one host serial byte is 10.85 us), and the host
stays the same distance ahead as at 10 kHz. Motor vibration measured from 20 to
160 mm/s was the same at both rates. No STM32F4 timer/DMA register code is used
on AT32.

## Port changes

- MCU phase queue, current interpolation/correction, SPI ownership and replay.
- Optional Kconfig feature restricted to AT32F403A; stock presets stay unchanged.
- Missing vendor SC7A20 Kconfig symbol restored so config regeneration retains
  the accelerometer commands already present in stock builds.
- Host phase generator, driver handover, diagnostic tests and calibration tools.
- Snapmaker's ToolHead flush callback runs after normal step generation and
  before trapq cleanup, so phase generation retains the same shaped trajectory.
- Stock host import style, CFFI definitions and precompiled helper Makefile.
- Stock motor-off's future print-time argument drains queued motion before
  leaving direct mode. Homing and FORCE_MOVE handling follow Hannott's code.
- Calibration uses a separate limits helper with stock G-code dispatch; stock
  resonance testing is untouched.

## Local build

Use the retained `u1-phase-test:20261114` Docker image (GNU Arm MCU toolchain
10.3-2021.10 plus host test dependencies), mounting this checkout at `/src`.

```
cp lava/at32f403a_phase_config .config
make olddefconfig
make -j4 CROSS_PREFIX=arm-none-eabi- OUT=out_phase/
make -C klippy/chelper -j4
python3 -m pytest -q test/test_phase_stepping.py \
  test/test_phase_stepping_glue.py test/test_phasegen.py \
  test/test_phase_calibrate.py test/test_motor_harmonics.py test/test_phase_u1.py
```

Snapmaker disables automatic helper compilation; Python changes alone are
insufficient. The host must also receive a rebuilt `c_helper.so` compatible
with its aarch64 runtime. The Debian helper built for tests is not a verified
deployment artifact. Toolhead MCU changes are unnecessary for X/Y phase control.

## Configuration and validation boundary

`config/sample-u1-phase-stepping.cfg` is an inactive example, never installed.
It leaves auto-enable false and uses the toolhead-0 accelerometer for calibration.
The U1's tool changes require selecting the physically attached toolhead's
accelerometer before any measurement. NumPy is needed for calibration, and
Matplotlib is optional for graphs.

Hardware tests must establish coil mapping, register read-back, both SPI buses,
update jitter/load, homing, motor disable, error/shutdown and tool changes.
The host's TMC2240 simulations validate software behavior, not physical driver
operation. See `Phase_Stepping.md` for upstream commands and diagnostics.
