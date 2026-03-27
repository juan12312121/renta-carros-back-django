from django.urls import path
from . import views_cliente

urlpatterns = [
    # Catálogo (Público / Clientes)
    path('vehiculos/', views_cliente.CatalogoVehiculosView.as_view(), name='cliente-catalogo-vehiculos'),
    path('vehiculos/<int:pk>/', views_cliente.DetalleVehiculoCatalogoView.as_view(), name='cliente-detalle-vehiculo'),
    
    # Rentas (Reservaciones de los clientes)
    path('rentales/', views_cliente.MisRentalesView.as_view(), name='cliente-mis-rentales'),
    path('rentales/crear/', views_cliente.CrearRentalView.as_view(), name='cliente-crear-rental'),
    path('rentales/<int:pk>/', views_cliente.DetalleMiRentalView.as_view(), name='cliente-detalle-rental'),
    
    # Pagos
    path('pagos/', views_cliente.IniciarPagoView.as_view(), name='cliente-iniciar-pago'),
    
    # Documentos e Identidad
    path('documentos/', views_cliente.MisDocumentosView.as_view(), name='cliente-documentos'),
    
    # Tickets de Soporte
    path('tickets/', views_cliente.MisTicketsView.as_view(), name='cliente-tickets'),
    
    # Reseñas
    path('resenas/vehiculos/', views_cliente.CrearResenaVehiculoView.as_view(), name='cliente-resenar-vehiculo'),
    path('resenas/choferes/', views_cliente.CrearResenaChoferView.as_view(), name='cliente-resenar-chofer'),
    
    # Promociones
    path('promociones/validar/', views_cliente.ValidarPromocionView.as_view(), name='cliente-validar-promocion'),

    # Seguimiento GPS
    path('rentales/<int:pk>/gps/', views_cliente.SeguimientoGPSChoferView.as_view(), name='cliente-seguimiento-gps'),
    
    # Facturas
    path('facturas/', views_cliente.MisFacturasView.as_view(), name='cliente-mis-facturas'),
    
    # Notificaciones
    path('notificaciones/', views_cliente.MisNotificacionesView.as_view(), name='cliente-notificaciones'),

    # Programa de Lealtad / Nivel
    path('nivel/', views_cliente.MiNivelView.as_view(), name='cliente-nivel'),
    
    # Listado de Promociones (Nueva)
    path('promociones/', views_cliente.ListaPromocionesView.as_view(), name='cliente-promociones'),
    
    # Listado de Facturas (Nueva)
    path('facturas/', views_cliente.ListaFacturasView.as_view(), name='cliente-facturas'),
]
