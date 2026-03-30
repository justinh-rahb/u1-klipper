# msgproto.py

See [klippy-minor-core-changes.md](klippy-minor-core-changes.md#msgprotospy) for the full analysis of this file.

**Summary of changes:**
- `error` now inherits from `CodedException` instead of `Exception`.
- `MessageParser.create_dummy_response()` removed.
- Empty argument encoding returns `""` instead of `[]`.
