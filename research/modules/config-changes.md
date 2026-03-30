# config/ — Upstream Config Changes

## Summary
The fork's `config/` directory is a near-copy of upstream Klipper's example printer configuration files, updated to the fork's base snapshot. The main differences are: replacement of `spi_bus` with explicit software SPI pin definitions across several BigTreeTech board configs (likely because the fork's underlying MCU SPI bus naming differs), removal of a TMC2130 section from one config, minor comment corrections, and the absence of two upstream-only config files. No new U1-specific configs exist in this directory; U1-specific configuration lives in `lava/` instead.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `spi_bus: spi3_PC11_PC12_PC10` in BTT Manta E3EZ TMC2130 sections | Replaced with `spi_software_miso_pin`, `spi_software_mosi_pin`, `spi_software_sclk_pin` | Fork's `mcu.py` may handle SPI bus names differently; explicit pins more portable |
| `generic-bigtreetech-skr-2.cfg` includes TMC2130 section | TMC2130 section removed | TMC2130 requires `spi_bus` that fork handles differently |
| `example-generic-caretesian.cfg` exists | Absent from fork | File missing; likely not copied when fork was created |
| `generic-mellow-fly-e3-v2.cfg` exists | Absent from fork | File added to upstream after fork diverged |
| Various BTT/Creality/Voron/kit configs have minor comment/spacing differences | Minor divergences | Snapshot in time of upstream configs |

## Additions
None — no new config files added to `config/` for U1.

## Removals / Overrides
- `example-generic-caretesian.cfg` — not present in fork (upstream-only)
- `generic-mellow-fly-e3-v2.cfg` — not present in fork (added to upstream after fork)
- TMC2130 section removed from `generic-bigtreetech-skr-2.cfg`

## Risks / Compatibility Notes
- Users copying BTT Manta E3EZ config from fork will use software SPI instead of hardware SPI — functional but slower and less timing-accurate
- The missing `example-generic-caretesian.cfg` is documentation only; no runtime impact

## Raw Diff
<details>
<summary>View Diff (generic-bigtreetech-manta-e3ez.cfg excerpt)</summary>

```diff
 #[tmc2130 stepper_x]
 #cs_pin: PB8
-#spi_bus: spi3_PC11_PC12_PC10
+#spi_software_miso_pin: PC11
+#spi_software_mosi_pin: PC12
+#spi_software_sclk_pin: PC10
 ##diag1_pin: PF3
 #run_current: 0.800
 #stealthchop_threshold: 999999
```
</details>
