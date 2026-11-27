from django.db import models


class Node(models.Model):
    node_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.node_id})"


class SensorReading(models.Model):
    SENSOR_CHOICES = [
        ('tank_level', 'Water Tank Level'),
        ('soil_moisture', 'Soil Moisture'),
        ('ldr', 'Light Level'),
        ('bin_level', 'Dustbin Level'),
    ]

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='readings')
    sensor_type = models.CharField(max_length=30, choices=SENSOR_CHOICES)
    value = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['node', 'sensor_type', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.node.node_id} - {self.sensor_type}: {self.value}"


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    ALERT_TYPE_CHOICES = [
        ('tank_low', 'Tank Low'),
        ('tank_critical', 'Tank Critical'),
        ('bin_full', 'Bin Full'),
    ]

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, blank=True)
    message = models.CharField(max_length=255)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='info')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.message}"
    



class DeviceControl(models.Model):
    MODE_CHOICES = [
        ('auto', 'Auto'),
        ('manual', 'Manual'),
    ]

    node = models.OneToOneField(
        Node,
        on_delete=models.CASCADE,
        related_name='control'
    )
    pump_on = models.BooleanField(default=False)
    light_on = models.BooleanField(default=False)
    pump_mode = models.CharField(
        max_length=10, choices=MODE_CHOICES, default='auto'
    )
    light_mode = models.CharField(
        max_length=10, choices=MODE_CHOICES, default='auto'
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Control for {self.node.node_id}"