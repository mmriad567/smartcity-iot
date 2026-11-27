from django.contrib import admin
from .models import Node, SensorReading, Alert,DeviceControl


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('node_id', 'name', 'is_online', 'last_seen')
    search_fields = ('node_id', 'name')


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('node', 'sensor_type', 'value', 'timestamp')
    list_filter = ('sensor_type', 'node')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('node', 'message', 'severity', 'is_resolved', 'created_at')
    list_filter = ('severity', 'is_resolved')

@admin.register(DeviceControl)
class DeviceControlAdmin(admin.ModelAdmin):
    list_display = ('node', 'pump_on', 'pump_mode', 'light_on', 'light_mode', 'updated_at')
    list_filter = ('pump_mode', 'light_mode')