"""
Views para Choferes - Sistema de Renta de Carros
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Rental, Usuario, SeguimientoGPS, DocumentoUsuario, TicketSoporte, Notificacion
from .serializers import (
    ChoferRentalSerializer, SeguimientoGPSSerializer, 
    DocumentoUsuarioSerializer, TicketSoporteSerializer, NotificacionSerializer
)

class ChoferRequiredMixin:
    """Valida que el usuario sea chofer y esté activo."""
    permission_classes = [IsAuthenticated]

    def get_chofer(self, request):
        try:
            usuario = Usuario.objects.get(id=request.user.id, role='chofer', activo=True)
            if not usuario.verificado or not usuario.activo_chofer:
                return None, Response(
                    {'error': 'Tu cuenta de chofer no está verificada o está inactiva.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return usuario, None
        except Usuario.DoesNotExist:
            return None, Response(
                {'error': 'Acceso denegado. Se requiere cuenta de chofer.'},
                status=status.HTTP_403_FORBIDDEN
            )

# ===============================================
# GESTIÓN DE VIAJES (RENTALES)
# ===============================================

class MisAsignacionesView(ChoferRequiredMixin, APIView):
    """GET /api/chofer/asignaciones/"""
    def get(self, request):
        chofer, error = self.get_chofer(request)
        if error: return error
        
        estado = request.query_params.get('estado')
        qs = Rental.objects.filter(chofer=chofer)
        
        if estado:
            qs = qs.filter(estado=estado)
        else:
            qs = qs.exclude(estado='cancelada')
            
        qs = qs.order_by('-fecha_inicio')
        
        serializer = ChoferRentalSerializer(qs, many=True)
        return Response({'asignaciones': serializer.data})


class DetalleAsignacionView(ChoferRequiredMixin, APIView):
    """GET /api/chofer/asignaciones/<id>/"""
    def get(self, request, pk):
        chofer, error = self.get_chofer(request)
        if error: return error
        
        try:
            rental = Rental.objects.get(pk=pk, chofer=chofer)
            return Response(ChoferRentalSerializer(rental).data)
        except Rental.DoesNotExist:
            return Response({'error': 'Asignación no encontrada.'}, status=status.HTTP_404_NOT_FOUND)


class ActualizarEstadoViajeView(ChoferRequiredMixin, APIView):
    """PATCH /api/chofer/asignaciones/<id>/estado/"""
    def patch(self, request, pk):
        chofer, error = self.get_chofer(request)
        if error: return error
        
        try:
            rental = Rental.objects.get(pk=pk, chofer=chofer)
        except Rental.DoesNotExist:
            return Response({'error': 'Asignación no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            
        nuevo_estado = request.data.get('estado')
        
        # Parámetros opcionales reportados por el chofer
        km_inicio = request.data.get('kilometraje_inicio')
        km_fin = request.data.get('kilometraje_fin')
        cond_inicio = request.data.get('condicion_inicio')
        cond_fin = request.data.get('condicion_fin')
        danos = request.data.get('danos_reportados')
        
        if nuevo_estado:
            if nuevo_estado not in ['en_curso', 'completada']:
                return Response({'error': 'Transición de estado no permitida.'}, status=status.HTTP_400_BAD_REQUEST)
                
            rental.estado = nuevo_estado
            
            if nuevo_estado == 'en_curso':
                if km_inicio: rental.kilometraje_inicio = km_inicio
                if cond_inicio: rental.condicion_inicio = cond_inicio
                
            elif nuevo_estado == 'completada':
                rental.fecha_devolucion_real = timezone.now()
                if km_fin: rental.kilometraje_fin = km_fin
                if cond_fin: rental.condicion_fin = cond_fin
                if danos: rental.danos_reportados = danos
                
                # Actualizar estadísticas del chofer
                chofer.total_viajes_completados += 1
                chofer.save(update_fields=['total_viajes_completados'])
                
                # Liberar el vehículo
                rental.vehiculo.estado = 'disponible'
                rental.vehiculo.save(update_fields=['estado'])
                
                # Notificar al cliente
                Notificacion.objects.create(
                    usuario=rental.cliente,
                    titulo='Viaje Completado',
                    mensaje='Tu viaje ha sido completado. Por favor, califica al conductor y al vehículo.',
                    tipo='rental',
                    renta=rental
                )

        rental.save()
        return Response({
            'mensaje': f'Estado de viaje actualizado a {nuevo_estado}',
            'asignacion': ChoferRentalSerializer(rental).data
        })

# ===============================================
# SEGUIMIENTO GPS
# ===============================================

class EnviarGPSView(ChoferRequiredMixin, APIView):
    """POST /api/chofer/gps/"""
    def post(self, request):
        chofer, error = self.get_chofer(request)
        if error: return error
        
        renta_id = request.data.get('renta')
        
        try:
            renta = Rental.objects.get(pk=renta_id, chofer=chofer, estado='en_curso')
        except Rental.DoesNotExist:
            return Response({'error': 'Renta no válida o no en curso.'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = SeguimientoGPSSerializer(data=request.data)
        if serializer.is_valid():
            gps = serializer.save(renta=renta)
            return Response({'mensaje': 'GPS registrado.', 'gps_id': gps.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ===============================================
# DOCUMENTOS Y NOTIFICACIONES
# ===============================================

class ChoferDocumentosView(ChoferRequiredMixin, APIView):
    """GET/POST /api/chofer/documentos/"""
    def get(self, request):
        chofer, error = self.get_chofer(request)
        if error: return error
        qs = DocumentoUsuario.objects.filter(usuario=chofer).order_by('-creado_en')
        return Response({'documentos': DocumentoUsuarioSerializer(qs, many=True).data})

    def post(self, request):
        chofer, error = self.get_chofer(request)
        if error: return error
        serializer = DocumentoUsuarioSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(usuario=chofer, verificado=False)
            return Response({'mensaje': 'Documento subido.', 'documento': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NotificacionesChoferView(ChoferRequiredMixin, APIView):
    """GET /api/chofer/notificaciones/"""
    def get(self, request):
        chofer, error = self.get_chofer(request)
        if error: return error
        qs = Notificacion.objects.filter(usuario=chofer).order_by('-creado_en')[:20]
        return Response({'notificaciones': NotificacionSerializer(qs, many=True).data})
