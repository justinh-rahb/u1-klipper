# mqtt.py

## Summary
`mqtt.py` implements `MQTTClient`, a Klipper extra that wraps the `paho-mqtt` Python library to provide a persistent MQTT v5 broker connection for other fork modules. It manages subscriptions and publications with per-topic QoS tracking, handles automatic broker reconnection (1–120 s back-off), and dispatches received messages to registered callbacks via `reactor.register_async_callback` to ensure callbacks run on the Klipper reactor thread. The `timelapse`, `defect_detection`, and `jsonrpc` modules all use this as their transport layer. Wildcards (`#`, `+`) are explicitly blocked in both subscribe and publish calls.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New module: MQTT v5 client with topic subscription management and async callback dispatch | U1 communicates with an on-board camera and other Linux-side services via MQTT; Klipper's built-in IPC (webhooks/Unix socket) is insufficient for these use cases |

## Additions

### Classes
- **`SubscriptionHandle`** — Lightweight container holding a topic string and callback; used as an opaque handle for `unsubscribe()`.
- **`MQTTClient`** — Klipper extra loaded as `[mqtt]`.

### Key Config Options
- `client_id` — MQTT client ID (default: `klipper_<random_5-7_digit_number>`).
- `address` — Broker hostname/IP (default: `localhost`).
- `port` — Broker port (default: 1883).
- `default_qos` — Default QoS level 0–2 (default: 0).

### Public API
- `subscribe_topic(topic, callback, qos=None)` → `SubscriptionHandle` — Subscribe to an exact topic (no wildcards). If a subscription already exists for the topic, the QoS is upgraded to `max(old, new)` and the callback is appended.
- `unsubscribe(hdl: SubscriptionHandle)` — Remove a specific subscription handle; sends an MQTT unsubscribe only if the last handler for that topic is removed.
- `publish_topic(topic, payload, qos=None, retain=False)` — Publish; dicts/lists are JSON-encoded; booleans are lowercased strings.
- `is_connected()` → bool
- `get_status(eventtime)` → `{'connected': bool}`

### Internal Callbacks
- `_on_connect` — Re-subscribes all known topics on reconnect.
- `_on_message` — Dispatches to all registered handlers for a topic via async reactor callbacks.
- `_on_disconnect` — Logs disconnect reason code.

### Lifecycle
- `_handle_shutdown()` / `_handle_request_restart()` — Disable reconnection and disconnect cleanly on Klipper shutdown or restart.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `paho-mqtt` Python package (`paho.mqtt.client`), which is not shipped with stock Klipper.
- The MQTT network thread (`loop_start()`) runs outside the Klipper reactor; callbacks are bounced back to the reactor thread via `register_async_callback`, but this introduces latency and means ordering with other reactor events is not guaranteed.
- `publish_topic` raises an exception if the broker is not connected, which will propagate to the caller as a G-code error.
- Only MQTTv5 is used (`paho_mqtt.MQTTv5`); brokers that only support v3.1.1 (e.g., some older Mosquitto versions) will reject the connection.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+import logging, json
+import paho.mqtt.client as paho_mqtt
+import threading, random
+from typing import List, Optional, Any, Callable, Dict, Union, Tuple
+
+class SubscriptionHandle:
+    def __init__(self, topic: str, callback: Callable[[bytes], None]):
+        self.callback = callback
+        self.topic = topic
+
+class MQTTClient:
+    def __init__(self, config):
+        ...
+        self.client = paho_mqtt.Client(client_id=self.client_id,
+                                       protocol=paho_mqtt.MQTTv5)
+        self.client.on_connect    = self._on_connect
+        self.client.on_message    = self._on_message
+        self.client.on_disconnect = self._on_disconnect
+        self.client.loop_start()
+        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
+        self.client.connect(self.address, self.port)
+    def subscribe_topic(self, topic, callback, qos=None) -> SubscriptionHandle: ...
+    def unsubscribe(self, hdl): ...
+    def publish_topic(self, topic, payload=None, qos=None, retain=False): ...
+
+def load_config(config):
+    return MQTTClient(config)
```
</details>
