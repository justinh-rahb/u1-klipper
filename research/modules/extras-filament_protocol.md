# filament_protocol.py

## Summary
`filament_protocol.py` is a pure-logic library module (no Klipper extra entry point) that defines the binary layout of Snapmaker's proprietary MIFARE M1 NFC filament tag and parses raw card bytes into a structured `FILAMENT_INFO_STRUCT` dictionary. The 1 KB card is divided into sections covering vendor/manufacturer strings, material type/sub-type codes, up to 5 RGB colours, physical spool data (diameter, weight, length), drying parameters, hotend temperature range, bed temperature, and manufacturing date. The parser also verifies an RSA-PKCS#1v15 / SHA-256 digital signature using one of 10 embedded public keys (key version 0–9) before accepting the data. If the signature check fails, `FILAMENT_PROTO_SIGN_CHECK_ERR` is returned and the info is treated as unofficial (`OFFICIAL = False`).

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: proprietary binary NFC card parser with RSA signature verification and 10 rotating public keys | Snapmaker implements filament authentication to ensure only genuine/authorised filament data is trusted for auto-parameter selection |

## Additions

### Data Structures
- **`FILAMENT_INFO_STRUCT`** — Template dict with 30 fields: `VERSION`, `VENDOR`, `MANUFACTURER`, `MAIN_TYPE`, `SUB_TYPE`, `TRAY`, `ALPHA`, `COLOR_NUMS`, `ARGB_COLOR`, `RGB_1`–`RGB_5`, `DIAMETER`, `WEIGHT`, `LENGTH`, `DRYING_TEMP`, `DRYING_TIME`, `HOTEND_MAX_TEMP`, `HOTEND_MIN_TEMP`, `BED_TYPE`, `BED_TEMP`, `FIRST_LAYER_TEMP`, `OTHER_LAYER_TEMP`, `SKU`, `MF_DATE`, `RSA_KEY_VERSION`, `OFFICIAL`, `CARD_UID`.

### Type Mappings
- `FILAMENT_PROTO_MAIN_TYPE_MAPPING` — Numeric codes for PLA, PETG, ABS, TPU, PVA.
- `FILAMENT_PROTO_SUB_TYPE_MAPPING` — Numeric codes for Basic, Matte, SnapSpeed, Silk, Support, HF, 95A, 95A HF.

### RSA Public Keys
- `FILAMENT_PROTO_RSA_PUBLIC_KEY_0` through `FILAMENT_PROTO_RSA_PUBLIC_KEY_9` — 10 PEM-encoded RSA-2048 public keys (2048-bit).

### Functions
- `get_key_by_value(dict_obj, value)` — Reverse lookup helper.
- `verify_signature_pkcs1(public_key, data, signature)` — Verifies RSA-PKCS#1v15 / SHA-256 signature using `cryptography` library.
- `m1_proto_data_parse(data_buf)` — Main entry point. Accepts a 1024-byte list. Returns `(error_code, info_dict)`. Parses all fields from defined byte offsets and validates the signature over bytes 0–639.

### Error Codes
- `FILAMENT_PROTO_OK = 0`
- `FILAMENT_PROTO_ERR = -1`
- `FILAMENT_PROTO_PARAMETER_ERR = -2`
- `FILAMENT_PROTO_RSA_KEY_VER_ERR = -3`
- `FILAMENT_PROTO_SIGN_CHECK_ERR = -4`

### Card Layout Constants
All byte positions (`M1_PROTO_*_POS`) and lengths (`M1_PROTO_*_LEN`) for every field in the 1 KB M1 card memory are defined as named constants (e.g., `M1_PROTO_VENDOR_POS = 16`, `M1_PROTO_VENDOR_LEN = 16`).

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `cryptography` Python package (`cryptography.hazmat.primitives`), which is not a standard Klipper dependency.
- The 10 hard-coded RSA public keys are Snapmaker IP; rotating keys beyond version 9 would require a fork update.
- Cards with RSA key version > 9 are rejected with `FILAMENT_PROTO_RSA_KEY_VER_ERR`, silently treating them as unofficial filament.
- The digital signature covers only bytes 0–639 of the 1 KB card; the remaining 384 bytes (signature sectors 10–15) are not validated for integrity beyond being extracted as the signature itself.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import copy
+from cryptography.hazmat.primitives import hashes, serialization
+from cryptography.hazmat.primitives.asymmetric import padding
+from cryptography.hazmat.backends import default_backend
+from cryptography.exceptions import InvalidSignature
+
+FILAMENT_INFO_STRUCT = {
+    'VERSION': 0, 'VENDOR': 'NONE', 'MANUFACTURER': 'NONE',
+    'MAIN_TYPE': 'NONE', 'SUB_TYPE': 'NONE', ...
+    'OFFICIAL': False, 'CARD_UID': 0,
+}
+
+FILAMENT_PROTO_RSA_PUBLIC_KEY_0 = b"""-----BEGIN RSA PUBLIC KEY-----
+MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA8oEF7YuKO86...
+-----END RSA PUBLIC KEY-----"""
+# ... keys 1-9 ...
+
+def m1_proto_data_parse(data_buf):
+    # validate length, select RSA key, verify signature
+    # parse all fields from byte offsets
+    # return (FILAMENT_PROTO_OK, info) or error code
+    ...
```
</details>
