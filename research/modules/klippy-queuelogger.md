# queuelogger.py

See [klippy-minor-core-changes.md](klippy-minor-core-changes.md#queueloggerpy) for the full analysis of this file.

**Summary of changes:**
- Log rotation changed from time-based (`TimedRotatingFileHandler`, midnight, 5 backups) to size-based (`RotatingFileHandler`, 10 MiB, 15 backups).
- `MillisecondFormatter` added for `HH:MM:SS.mmm` timestamps.
- `setup_bg_logging` gains a `maxBytes` parameter.
