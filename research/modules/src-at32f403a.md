# src/stm32/at32f403a.c

## Summary
A fork-exclusive C source file providing board-level initialisation for the **Artery AT32F403A** microcontroller (an STM32F4-compatible 32-bit ARM Cortex-M4 MCU from Artery Technology). It sets up the system clock, configures the USB 48 MHz clock using either the internal RC oscillator (HICK) with ACC auto-calibration or the external crystal (HEXT) depending on the selected PLL multiplier, provides a debug UART on USART3 / PB10, and optionally configures GPIO remaps for UART5, CAN2, and SPI4. The file bridges the AT32 vendor SDK (`at32f403a_407.h`) into Klipper's firmware HAL layer (`sched.h`, `command.h`, `armcm_boot.h`).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| No AT32F403A support | `at32f403a_clock_setup()` called by `DECL_INIT` equivalent to set system clock and USB clock | Snapmaker U1 main SoC MCU uses AT32F403A |
| N/A | Debug UART on USART3/PB10 with optional `RESERVE_PINS_debug_uart_tx_pin` constant | Factory/debug logging on embedded hardware |

## Additions

**Functions:**
- `uart_debug_print_init(uint32_t baudrate)` — configures USART3/PB10 as a TX-only UART for debug output; enables clocks via `crm_periph_clock_enable`.
- `at32f403a_log(char* log)` — writes a NUL-terminated string byte-by-byte to USART3; used as a low-level print function.
- `PUTCHAR_PROTOTYPE` (`__io_putchar` or `fputc`) — retargets C `printf` to USART3.
- `usb_clock48m_select(usb_clk48_s clk_s)` — selects the USB 48 MHz source:
  - `USB_CLK_HICK` path: enables `CRM_ACC_PERIPH_CLOCK`, writes ACC calibration constants (`c1=7980`, `c2=8000`, `c3=8020`), enables HICK auto-trim.
  - `USB_CLK_HEXT` path: sets `CRM_USB_DIV_*` based on `SystemCoreClock` (48/72/96/120/144/168/192 MHz).
- `mcu_uart_gpio_remap()` — enables `UART5_GMUX_0001` remap (conditional on `CONFIG_STM32_SERIAL_AT_USART5_PB8_PB9`).
- `mcu_can2_gpio_remap()` — enables `CAN2_GMUX_0001`.
- `mcu_spi4_gpio_remap()` — enables `SPI4_GMUX_0001`.
- `at32f403a_clock_setup()` — calls `system_clock_config()`, `usb_clock48m_select(USB_CLK_HICK)`, and enables the USB peripheral clock.

**Config constants:**
- `RESERVE_PINS_debug_uart_tx_pin = "PB10"` (if `CONFIG_AT32_ENABLE_DEBUG_USART`).

## Removals / Overrides
- None (new file with no upstream counterpart).

## Risks / Compatibility Notes
- `usb_clock48m_select(USB_CLK_HICK)` uses ACC auto-calibration with fixed C1/C2/C3 constants (7980/8000/8020). These are tuned for an 8 MHz HICK target; if the AT32F403A variant in the U1 has a different trim range, USB enumeration may fail.
- `at32f403a_log` blocks in a tight loop waiting for `USART_TDBE_FLAG`; calling this during time-critical ISR code will introduce latency.
- `PUTCHAR_PROTOTYPE` targets GCC `__io_putchar`; clang uses `fputc`. The `#if` guards handle this, but mixing toolchains requires care.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
--- /dev/null
+++ b/src/stm32/at32f403a.c
@@ -0,0 +1,~160 @@
+// New file – AT32F403A board-level init
+void uart_debug_print_init(uint32_t baudrate);
+void at32f403a_log(char* log);
+static void usb_clock48m_select(usb_clk48_s clk_s);
+void mcu_uart_gpio_remap(void);
+void mcu_can2_gpio_remap(void);
+void mcu_spi4_gpio_remap(void);
+void at32f403a_clock_setup(void);  // called by DECL_INIT chain
```

</details>
