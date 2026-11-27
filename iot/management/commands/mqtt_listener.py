import json
import uuid
import logging

import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from django.utils import timezone

from iot.models import Node, SensorReading


BROKER_HOST = 'broker.emqx.io'
BROKER_PORT = 1883
TOPIC_TELEMETRY = 'smartcity/smartcity-riad-001/node1/telemetry'
TOPIC_STATUS = 'smartcity/smartcity-riad-001/node1/status'

logger = logging.getLogger('iot.mqtt_listener')


class Command(BaseCommand):
    help = 'Listen to MQTT telemetry and save to DB'

    def handle(self, *args, **options):
        client_id = 'django-smartcity-' + uuid.uuid4().hex[:8]
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.on_message = self.on_message
        client.reconnect_delay_set(min_delay=1, max_delay=60)
        client.will_set(TOPIC_STATUS, payload='offline', qos=1, retain=False)
        self.stdout.write(f'Connecting to {BROKER_HOST}:{BROKER_PORT} as {client_id}...')
        client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        try:
            client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write('Stopped.')

    def on_connect(self, client, userdata, flags, rc):
        self.stdout.write(self.style.SUCCESS(f'[MQTT] Connected (rc={rc})'))
        client.subscribe(TOPIC_TELEMETRY, qos=1)
        client.subscribe(TOPIC_STATUS, qos=1)
        client.publish(TOPIC_STATUS, payload='online', qos=1)
        self.stdout.write(f'[MQTT] Subscribed to telemetry and status')

    def on_disconnect(self, client, userdata, rc):
        self.stdout.write(f'[MQTT] Disconnected (rc={rc})')

    def on_message(self, client, userdata, msg):
        try:
            payload_str = msg.payload.decode('utf-8')
        except Exception as e:
            logger.warning(f'Decode error: {e}')
            return
        self.stdout.write(f'[MQTT-IN] {msg.topic}: {payload_str}')
        if msg.topic != TOPIC_TELEMETRY:
            return
        try:
            data = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.warning(f'JSON parse error: {e}')
            return
        node_id = data.get('node_id', 'esp32-01')
        node, _ = Node.objects.get_or_create(
            node_id=node_id,
            defaults={'name': 'পার্ক নোড ১'}
        )
        mapping = {
            'tank_pct': 'tank_level',
            'soil_pct': 'soil_moisture',
            'ldr': 'ldr',
            'bin_pct': 'bin_level',
        }
        for payload_key, sensor_type in mapping.items():
            if payload_key in data:
                try:
                    value = float(data[payload_key])
                except (TypeError, ValueError):
                    continue
                SensorReading.objects.create(
                    node=node, sensor_type=sensor_type, value=value
                )
        node.is_online = True
        node.last_seen = timezone.now()
        node.save()
