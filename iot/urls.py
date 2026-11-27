from django.urls import path
from . import views

app_name = 'iot'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('sensor-cards/', views.sensor_cards, name='sensor_cards'),
    path('pump-panel/', views.pump_panel, name='pump_panel'),
    path('toggle-pump/', views.toggle_pump, name='toggle_pump'),
]