from django.urls import path
from . import views_chofer

urlpatterns = [
    # Viajes Asignados y Operación
    path('asignaciones/', views_chofer.MisAsignacionesView.as_view(), name='chofer-asignaciones'),
    path('asignaciones/<int:pk>/', views_chofer.DetalleAsignacionView.as_view(), name='chofer-detalle-asignacion'),
    path('asignaciones/<int:pk>/estado/', views_chofer.ActualizarEstadoViajeView.as_view(), name='chofer-actualizar-viaje'),
    
    # Tracking GPS (para apps móviles/scripts que reportan ubicación viva)
    path('gps/', views_chofer.EnviarGPSView.as_view(), name='chofer-enviar-gps'),
    
    # Entidad del Chofer (Documentos, Licencias, Alertas)
    path('documentos/', views_chofer.ChoferDocumentosView.as_view(), name='chofer-documentos'),
    path('notificaciones/', views_chofer.NotificacionesChoferView.as_view(), name='chofer-notificaciones'),
]
