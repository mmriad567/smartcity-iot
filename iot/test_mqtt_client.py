from unittest.mock import patch

from django.test import TestCase

from iot import mqtt_client


class PublishCommandTest(TestCase):

    @patch('iot.mqtt_client.publish.single')
    def test_publish_command_calls_broker(self, mock_single):
        result = mqtt_client.publish_command({'pump': 'on'})
        self.assertTrue(result)
        self.assertEqual(mock_single.call_count, 1)
        args, kwargs = mock_single.call_args
        # first positional arg = topic
        self.assertEqual(args[0], mqtt_client.TOPIC_COMMAND)
        # payload is JSON string
        self.assertIn('pump', kwargs['payload'])
        self.assertIn('on', kwargs['payload'])
        self.assertEqual(kwargs['hostname'], mqtt_client.BROKER_HOST)

    @patch('iot.mqtt_client.publish.single')
    def test_publish_command_returns_false_on_error(self, mock_single):
        mock_single.side_effect = Exception('broker down')
        result = mqtt_client.publish_command({'pump': 'on'})
        self.assertFalse(result)

    @patch('iot.mqtt_client.publish.single')
    def test_publish_command_never_raises(self, mock_single):
        mock_single.side_effect = ConnectionError('network dead')
        try:
            mqtt_client.publish_command({'pump': 'auto'})
        except Exception as e:
            self.fail(f'publish_command raised: {e}')
