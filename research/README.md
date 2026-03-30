# Snapmaker U1 Klipper Fork — Research Index

## Analyses

### MCU C Source Analysis (AT32)

**Directory:** [`/research/mcu/`](mcu/)

Documents the AT32F403A/AT32F415RC MCU implementation that is disguised as STM32 variants within the Klipper build system. The AT32F403A (240 MHz, main board) masquerades as `stm32f103xe`; the AT32F415RC (144 MHz, extruder heads) masquerades as `stm32f105xc`.

**Scope:**
- 7 new files in `src/stm32/` (1,731 lines): clock setup, ACC calibration, inductance coil probing, power loss recovery
- 7 modified files in `src/stm32/`: CAN, SPI, serial, USB, and clock init conditionals for AT32
- 2 full HAL libraries (`lib/at32f403a/`, `lib/at32f415/`): ~103,500 lines from official Artery SDK
- Build system changes: Kconfig entries, Makefile source lists, compiler flags
- Python-C cross-reference: new MCU commands for U1 hardware features

**Key documents:**
- [Summary Report](mcu/README.md)
- [Architecture Overview](mcu/architecture-overview.md)
- [Upstream Contribution Path](mcu/upstream-path.md)

**Raw diffs:** [`/research/raw/mcu-*.diff`](raw/)

---

## Raw Diffs

All raw diffs are stored in [`/research/raw/`](raw/) with descriptive prefixes:

| File | Scope | Lines |
|------|-------|------:|
| `mcu-src-stm32.diff` | `src/stm32/` changes | 2,309 |
| `mcu-lib-at32f403a.diff` | `lib/at32f403a/` (full library) | 51,919 |
| `mcu-lib-at32f415.diff` | `lib/at32f415/` (full library) | 54,668 |
| `mcu-build.diff` | Makefile, Kconfig, scripts/ | 130 |
| `mcu-name-status.diff` | File manifest for `src/` and `lib/` | 286 |
