"""
URLs del sistema de renta de carros
"""

from django.urls import path, include
from . import authentication
from . import views_admin

# -----------------------------------------------
# RUTAS DE AUTENTICACIÓN
# -----------------------------------------------
auth_urlpatterns = [
    path('registro/cliente/', authentication.RegistroClienteView.as_view(), name='registro-cliente'),
    path('registro/chofer/', authentication.RegistroChoferView.as_view(), name='registro-chofer'),
    path('registro/admin/', authentication.RegistroAdminView.as_view(), name='registro-admin'),
    path('login/', authentication.LoginView.as_view(), name='login'),
    path('logout/', authentication.LogoutView.as_view(), name='logout'),
    path('me/', authentication.MiPerfilView.as_view(), name='mi-perfil'),
    path('cambiar-password/', authentication.CambiarPasswordView.as_view(), name='cambiar-password'),
]

# -----------------------------------------------
# RUTAS DE ADMIN
# -----------------------------------------------
admin_urlpatterns = [
    path('dashboard/', views_admin.AdminDashboardView.as_view()),
    path('usuarios/', views_admin.AdminListaUsuariosView.as_view()),
    path('usuarios/<int:pk>/', views_admin.AdminDetalleUsuarioView.as_view()),
    path('usuarios/<int:pk>/verificar/', views_admin.AdminVerificarChoferView.as_view()),
    path('vehiculos/', views_admin.AdminListaVehiculosView.as_view()),
    path('vehiculos/<int:pk>/', views_admin.AdminDetalleVehiculoView.as_view()),
    path('mantenimientos/', views_admin.AdminListaMantenimientosView.as_view()),
    path('mantenimientos/<int:pk>/', views_admin.AdminDetalleMantenimientoView.as_view()),
    path('rentales/', views_admin.AdminListaRentalesView.as_view()),
    path('rentales/<int:pk>/', views_admin.AdminDetalleRentalView.as_view()),
    path('rentales/<int:pk>/asignar-chofer/', views_admin.AdminAsignarChoferView.as_view()),
    path('pagos/', views_admin.AdminListaPagosView.as_view()),
    path('pagos/<int:pk>/', views_admin.AdminActualizarPagoView.as_view()),
    path('tickets/', views_admin.AdminListaTicketsView.as_view()),
    path('tickets/<int:pk>/', views_admin.AdminDetalleTicketView.as_view()),
    path('promociones/', views_admin.AdminListaPromocionesView.as_view()),
    path('promociones/<int:pk>/', views_admin.AdminDetallePromocionView.as_view()),
    path('estadisticas/', views_admin.AdminEstadisticasView.as_view()),
    path('documentos/', views_admin.AdminDocumentosView.as_view()),
    path('documentos/<int:pk>/verificar/', views_admin.AdminVerificarDocumentoView.as_view()),
    path('admin/notificaciones/enviar/', views_admin.AdminEnviarNotificacionView.as_view(), name='admin-enviar-notificacion'),
    path('admin/auditoria/', views_admin.AdminAuditoriaView.as_view(), name='admin-auditoria'),
]

# -----------------------------------------------
# RUTAS PRINCIPALES
# -----------------------------------------------
urlpatterns = [
    path('auth/', include(auth_urlpatterns)),
    path('admin/', include(admin_urlpatterns)),
    path('cliente/', include('api.urls_cliente')),
    path('chofer/', include('api.urls_chofer')),
]