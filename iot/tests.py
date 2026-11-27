from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Node, SensorReading, Alert
from .services import create_alert_once


class NodeModelTest(TestCase):
    """Node মডেলের টেস্ট"""

    def setUp(self):
        # প্রতিটি টেস্টের আগে এই ফাংশন চলবে
        # যাতে প্রতিটা টেস্ট পরিষ্কার অবস্থায় শুরু হয়
        self.node = Node.objects.create(
            node_id='esp32-01',
            name='পার্ক নোড ১',
            location='কেন্দ্রীয় পার্ক'
        )

    def test_node_created_successfully(self):
        """একটা নোড ঠিকমতো তৈরি হয় কিনা"""
        self.assertEqual(Node.objects.count(), 1)
        self.assertEqual(self.node.node_id, 'esp32-01')

    def test_node_str_returns_readable_name(self):
        """__str__ মেথড সুন্দর নাম দেয় কিনা"""
        self.assertEqual(str(self.node), 'পার্ক নোড ১ (esp32-01)')

    def test_node_id_must_be_unique(self):
        """একই node_id দুইবার দেওয়া গেলে error হয় কিনা"""
        with self.assertRaises(Exception):
            Node.objects.create(
                node_id='esp32-01',   # ইতিমধ্যে ব্যবহৃত
                name='অন্য নোড'
            )


class SensorReadingModelTest(TestCase):
    """SensorReading মডেলের টেস্ট"""

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='নোড ১'
        )

    def test_reading_created_with_node(self):
        """নোডের সাথে রিডিং যুক্ত হয় কিনা"""
        reading = SensorReading.objects.create(
            node=self.node,
            sensor_type='tank_level',
            value=72.5
        )
        self.assertEqual(reading.node, self.node)
        self.assertEqual(reading.value, 72.5)

    def test_readings_ordering_newest_first(self):
        """সর্বশেষ রিডিং আগে আসে কিনা (Meta.ordering)"""
        SensorReading.objects.create(
            node=self.node, sensor_type='tank_level', value=50
        )
        newer = SensorReading.objects.create(
            node=self.node, sensor_type='tank_level', value=45
        )
        # প্রথম রিডিংটি হওয়া উচিত নতুনটি
        self.assertEqual(
            SensorReading.objects.first().id, newer.id
        )

    def test_cascade_delete(self):
        """নোড ডিলিট হলে তার রিডিংও ডিলিট হয় কিনা"""
        SensorReading.objects.create(
            node=self.node, sensor_type='tank_level', value=60
        )
        self.assertEqual(SensorReading.objects.count(), 1)

        self.node.delete()
        self.assertEqual(SensorReading.objects.count(), 0)  # 👈 ক্যাসকেড কাজ ক


from django.test import TestCase
from django.urls import reverse


class DashboardViewTest(TestCase):

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='টেস্ট নোড'
        )
        SensorReading.objects.create(
            node=self.node, sensor_type='tank_level', value=72
        )
        SensorReading.objects.create(
            node=self.node, sensor_type='soil_moisture', value=45
        )

    def test_dashboard_url_exists(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_uses_correct_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'iot/dashboard.html')

    def test_dashboard_shows_latest_tank_level(self):
        """ডেটাবেসের সর্বশেষ ট্যাংক লেভেল দেখাচ্ছে কিনা"""
        response = self.client.get('/')
        self.assertContains(response, '72%')

    def test_dashboard_shows_latest_soil_moisture(self):
        response = self.client.get('/')
        self.assertContains(response, '45%')

    def test_dashboard_handles_empty_database(self):
        """ডেটাবেস খালি থাকলেও ক্র্যাশ করবে না"""
        SensorReading.objects.all().delete()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_latest_reading_is_used(self):
        """পুরোনো নয়, সর্বশেষ রিডিং ব্যবহৃত হচ্ছে কিনা"""
        SensorReading.objects.create(
            node=self.node, sensor_type='tank_level', value=99
        )
        response = self.client.get('/')
        self.assertContains(response, '99%')
        self.assertNotContains(response, '72%')


