from django.shortcuts import render


def dashboard(request):
    context = {
        'node_id': 'esp32-01',
        'tank_level': 72,
        'soil_moisture': 45,
        'ldr_value': 1800,
        'light_on': True,
        'bin_level': 30,
        'pump_on': False,
    }
    return render(request, 'iot/dashboard.html', context)