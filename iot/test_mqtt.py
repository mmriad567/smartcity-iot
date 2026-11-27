from unittest.mock import MagicMock

from django.test import TestCase
from django.utils import timezone

from iot.models import Node, SensorReading
from iot.management.commands.mqtt_listener import Command, TOPIC_TELEMETRY


class MqttListenerTest(TestCase):

    def setUp(self):
        self.cmd = Command()
        self.cmd.stdout = MagicMock()
        self.cmd.style = MagicMock()

    def _msg(self, topic, raw_payload):
        msg = MagicMock()
        msg.topic = topic
        msg.payload = raw_payload.encode('utf-8')
        return msg

    def test_valid_telemetry_creates_all_four_readings(self):
        payload = '{"node_id":"esp32-01","tank_pct":72,"soil_pct":45,"ldr":1800,"bin_pct":30}'
        self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, payload))
        self.assertEqual(SensorReading.objects.filter(sensor_type='tank_level').count(), 1)
        self.assertEqual(SensorReading.objects.filter(sensor_type='soil_moisture').count(), 1)
        self.assertEqual(SensorReading.objects.filter(sensor_type='ldr').count(), 1)
        self.assertEqual(SensorReading.objects.filter(sensor_type='bin_level').count(), 1)

    def test_partial_payload_creates_only_present_readings(self):
        payload = '{"tank_pct":50}'
        self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, payload))
        self.assertEqual(SensorReading.objects.filter(sensor_type='tank_level').count(), 1)
        self.assertEqual(SensorReading.objects.filter(sensor_type='soil_moisture').count(), 0)
        self.assertEqual(SensorReading.objects.count(), 1)

    def test_node_created_if_missing(self):
        self.assertFalse(Node.objects.filter(node_id='esp32-01').exists())
        payload = '{"tank_pct":50}'
        self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, payload))
        self.assertTrue(Node.objects.filter(node_id='esp32-01').exists())

    def test_invalid_json_does_not_crash(self):
        try:
            self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, '{not valid'))
        except Exception as e:
            self.fail(f'on_message raised on bad JSON: {e}')
        self.assertEqual(SensorReading.objects.count(), 0)

    def test_non_telemetry_topic_is_ignored(self):
        payload = '{"tank_pct":50}'
        self.cmd.on_message(None, None, self._msg('some/other/topic', payload))
        self.assertEqual(SensorReading.objects.count(), 0)

    def test_node_marked_online_and_last_seen_updated(self):
        payload = '{"tank_pct":50}'
        self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, payload))
        node = Node.objects.get(node_id='esp32-01')
        self.assertTrue(node.is_online)
        self.assertIsNotNone(node.last_seen)

    def test_numeric_string_values_are_accepted(self):
        payload = '{"tank_pct":"65","soil_pct":"40"}'
        self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, payload))
        self.assertEqual(SensorReading.objects.filter(sensor_type='tank_level').count(), 1)
        reading = SensorReading.objects.get(sensor_type='tank_level')
        self.assertEqual(reading.value, 65.0)

    def test_non_numeric_value_skipped(self):
        payload = '{"tank_pct":"not_a_number","soil_pct":40}'
        self.cmd.on_message(None, None, self._msg(TOPIC_TELEMETRY, payload))
        self.assertEqual(SensorReading.objects.filter(sensor_type='tank_level').count(), 0)
        self.assertEqual(SensorReading.objects.filter(sensor_type='soil_moisture').count(), 1)
