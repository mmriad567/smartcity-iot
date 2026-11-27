from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .models import SensorReading, Node, DeviceControl


def get_node():
    return Node.objects.filter(node_id='esp32-01').first()


def get_latest_readings():
    latest = {}
    for sensor_type in ['tank_level', 'soil_moisture', 'ldr', 'bin_level']:
        reading = SensorReading.objects.filter(
            sensor_type=sensor_type
        ).first()
        latest[sensor_type] = reading.value if reading else 0
    return latest


def build_context():
    node = get_node()
    readings = get_latest_readings()

    ldr = int(readings['ldr'])
    soil = readings['soil_moisture']

    control = None
    if node:
        control, _ = DeviceControl.objects.get_or_create(node=node)

    # Auto/Manual লজিক
    if control and control.pump_mode == 'manual':
        pump_on = control.pump_on
    else:
        pump_on = soil < 30

    if control and control.light_mode == 'manual':
        light_on = control.light_on
    else:
        light_on = ldr < 2000

    last_reading = SensorReading.objects.first()

    return {
        'tank_level': int(readings['tank_level']),
        'soil_moisture': int(soil),
        'ldr_value': ldr,
        'light_on': light_on,
        'bin_level': int(readings['bin_level']),
        'pump_on': pump_on,
        'pump_mode': control.pump_mode if control else 'auto',
        'light_mode': control.light_mode if control else 'auto',
        'last_updated': last_reading.timestamp if last_reading else None,
    }


def dashboard(request):
    return render(request, 'iot/dashboard.html', build_context())


def sensor_cards(request):
    return render(request, 'iot/partials/sensor_cards.html', build_context())


def pump_panel(request):
    return render(request, 'iot/partials/pump_panel.html', build_context())


@require_POST
def toggle_pump(request):
    node = get_node()
    if not node:
        return HttpResponse('No node available', status=404)

    control, _ = DeviceControl.objects.get_or_create(node=node)
    action = request.POST.get('action')

    if action == 'on':
        control.pump_on = True
        control.pump_mode = 'manual'
    elif action == 'off':
        control.pump_on = False
        control.pump_mode = 'manual'
    elif action == 'auto':
        control.pump_mode = 'auto'
    else:
        return HttpResponse('Invalid action', status=400)

    control.save()
    return render(request, 'iot/partials/pump_panel.html', build_context())