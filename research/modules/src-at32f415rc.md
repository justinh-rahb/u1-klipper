# src/stm32/at32f415rc.c

## Summary
A fork-exclusive C source file providing board-level initialisation for the **Artery AT32F415RC** microcontroller (ARM Cortex-M4, 256 KB flash, USB OTG FS). This is the chip used on Snapmaker U1 extruder MCU boards (E0–E3). It configures the system clock via `system_clock_config()`, sets up USB OTG with the external crystal as the 48 MHz source, and provides a debug UART on USART3/PB10 (same pin as the AT32F403A). The file is structurally simpler than `at32f403a.c` because the AT32F415 uses a single USB clock divider path and has a built-in USB OTG peripheral (no external CAN bus clock mux needed).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No AT32F415 support | Full clock and USB OTG init for AT32F415RC | Snapmaker U1 extruder MCU is AT32F415RC |
| N/A | Debug UART on USART3/PB10 | Factory/debug output on extruder boards |

## Additions

**Functions:**
- `uart_debug_print_init(uint32_t baudrate)` — configures USART3/PB10 as debug TX UART; uses `crm_periph_clock_enable` for CRM_USART3 and CRM_GPIOB clocks.
- `at32f415_log(char* log)` — byte-by-byte string write to USART3 (mirrors `at32f403a_log`).
- `usb_clock48m_select(usb_clk48_s clk_s)` — **ignores `clk_s` entirely**; the function body is a single `switch(system_core_clock)` block and the `clk_s` parameter is never referenced. Regardless of whether `USB_CLK_HICK` or `USB_CLK_HEXT` is passed, the function always executes the same divider-select path (48/72/96/120/144 MHz → `CRM_USB_DIV_1` through `CRM_USB_DIV_3`). The parameter exists for API compatibility with `at32f403a.c`'s version, which does branch on `clk_s`.
- `at32f415rc_clock_setup()` — calls `system_clock_config()` only; called directly from `src/stm32/stm32f1.c:279` inside a `#if CONFIG_MACH_AT32F415` block, not via DECL_INIT.
- `at32f415rc_usbotg_clock_config()` — enables `OTG_CLOCK` (`crm_periph_clock_enable`) and calls `usb_clock48m_select(USB_CLK_HEXT)`.

**Config constants:**
- `RESERVE_PINS_debug_uart_tx_pin = "PB10"` (if `CONFIG_AT32_ENABLE_DEBUG_USART`).

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `usb_clock48m_select` uses `USB_CLK_HEXT` in `at32f415rc_usbotg_clock_config()` — requires a stable external crystal. If the crystal is absent or out of tolerance, USB enumeration will fail silently.
- Unlike the AT32F403A file, there is no ACC auto-calibration fallback; the AT32F415 does not support ACC for HEXT.
- The `power_loss_check.c` sectors (`0x0801F800`, `0x0801FC00`) sit at the 128 KB boundary, halfway through the 256 KB flash. Any build exceeding 128 KB will overwrite the power-loss data sectors (`src/stm32/Kconfig:238`: `FLASH_SIZE = 0x40000 = 256 KB`).

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/at32f415rc.c
@@ -0,0 +1,~100 @@
+// New file – AT32F415RC board-level init
+void uart_debug_print_init(uint32_t baudrate);
+void at32f415_log(char* log);
+void usb_clock48m_select(usb_clk48_s clk_s);
+void at32f415rc_clock_setup(void);
+void at32f415rc_usbotg_clock_config(void);
```

</details>
