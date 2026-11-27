import json
import logging
import uuid

import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt


BROKER_HOST = 'broker.emqx.io'
BROKER_PORT = 1883
TOPIC_COMMAND = 'smartcity/smartcity-riad-001/node1/command'
PUBLISH_TIMEOUT_SEC = 3

logger = logging.getLogger('iot.mqtt_client')


def publish_command(payload: dict) -> bool:
    """Fire-and-forget MQTT publish. Returns True on success, False on failure.
       Never raises. Safe to call from HTTP request handlers."""
    try:
        publish.single(
            TOPIC_COMMAND,
            payload=json.dumps(payload),
            hostname=BROKER_HOST,
            port=BROKER_PORT,
            qos=1,
            client_id='django-pub-' + uuid.uuid4().hex[:8],
            keepalive=15,
        )
        logger.info(f"MQTT command published: {payload}")
        return True
    except Exception as e:
        logger.warning(f"MQTT publish failed: {e}")
        return False