class SensorCardsPartialTest(TestCase):
    """HTMX partial ভিউ-এর টেস্ট"""

    def test_partial_url_returns_200(self):
        response = self.client.get('/sensor-cards/')
        self.assertEqual(response.status_code, 200)

    def test_partial_uses_correct_template(self):
        response = self.client.get('/sensor-cards/')
        self.assertTemplateUsed(response, 'iot/partials/sensor_cards.html')

    def test_partial_does_not_contain_navbar(self):
        """Partial-এ নেভবার থাকা যাবে না (শুধু কার্ড)"""
        response = self.client.get('/sensor-cards/')
        self.assertNotContains(response, 'Smart City IoT')


from .models import DeviceControl
from django.urls import reverse


class DeviceControlTest(TestCase):

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='টেস্ট নোড'
        )
        # শুকনো মাটি — auto তে পাম্প ON হওয়া উচিত
        SensorReading.objects.create(
            node=self.node, sensor_type='soil_moisture', value=20
        )

    def test_control_created_on_first_access(self):
        """প্রথমবার build_context() কল করলে Control তৈরি হয়"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DeviceControl.objects.filter(node=self.node).exists())

    def test_pump_on_in_auto_mode_when_soil_dry(self):
        """Auto মোডে শুকনো মাটিতে পাম্প ON দেখায়"""
        response = self.client.get('/')
        self.assertTrue(response.context['pump_on'])
        self.assertEqual(response.context['pump_mode'], 'auto')

    def test_pump_off_in_auto_mode_when_soil_wet(self):
        """Auto মোডে ভেজা মাটিতে পাম্প OFF দেখায়"""
        SensorReading.objects.create(
            node=self.node, sensor_type='soil_moisture', value=70
        )
        response = self.client.get('/')
        self.assertFalse(response.context['pump_on'])

    def test_manual_override_keeps_pump_on(self):
        """Manual-এ চালু করলে শুকনো/ভেজা যাই হোক ON থাকবে"""
        control = DeviceControl.objects.create(
            node=self.node, pump_mode='manual', pump_on=True
        )
        SensorReading.objects.create(
            node=self.node, sensor_type='soil_moisture', value=80
        )
        response = self.client.get('/')
        self.assertTrue(response.context['pump_on'])
        self.assertEqual(response.context['pump_mode'], 'manual')


class TogglePumpTest(TestCase):

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='টেস্ট নোড'
        )
        SensorReading.objects.create(
            node=self.node, sensor_type='soil_moisture', value=20
        )

    def test_toggle_pump_on_sets_manual_mode(self):
        """'on' action → pump_on=True, mode='manual'"""
        response = self.client.post(
            '/toggle-pump/', {'action': 'on'}
        )
        self.assertEqual(response.status_code, 200)
        control = DeviceControl.objects.get(node=self.node)
        self.assertTrue(control.pump_on)
        self.assertEqual(control.pump_mode, 'manual')

    def test_toggle_pump_off_sets_manual_mode(self):
        response = self.client.post(
            '/toggle-pump/', {'action': 'off'}
        )
        control = DeviceControl.objects.get(node=self.node)
        self.assertFalse(control.pump_on)
        self.assertEqual(control.pump_mode, 'manual')

    def test_toggle_pump_auto_restores_auto_mode(self):
        """'auto' action → mode='auto', সেন্সর অনুযায়ী চলবে"""
        DeviceControl.objects.create(
            node=self.node, pump_mode='manual', pump_on=True
        )
        response = self.client.post(
            '/toggle-pump/', {'action': 'auto'}
        )
        control = DeviceControl.objects.get(node=self.node)
        self.assertEqual(control.pump_mode, 'auto')

    def test_invalid_action_returns_400(self):
        response = self.client.post(
            '/toggle-pump/', {'action': 'garbage'}
        )
        self.assertEqual(response.status_code, 400)

    def test_get_method_not_allowed(self):
        """toggle_pump শুধু POST নেয়"""
        response = self.client.get('/toggle-pump/')
        self.assertEqual(response.status_code, 405)

    def test_no_node_returns_404(self):
        """নোড না থাকলে 404"""
        Node.objects.all().delete()
        response = self.client.post(
            '/toggle-pump/', {'action': 'on'}
        )
        self.assertEqual(response.status_code, 404)


class PumpPanelPartialTest(TestCase):

    def test_pump_panel_returns_200(self):
        Node.objects.create(node_id='esp32-01', name='নোড ১')
        response = self.client.get('/pump-panel/')
        self.assertEqual(response.status_code, 200)

    def test_pump_panel_uses_correct_template(self):
        Node.objects.create(node_id='esp32-01', name='নোড ১')
        response = self.client.get('/pump-panel/')
        self.assertTemplateUsed(response, 'iot/partials/pump_panel.html')


class AlertCooldownTest(TestCase):
    """Test the 30-minute cooldown on alert creation."""

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='Test Node'
        )

    def test_alert_created_when_no_previous_alert(self):
        create_alert_once(self.node, 'tank_low', 'Low tank', 'warning')
        self.assertEqual(
            Alert.objects.filter(alert_type='tank_low').count(), 1
        )

    def test_alert_not_duplicated_while_unresolved(self):
        create_alert_once(self.node, 'tank_low', 'Low tank', 'warning')
        create_alert_once(self.node, 'tank_low', 'Low again', 'warning')
        self.assertEqual(
            Alert.objects.filter(alert_type='tank_low').count(), 1
        )

    def test_alert_recreated_after_cooldown_expires(self):
        create_alert_once(self.node, 'tank_low', 'Low tank', 'warning')
        alert = Alert.objects.get(alert_type='tank_low')
        alert.is_resolved = True
        alert.resolved_at = timezone.now() - timedelta(minutes=31)
        alert.save()
        create_alert_once(self.node, 'tank_low', 'Low again', 'warning')
        self.assertEqual(
            Alert.objects.filter(alert_type='tank_low').count(), 2
        )

    def test_alert_skipped_within_cooldown(self):
        create_alert_once(self.node, 'tank_low', 'Low tank', 'warning')
        alert = Alert.objects.get(alert_type='tank_low')
        alert.is_resolved = True
        alert.resolved_at = timezone.now() - timedelta(minutes=5)
        alert.save()
        create_alert_once(self.node, 'tank_low', 'Low again', 'warning')
        self.assertEqual(
            Alert.objects.filter(alert_type='tank_low').count(), 1
        )

    def test_resolve_sets_resolved_at(self):
        create_alert_once(self.node, 'tank_low', 'Low tank', 'warning')
        alert = Alert.objects.get(alert_type='tank_low')
        self.client.post(f'/alerts/{alert.id}/resolve/')
        alert.refresh_from_db()
        self.assertTrue(alert.is_resolved)
        self.assertIsNotNone(alert.resolved_at)


from unittest.mock import patch


class TogglePumpPublishesMqttTest(TestCase):

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='Test Node'
        )
        SensorReading.objects.create(
            node=self.node, sensor_type='soil_moisture', value=20
        )

    @patch('iot.views.publish_command')
    def test_toggle_pump_on_publishes_on(self, mock_pub):
        self.client.post('/toggle-pump/', {'action': 'on'})
        mock_pub.assert_called_once_with({'pump': 'on'})

    @patch('iot.views.publish_command')
    def test_toggle_pump_off_publishes_off(self, mock_pub):
        self.client.post('/toggle-pump/', {'action': 'off'})
        mock_pub.assert_called_once_with({'pump': 'off'})

    @patch('iot.views.publish_command')
    def test_toggle_pump_auto_publishes_auto(self, mock_pub):
        self.client.post('/toggle-pump/', {'action': 'auto'})
        mock_pub.assert_called_once_with({'pump': 'auto'})

    @patch('iot.views.publish_command')
    def test_toggle_pump_invalid_action_does_not_publish(self, mock_pub):
        response = self.client.post('/toggle-pump/', {'action': 'garbage'})
        self.assertEqual(response.status_code, 400)
        mock_pub.assert_not_called()

    @patch('iot.views.publish_command')
    def test_toggle_pump_survives_mqtt_failure(self, mock_pub):
        # Simulate MQTT broker down (publish_command swallows errors)
        mock_pub.return_value = False
        response = self.client.post('/toggle-pump/', {'action': 'on'})
        # HTTP response must be 200 even if MQTT fails
        self.assertEqual(response.status_code, 200)


class ToggleLightTest(TestCase):

    def setUp(self):
        self.node = Node.objects.create(
            node_id='esp32-01', name='Test Node'
        )
        SensorReading.objects.create(
            node=self.node, sensor_type='ldr', value=3000
        )

    @patch('iot.views.publish_command')
    def test_toggle_light_on_sets_manual_and_publishes(self, mock_pub):
        response = self.client.post('/toggle-light/', {'action': 'on'})
        self.assertEqual(response.status_code, 200)
        control = DeviceControl.objects.get(node=self.node)
        self.assertTrue(control.light_on)
        self.assertEqual(control.light_mode, 'manual')
        mock_pub.assert_called_once_with({'light': 'on'})

    @patch('iot.views.publish_command')
    def test_toggle_light_off_sets_manual_and_publishes(self, mock_pub):
        self.client.post('/toggle-light/', {'action': 'off'})
        control = DeviceControl.objects.get(node=self.node)
        self.assertFalse(control.light_on)
        self.assertEqual(control.light_mode, 'manual')
        mock_pub.assert_called_once_with({'light': 'off'})

    @patch('iot.views.publish_command')
    def test_toggle_light_auto_restores_auto_mode(self, mock_pub):
        DeviceControl.objects.create(
            node=self.node, light_mode='manual', light_on=True
        )
        self.client.post('/toggle-light/', {'action': 'auto'})
        control = DeviceControl.objects.get(node=self.node)
        self.assertEqual(control.light_mode, 'auto')
        mock_pub.assert_called_once_with({'light': 'auto'})

    @patch('iot.views.publish_command')
    def test_toggle_light_invalid_action_returns_400(self, mock_pub):
        response = self.client.post('/toggle-light/', {'action': 'garbage'})
        self.assertEqual(response.status_code, 400)
        mock_pub.assert_not_called()

    def test_toggle_light_get_method_not_allowed(self):
        response = self.client.get('/toggle-light/')
        self.assertEqual(response.status_code, 405)


class LightPanelPartialTest(TestCase):

    def setUp(self):
        Node.objects.create(node_id='esp32-01', name='Test Node')

    def test_light_panel_returns_200(self):
        response = self.client.get('/light-panel/')
        self.assertEqual(response.status_code, 200)

    def test_light_panel_uses_correct_template(self):
        response = self.client.get('/light-panel/')
        self.assertTemplateUsed(response, 'iot/partials/light_panel.html')

    def test_light_panel_shows_auto_when_mode_auto(self):
        response = self.client.get('/light-panel/')
        self.assertContains(response, 'AUTO')

    def test_light_panel_shows_manual_when_mode_manual(self):
        node = Node.objects.get(node_id='esp32-01')
        DeviceControl.objects.create(
            node=node, light_mode='manual', light_on=True
        )
        response = self.client.get('/light-panel/')
        self.assertContains(response, 'MANUAL')


class DashboardHasBothPanelsTest(TestCase):

    def setUp(self):
        Node.objects.create(node_id='esp32-01', name='Test Node')

    def test_dashboard_contains_pump_and_light_panels(self):
        response = self.client.get('/')
        self.assertContains(response, 'id="pump-panel"')
        self.assertContains(response, 'id="light-panel"')