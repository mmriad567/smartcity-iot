from django.test import TestCase
from .models import Node, SensorReading, Alert


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