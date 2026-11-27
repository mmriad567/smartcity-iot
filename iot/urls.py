from django.urls import path
from . import views

app_name = 'iot'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sensor-cards/', views.sensor_cards, name='sensor_cards'),
    path('pump-panel/', views.pump_panel, name='pump_panel'),
    path('alerts-banner/', views.alerts_banner, name='alerts_banner'),
    path('toggle-pump/', views.toggle_pump, name='toggle_pump'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
]