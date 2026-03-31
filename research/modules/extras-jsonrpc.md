# jsonrpc.py

## Summary
`jsonrpc.py` provides a JSON-RPC 2.0 client library used by the `timelapse` and `defect_detection` modules to communicate with on-board camera and vision services over MQTT. It defines an abstract `TransportInterface`, a concrete `MQTTTransport` implementation (backed by the fork's `mqtt.py` extra), and a `JSONRPCClient` that manages pending requests, generates monotonically-increasing IDs via a thread-safe `GlobalIdGenerator`, and supports both fire-and-forget async requests (`send_request`) and blocking synchronous requests (`send_request_with_response`). The synchronous path polls the reactor with 50 ms pauses while waiting for the response topic message.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: JSON-RPC 2.0 client over MQTT transport with async and synchronous request modes | On-board camera services expose a JSON-RPC API over MQTT; this adapter makes calling them from Klipper G-code handlers straightforward |

## Additions

### Classes
- **`GlobalIdGenerator`** — Thread-safe sequential integer ID generator (range 1 to 0x7FFFFFFF, wrapping).
- **`TransportInterface`** (ABC) — Abstract base class with `connect`, `disconnect`, `is_connected`, `send`, and `set_message_handler`.
- **`MQTTTransport`** (`TransportInterface`) — Subscribes to a response topic and publishes to a request topic using the `MQTTClient` extra. Tracks `_is_connected` state separately from the underlying MQTT connection.
- **`JSONRPCClient`** — Core JSON-RPC 2.0 client; not a Klipper extra itself (instantiated by callers).

### Error Codes
- `JSONRPC_ERR_SERVER_ERROR = -32000` (JSON-RPC standard)
- `JSONRPC_ERR_INVALID_REQUEST = -32600`
- `JSONRPC_ERR_METHOD_NOT_FOUND = -32601`
- `JSONRPC_ERR_INVALID_PARAMS = -32602`
- `JSONRPC_ERR_PARSE_ERROR = -32700`
- `JSONRPC_ERR_TRANSPORT_ERROR = -111` (fork-specific)
- `JSONRPC_ERR_TIMEOUT = -112` (fork-specific)
- `JSONRPC_ERR_NOT_CONNECTED = -113` (fork-specific)

### Transport Constant
- `JSONRPC_TRANSPORT_MQTT = "mqtt"` — Only supported transport type.

### Key Methods on `JSONRPCClient`
- `connect()` — Connects the underlying transport (subscribes the response topic).
- `disconnect()` — Clears pending requests and disconnects transport.
- `send_request(method, params={}, callback=None)` — Fire-and-forget; stores the callback in `pending_requests` keyed by request ID. Response dispatched by `_handle_response`.
- `send_request_with_response(method, params={}, timeout=None)` → dict — Blocks the reactor (via `reactor.pause`) until the matching response arrives or times out. Returns the full JSON-RPC response dict including `result` or `error`.

### Limits
- `JSONRPC_PENDING_REQUEST_SIZE = 100` — Maximum number of outstanding async requests; oldest is evicted on overflow.
- Default `request_timeout = 30` s.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- `send_request_with_response` calls `reactor.pause()` in a loop — this is acceptable in a G-code command handler but must not be called from a reactor timer callback or it will deadlock the reactor.
- Only one synchronous request can be in-flight at a time (`sync_request_id` single slot). Concurrent calls serialize via a `while self.sync_request_id is not None` spin-wait.
- Response matching is purely by ID; if the remote service reuses IDs or sends out-of-order responses, the wrong callback may be invoked.
- The module imports `*` from itself (`from .jsonrpc import *`) in callers; all module-level names are therefore potentially exported into the caller's namespace.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import json, logging, copy
+from abc import ABC, abstractmethod
+from typing import Callable, Dict
+import threading
+
+JSONRPC_ERR_SERVER_ERROR    = -32000
+JSONRPC_ERR_TIMEOUT         = -112
+JSONRPC_ERR_NOT_CONNECTED   = -113
+JSONRPC_PENDING_REQUEST_SIZE = 100
+JSONRPC_TRANSPORT_MQTT = "mqtt"
+
+class GlobalIdGenerator: ...
+class TransportInterface(ABC): ...
+class JSONRPCClient:
+    def send_request(self, method, params={}, callback=None): ...
+    def send_request_with_response(self, method, params={}, timeout=None): ...
+    def _handle_message(self, message: str): ...
+    def _handle_response(self, response: Dict): ...
+class MQTTTransport(TransportInterface):
+    def connect(self): ...   # subscribe response_topic
+    def send(self, data): ...  # publish request_topic
```
</details>
