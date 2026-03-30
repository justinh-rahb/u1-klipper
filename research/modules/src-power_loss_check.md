# src/stm32/power_loss_check.c

## Summary
A fork-exclusive MCU firmware module that detects power-supply brownout/loss events and saves the current stepper motor positions to on-chip flash so that a print can be resumed after power is restored. The module monitors a voltage-sense GPIO (PB8 on AT32F415, PB7 on AT32F403A) using a 10 kHz timer, applies duty-cycle-based debouncing to distinguish genuine power loss from noise, and when confirmed uses a dual-sector wear-levelling scheme (two 1 KB/2 KB flash sectors with alternating sequence numbers) to atomically write a `power_loss_env` record containing all registered stepper positions. On startup, `load_save_flash_info()` reads back the valid sector and makes the saved data available for query. The module also reports back to the host via `serialhdl`'s "Power loss info saved" notification which `serialhdl.py` in the klippy host intercepts.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No power-loss recovery at firmware level | Timer-driven GPIO monitoring + flash save on brownout | Snapmaker U1 requirement for print resume after power loss |
| N/A | Dual-sector wear-levelled flash storage with sequence numbers | Prevents data loss if a second power cut occurs during the flash write |
| N/A | `stepper.c` extended with `type`/`index` fields in `config_stepper` and `line` field in `queue_step` | MCU firmware can associate each step with a stepper identity and print line for recovery |

## Additions

**Key constants (per-chip, gated by `CONFIG_MACH_AT32F415` / `CONFIG_MACH_AT32F403A`):**
- `FLASH_SECTOR_SIZE` — 1024 (AT32F415) or 2048 (AT32F403A) bytes.
- `RECORD_FLASH_SECTOR_ADDR1` / `RECORD_FLASH_SECTOR_ADDR2` — two sectors at the top of flash.
- `DETECTION_GPIO` / `DETECTION_GPIO_PIN` — PB8 (AT32F415) or PB7 (AT32F403A).
- `TRM_OVER_FREQ = 10000` / `TRM_PR_DIV_VALUE` — 10 kHz sampling timer.
- `MAX_ALLOW_SAVE_STEPPER_NUM = 16` — maximum steppers in a save record.
- `ENV_VALID_FLAG = 0x12345678` — magic number for flash record validation.

**Key data structures:**
- `power_loss_check_dev` struct — per-OID state: `report_state`, `need_save`, `print_act`, `voltage_type` (Type1/Type2 auto-detected), `high_level_tick`/`low_level_tick`, `duty_cycle_threshold`, `power_loss_trigger_time`, debounce counters, `power_loss_flag`.
- `power_loss_env` struct (2-byte aligned) — `flag`, `step_info_num`, `step_info_arry[16]` (from `stepper.h`).
- `SectorInfo` struct — `addr`, `seq_num`, `valid`, `is_init` for each of the two flash sectors.

**Functions:**
- `flash_read(addr, buf, n)` — byte-by-byte flash read.
- `flash_write_nocheck(addr, buf, n)` / `flash_write(addr, buf, n)` — halfword-mode flash write with optional sector-erase-and-rewrite logic.
- `flash_sector_erase_ex(sector_address)` — unlocks flash, erases one sector, re-locks.
- `power_loss_rotate_sector()` — implements wear-levelling: writes new record to the inactive sector with incremented sequence number, then erases the old sector.
- `load_save_flash_info()` — on startup, reads both sectors, validates flags and checksums, selects the sector with the higher sequence number as the current valid record.
- `power_loss_check_task_init()` — `DECL_INIT`; sets up GPIO, detection timer, and wake task.

**MCU commands (via `DECL_COMMAND`):**
- `command_config_power_loss_check_dev` — allocates OID and configures thresholds, debounce, and report interval.
- `query_power_loss_status oid=%c` — returns current `power_loss_flag` and `voltage_type`.
- `command_update_report_interval` — updates the periodic reporting interval at runtime.
- `command_enable_power_loss` — arms/disarms power-loss detection (`print_act` flag + `print_mark` identifier).
- `query_power_loss_flash_valid oid=%c` — checks whether valid stepper data exists in flash.
- `query_power_loss_stepper_info oid=%c type=%u index=%u` — retrieves saved stepper position for a specific `(type, index)` pair (matched against `step_info_arry`).

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- Flash write operations (`flash_halfword_program`) are performed inside the timer ISR path (via `power_loss_check_task`). Flash writes on AT32 stall instruction fetch from flash for the duration; if other ISRs fire during this window they will be delayed.
- The dual-sector scheme assumes that `power_loss_rotate_sector` completes before a second power loss occurs. If power is lost during the sector write, both sectors may be invalid on next boot.
- `MAX_ALLOW_SAVE_STEPPER_NUM = 16` is a compile-time constant. If `stepper.h`'s `get_all_stepper_info()` returns more than 16 steppers, the excess are silently ignored.
- `voltage_type` auto-detection uses a continuous-recognition counter (`type_confirm_threshold`, default 3 measurements). During startup there is a window where the type is `0xFF` (uninitialized) and the duty-cycle threshold uses a default that may not match the actual hardware.
- The module sends `"Power loss info saved"` as an MCU output message when a save completes. `serialhdl.py` in the host intercepts this string to raise a coded exception — if this string format ever changes, the host-side intercept will silently stop working.
- `RECORD_FLASH_SECTOR_ADDR1/2` for AT32F403A sit at `0x080FF000`/`0x080FF800` — the very last two sectors of a 1 MB device. Any firmware build larger than ~1020 KB will overwrite these sectors.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/power_loss_check.c
@@ -0,0 +1,~700 @@
+// New file – power-loss detection and stepper state save to flash
+// AT32F415: sectors at 0x0801F800/0x0801FC00 (1 KB), GPIO PB8
+// AT32F403A: sectors at 0x080FF000/0x080FF800 (2 KB), GPIO PB7
+// DECL_COMMAND: config_power_loss_check_dev, query_power_loss_status,
+//   command_update_report_interval, command_enable_power_loss,
+//   query_power_loss_flash_valid, query_power_loss_stepper_info
+// DECL_INIT: power_loss_check_task_init
```

</details>
