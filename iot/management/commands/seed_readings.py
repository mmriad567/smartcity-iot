import random
from django.core.management.base import BaseCommand
from iot.models import Node, SensorReading


class Command(BaseCommand):
    help = 'টেস্টের জন্য র‍্যান্ডম সেন্সর রিডিং তৈরি করে'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=20,
            help='প্রতি সেন্সরের জন্য কতটি রিডিং'
        )
        parser.add_argument(
            '--tank', type=float, default=None,
            help='নির্দিষ্ট ট্যাংক লেভেল'
        )
        parser.add_argument(
            '--soil', type=float, default=None,
            help='নির্দিষ্ট মাটির আর্দ্রতা'
        )
        parser.add_argument(
            '--ldr', type=float, default=None,
            help='নির্দিষ্ট LDR মান'
        )
        parser.add_argument(
            '--bin', type=float, default=None,
            help='নির্দিষ্ট ডাস্টবিন লেভেল'
        )

    def handle(self, *args, **options):
        node, created = Node.objects.get_or_create(
            node_id='esp32-01',
            defaults={'name': 'পার্ক নোড ১', 'location': 'কেন্দ্রীয় পার্ক'}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'নোড তৈরি: {node}'))

        overrides = {
            'tank_level': options['tank'],
            'soil_moisture': options['soil'],
            'ldr': options['ldr'],
            'bin_level': options['bin'],
        }

        configs = {
            'tank_level':    (10, 100),
            'soil_moisture': (10, 80),
            'ldr':           (500, 4000),
            'bin_level':     (5, 95),
        }

        count = options['count']
        for sensor_type, (low, high) in configs.items():
            if overrides[sensor_type] is not None:
                SensorReading.objects.create(
                    node=node,
                    sensor_type=sensor_type,
                    value=overrides[sensor_type],
                )
            else:
                for _ in range(count):
                    SensorReading.objects.create(
                        node=node,
                        sensor_type=sensor_type,
                        value=round(random.uniform(low, high), 1),
                    )

        self.stdout.write(
            self.style.SUCCESS('রিডিং তৈরি হয়েছে')
        )