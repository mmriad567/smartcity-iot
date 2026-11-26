from django.shortcuts import render
from .models import SensorReading


def get_latest_readings():
    """প্রতিটি সেন্সরের সর্বশেষ মান ডেটাবেস থেকে নিয়ে আসে"""
    latest = {}
    for sensor_type in ['tank_level', 'soil_moisture', 'ldr', 'bin_level']:
        reading = SensorReading.objects.filter(
            sensor_type=sensor_type
        ).first()
        latest[sensor_type] = reading.value if reading else 0
    return latest


def build_context():
    """ড্যাশবোর্ডে পাঠানোর ডেটা তৈরি করে"""
    readings = get_latest_readings()
    ldr = int(readings['ldr'])
    return {
        'tank_level': int(readings['tank_level']),
        'soil_moisture': int(readings['soil_moisture']),
        'ldr_value': ldr,
        'light_on': ldr < 2000,          # অন্ধকার = লাইট জ্বলে
        'bin_level': int(readings['bin_level']),
        'pump_on': readings['soil_moisture'] < 30,  # শুকনো = পাম্প চালু
    }


def dashboard(request):
    return render(request, 'iot/dashboard.html', build_context())


def sensor_cards(request):
    """HTMX-এর জন্য শুধু কার্ডগুলো ফেরত দেয় (পুরো পেজ নয়)"""
    return render(request, 'iot/partials/sensor_cards.html', build_context())