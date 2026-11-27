from django.urls import path
from . import views

app_name = 'iot'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sensor-cards/', views.sensor_cards, name='sensor_cards'),
    path('pump-panel/', views.pump_panel, name='pump_panel'),
    path('light-panel/', views.light_panel, name='light_panel'),
    path('chart-panel/', views.chart_panel, name='chart_panel'),
    path('alerts-banner/', views.alerts_banner, name='alerts_banner'),
    path('toggle-pump/', views.toggle_pump, name='toggle_pump'),
    path('toggle-light/', views.toggle_light, name='toggle_light'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
]