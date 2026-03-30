# fm175xx_reader.py

## Summary
`fm175xx_reader.py` implements `FM175XXReader`, a Klipper extra that drives one or more FM175XX SPI NFC/RFID reader ICs (connected via `/dev/spidev*`) to read MIFARE M1 1K NFC tags embedded in Snapmaker filament spools. The module runs a dedicated background thread that continuously scans up to 4 channels, dispatching card-info read or clear requests from a queue. For each successful read it verifies an HMAC-SHA256 message authentication code derived from the card UID to guard against replay attacks before passing the raw 1 KB card data to registered callbacks. It also provides a self-test mode for production validation.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: multi-channel SPI NFC reader driver with HMAC authentication, async request queuing, and callbacks for the filament detection system | U1 hardware has FM175XX NFC chips in the feeder unit to read per-spool RFID tags; no upstream equivalent exists |

## Additions

### Classes
- **`FM175XXReader`** — Klipper extra loaded as `[fm175xx_reader]`.

### Key Config Options
- `spi_bus_ch*` — SPI bus device path for each channel (e.g. `/dev/spidev0.0`).
- `spi_cs_ch*_pin` — Chip-select GPIO pin for each channel.
- `hmac_key` — HMAC-SHA256 key used to authenticate card UID.
- `channel_nums` (int, default 4) — Number of reader channels.

### Public API
- `register_cb_2_card_info_deal(cb)` — Register a callback `cb(channel, operation, result, card_type, card_data)` invoked after each read or clear.
- `request_read_card_info(channel)` — Enqueue a read request for `channel`.
- `request_clear_card_info(channel)` — Enqueue a clear (info-reset) request for `channel`.
- `self_test(channel, times)` — Run `times` consecutive read attempts on `channel`.
- `self_test_result()` → `(finished, test_times, success_times)` — Poll self-test progress.

### Constants
- `FM175XX_CHANNEL_NUMS = 4`
- `FM175XX_OK = 0`, `FM175XX_ERR = -1`, etc.
- `FM175XX_MIFARE_CARD_TYPE_M1` — Card type identifier for MIFARE 1K.
- `FM175XX_CARD_INFO_READ` / `FM175XX_CARD_INFO_CLEAR` — Operation codes passed to callbacks.

### Background Thread
A dedicated Python thread (started in `__init__`) processes the request queue by calling `spidev` directly to communicate with the FM175XX chip, implementing the MIFARE 1K read protocol (REQA, anticollision, select, authentication, block reads).

### HMAC Authentication
After reading the card UID, the module computes `HMAC-SHA256(hmac_key, card_uid)` and checks it against a stored authenticator on the card before accepting the data — preventing cloning or replay attacks.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `spidev` Python package and appropriate kernel SPI device nodes (`/dev/spidev*`) — hardware-specific.
- The background thread uses `threading` directly, which runs outside the Klipper reactor; all callbacks are dispatched back to the reactor via `reactor.register_async_callback`.
- If a channel's SPI device is absent or fails to open, the module may log errors but continues operating the remaining channels.
- HMAC key is stored in Klipper config (plaintext); this provides authentication but not confidentiality.
- The self-test mode (`self_test`) spins in the background thread; polling via `self_test_result()` from a G-code handler with `reactor.pause()` can block the print thread.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, time, threading, copy
+import spidev
+import hmac, hashlib
+
+FM175XX_CHANNEL_NUMS = 4
+FM175XX_OK    = 0
+FM175XX_ERR   = -1
+FM175XX_CARD_INFO_READ  = 0
+FM175XX_CARD_INFO_CLEAR = 1
+FM175XX_MIFARE_CARD_TYPE_M1 = 1
+
+class FM175XXReader:
+    def __init__(self, config):
+        # open spidev devices for each channel
+        # start background reader thread
+        ...
+    def register_cb_2_card_info_deal(self, cb): ...
+    def request_read_card_info(self, channel): ...
+    def request_clear_card_info(self, channel): ...
+    def self_test(self, channel, times): ...
+    def self_test_result(self): ...
+
+def load_config(config):
+    return FM175XXReader(config)
```
</details>
