import json
import time
import uuid
import random
import math
import signal
import sys
import threading

import paho.mqtt.client as mqtt
from datetime import datetime


BROKER_HOST = 'broker.emqx.io'
BROKER_PORT = 1883
TOPIC_TELEMETRY = 'smartcity/smartcity-riad-001/node1/telemetry'
TOPIC_STATUS = 'smartcity/smartcity-riad-001/node1/status'
TOPIC_COMMAND = 'smartcity/smartcity-riad-001/node1/command'
TICK_INTERVAL = 5  # seconds

state = {
    'tank_pct': 80.0,
    'soil_pct': 50.0,
    'ldr': 2000,
    'bin_pct': 20.0,
}
cmd_state = {'pump': 'auto', 'light': 'auto'}
tick_count = 0


def on_connect(client, userdata, flags, rc):
    print(f"[SIM] Connected (rc={rc})")
    client.subscribe(TOPIC_COMMAND, qos=1)
    client.publish(TOPIC_STATUS, payload='online', qos=1)


def on_disconnect(client, userdata, rc):
    print(f"[SIM] Disconnected (rc={rc})")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
    except Exception as e:
        print(f"[SIM] decode error: {e}")
        return
    print(f"[SIM-IN] {msg.topic}: {payload}")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"[SIM] parse error: {e}")
        return
    for key in ('pump', 'light'):
        if key in data and data[key] in ('on', 'off', 'auto'):
            cmd_state[key] = data[key]


def update_state():
    global tick_count, state
    tick_count += 1
    # Tank decreases slowly (consumption)
    state['tank_pct'] = max(0.0, state['tank_pct'] - random.uniform(0.5, 2.0))
    # Bin increases slowly (garbage added)
    state['bin_pct'] = min(100.0, state['bin_pct'] + random.uniform(0.1, 0.5))
    # LDR oscillates (simulated day-night cycle, 60-sec period)
    state['ldr'] = int(2500 + 1500 * math.sin(tick_count / 10.0))
    # Soil moisture: determine if pump is active
    pump_active = (
        cmd_state['pump'] == 'on'
        or (cmd_state['pump'] == 'auto' and state['soil_pct'] < 30.0)
    )
    if state['tank_pct'] < 10.0:
        pump_active = False  # dry-run protection
    if pump_active:
        state['soil_pct'] = min(70.0, state['soil_pct'] + 5.0)
    else:
        state['soil_pct'] = max(0.0, state['soil_pct'] - random.uniform(1.0, 3.0))


def build_telemetry():
    return {
        "node_id": "esp32-01",
        "tank_pct": round(state['tank_pct'], 1),
        "soil_pct": round(state['soil_pct'], 1),
        "ldr": int(state['ldr']),
        "bin_pct": round(state['bin_pct'], 1),
        "ts": int(time.time()),
    }


def main():
    client_id = 'sim-esp32-' + uuid.uuid4().hex[:8]
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.will_set(TOPIC_STATUS, payload='offline', qos=1, retain=False)

    print(f"Simulator starting. Client ID: {client_id}")
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_start()

    def shutdown(signum, frame):
        print("\n[SIM] Shutting down...")
        client.publish(TOPIC_STATUS, payload='offline', qos=1)
        time.sleep(0.5)
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"[SIM] Sending telemetry every {TICK_INTERVAL}s. Ctrl+C to stop.")
    try:
        while True:
            update_state()
            payload = build_telemetry()
            client.publish(TOPIC_TELEMETRY, json.dumps(payload), qos=1)
            print(f"[SIM-OUT] {payload}")
            time.sleep(TICK_INTERVAL)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == '__main__':
    main()
