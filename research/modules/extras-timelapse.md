# timelapse.py

## Summary
`timelapse.py` implements `TimeLapse`, a Klipper extra that controls an on-board camera to capture timelapse frames during printing. It communicates with a camera service via JSON-RPC over MQTT (`mqtt.py` + `jsonrpc.py`), calling the `camera.start_timelapse`, `camera.stop_timelapse`, and `camera.take_a_photo` methods. Timelapse activation is gated by the `print_task_config` flag `time_lapse_camera`. A minimum 1-second interval between frame requests prevents flooding. On `TIMELAPSE_START` the module also turns on the cavity LED (`SET_LED LED=cavity_led WHITE=1`). Frame capture requests are fire-and-forget (async JSON-RPC), while start/stop calls are synchronous with a 5-second timeout.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: timelapse control via MQTT JSON-RPC to on-board camera service, gated by print_task_config | U1 has an optional cavity camera; this module provides a Klipper-native way to trigger it from G-code macros |

## Additions

### Classes
- **`TimeLapse`** — Klipper extra loaded as `[timelapse]`.

### G-code Commands
- **`TIMELAPSE_START [TYPE=new|continue] [FRAME_RATE=<int>]`** — Start a timelapse session. Sends `camera.start_timelapse` JSON-RPC call synchronously. Raises a structured error (ID 524) on failure, which causes the print to pause.
- **`TIMELAPSE_STOP`** — Stop timelapse; sends `camera.stop_timelapse` synchronously.
- **`TIMELAPSE_TAKE_FRAME [DEBUG=0|1]`** — Trigger a single photo capture (async). In debug mode (`DEBUG=1`) saves the image to `/userdata/gcodes/pictures/pic_<timestamp>.jpg`.
- **`TIMELAPSE_IGNORE IGNORE=<0|1>`** — Suppress all frame captures for the current print session (useful during non-print phases).

### Config Options
- `frame_rate` (int, default 24) — Default frames-per-second requested when starting timelapse.

### MQTT Topics
- Request: `camera/request`
- Response: `camera/response`

### Event Handlers
- `print_stats:start` — Clears the `timeslapse_ignore` flag.
- `print_stats:stop` — Clears the `timeslapse_ignore` flag.
- `klippy:ready` — Looks up `mqtt` and `print_task_config` objects; creates the `JSONRPCClient`.

### Key Logic
- `REQUEST_INTERVAL_MIN = 1` s — Minimum time between consecutive frame-capture requests.
- `REQUEST_TIMEOUT = 5` s — Synchronous JSON-RPC timeout for start/stop.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `mqtt` and `print_task_config` extras to be present; if either is absent, G-code commands raise errors.
- `TIMELAPSE_START` failure path uses a structured error dict (`id=524`) inside `gcmd.error()`; this is a fork-specific extension of Klipper's `GCodeException`.
- `send_request_with_response` blocks the G-code thread for up to 5 seconds; during that time no other G-code can execute.
- Debug image path is hardcoded to `/userdata/gcodes/pictures` — Snapmaker-specific filesystem layout.
- The `TIMELAPSE_TAKE_FRAME` command has a `filepath` hardcoded to `/tmp/tmp.jpg` for non-debug mode — this is a temporary location that will be overwritten by every frame capture.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+# timelapse manager for klippy
+# Copyright (C) 2025-2030  Scott Huang <shili.huang@snapmaker.com>
+import logging, time, os
+from .jsonrpc import *
+
+REQUEST_TOPIC  = "camera/request"
+RESPONSE_TOPIC = "camera/response"
+REQUEST_INTERVAL_MIN = 1
+REQUEST_TIMEOUT = 5
+
+class TimeLapse:
+    def __init__(self, config):
+        ...
+        self.gcode.register_command('TIMELAPSE_START', ...)
+        self.gcode.register_command('TIMELAPSE_STOP', ...)
+        self.gcode.register_command('TIMELAPSE_TAKE_FRAME', ...)
+        self.gcode.register_command('TIMELAPSE_IGNORE', ...)
+
+    def cmd_TIMELAPSE_START(self, gcmd):
+        # check print_task_config['time_lapse_camera']
+        # gcode.run_script_from_command("SET_LED LED=cavity_led WHITE=1")
+        # mqtt_jsonrpc.send_request_with_response("camera.start_timelapse", ...)
+        ...
+
+def load_config(config):
+    return TimeLapse(config)
```
</details>
