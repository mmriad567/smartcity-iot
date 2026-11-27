from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import SensorReading, Node, DeviceControl, Alert
from .services import (
    check_alerts, get_latest_value, get_pump_state, get_light_state,
)


def get_node():
    return Node.objects.filter(node_id='esp32-01').first()


def build_context():
    node = get_node()

    if node:
        check_alerts(node)  # প্রতিবার ড্যাশবোর্ড খুললেই লজিক চেক

    tank = get_latest_value('tank_level')
    soil = get_latest_value('soil_moisture')
    ldr = get_latest_value('ldr')
    bin_level = get_latest_value('bin_level')

    control = None
    if node:
        control, _ = DeviceControl.objects.get_or_create(node=node)

    last_reading = SensorReading.objects.first()

    return {
        'tank_level': int(tank or 0),
        'soil_moisture': int(soil or 0),
        'ldr_value': int(ldr or 0),
        'bin_level': int(bin_level or 0),
        'pump_on': get_pump_state(soil, tank, control),
        'light_on': get_light_state(ldr, control),
        'pump_mode': control.pump_mode if control else 'auto',
        'light_mode': control.light_mode if control else 'auto',
        'last_updated': last_reading.timestamp if last_reading else None,
        'active_alerts': Alert.objects.filter(is_resolved=False)[:5],
    }


def dashboard(request):
    return render(request, 'iot/dashboard.html', build_context())


def sensor_cards(request):
    return render(request, 'iot/partials/sensor_cards.html', build_context())


def pump_panel(request):
    return render(request, 'iot/partials/pump_panel.html', build_context())


def alerts_banner(request):
    return render(request, 'iot/partials/alerts_banner.html', build_context())


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


@require_POST
def resolve_alert(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.save()
    return render(request, 'iot/partials/alerts_banner.html', build_context())