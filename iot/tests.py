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
    """ড্যাশবোর্ড ভিউ-এর টেস্ট"""

    def test_dashboard_url_exists(self):
        """রুট URL কাজ করে কিনা"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_dashboard_uses_correct_template(self):
        """সঠিক টেমপ্লেট ব্যবহার হচ্ছে কিনা"""
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'iot/dashboard.html')

    def test_dashboard_shows_tank_level(self):
        """ট্যাংক লেভেল পেজে দেখা যাচ্ছে কিনা"""
        response = self.client.get('/')
        self.assertContains(response, '72%')

    def test_dashboard_reverse_url(self):
        """URL name দিয়ে ঠিকানা তৈরি হয় কিনা"""
        url = reverse('iot:dashboard')
        self.assertEqual(url, '/')