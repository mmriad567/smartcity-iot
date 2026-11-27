from .models import Alert, SensorReading


TANK_LOW_THRESHOLD = 20
TANK_CRITICAL_THRESHOLD = 10
BIN_FULL_THRESHOLD = 80
SOIL_DRY_THRESHOLD = 30
LDR_DARK_THRESHOLD = 2000


def get_latest_value(sensor_type):
    reading = SensorReading.objects.filter(sensor_type=sensor_type).first()
    return reading.value if reading else None


def create_alert_once(node, alert_type, message, severity):
    """একই টাইপের unresolved alert থাকলে নতুন তৈরি করে না"""
    already_exists = Alert.objects.filter(
        node=node, alert_type=alert_type, is_resolved=False
    ).exists()
    if not already_exists:
        Alert.objects.create(
            node=node,
            alert_type=alert_type,
            message=message,
            severity=severity,
        )


def check_alerts(node):
    """সর্বশেষ রিডিং দেখে দরকার হলে অ্যালার্ট তৈরি করে"""
    if not node:
        return

    tank = get_latest_value('tank_level')
    bin_level = get_latest_value('bin_level')

    if tank is not None:
        if tank < TANK_CRITICAL_THRESHOLD:
            create_alert_once(
                node, 'tank_critical',
                f'🚨 পানি ট্যাংক সংকটাপন্ন! মাত্র {int(tank)}% বাকি',
                'critical',
            )
        elif tank < TANK_LOW_THRESHOLD:
            create_alert_once(
                node, 'tank_low',
                f'পানি ট্যাংক কম: {int(tank)}%',
                'warning',
            )

    if bin_level is not None and bin_level > BIN_FULL_THRESHOLD:
        create_alert_once(
            node, 'bin_full',
            f'ডাস্টবিন ভরে গেছে: {int(bin_level)}%',
            'warning',
        )


def get_pump_state(soil_moisture, tank_level, control):
    """পাম্প চালু হবে কিনা — সব নিয়ম মিলিয়ে"""
    # ১. ট্যাংক সংকটাপন্ন হলে পাম্প কখনো চলবে না
    if tank_level is not None and tank_level < TANK_CRITICAL_THRESHOLD:
        return False

    # ২. Manual মোডে ব্যবহারকারীর সেট মান
    if control and control.pump_mode == 'manual':
        return control.pump_on

    # ৩. Auto মোডে মাটির আর্দ্রতা
    return (soil_moisture or 0) < SOIL_DRY_THRESHOLD


def get_light_state(ldr_value, control):
    """লাইট জ্বলবে কিনা"""
    if control and control.light_mode == 'manual':
        return control.light_on
    return (ldr_value or 0) < LDR_DARK_THRESHOLD