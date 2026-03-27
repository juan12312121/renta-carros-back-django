"""
Views para Clientes - Sistema de Renta de Carros
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import datetime

from .models import Vehiculo, Rental, Usuario, Pago, DocumentoUsuario, TicketSoporte, ResenaVehiculo, ResenaChofer, Promocion, SeguimientoGPS, Factura, Notificacion
from .serializers import (
    VehiculoResumenSerializer, VehiculoDetalleSerializer,
    RentalResumenSerializer, CrearRentalSerializer, RentalDetalleSerializer,
    DocumentoUsuarioSerializer, TicketSoporteSerializer,
    ResenaVehiculoSerializer, ResenaChoferSerializer,
    CrearPagoSerializer, PagoSerializer,
    ValidarPromocionSerializer, SeguimientoGPSSerializer,
    FacturaSerializer, NotificacionSerializer
)

from .authentication import JWTAuthentication

class ClienteRequiredMixin:
    """Valida que el usuario autenticado sea de tipo cliente o admin usando JWT Authentication manualmente."""
    permission_classes = [] # Se maneja de forma manual

    def get_cliente(self, request):
        usuario, error = JWTAuthentication.obtener_usuario_de_request(request)
        if error:
            return None, error
            
        if usuario.role not in ['cliente', 'admin']:
            return None, Response(
                {'error': 'Acceso denegado. Se requiere cuenta de cliente o admin activo.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        return usuario, None

# ===============================================
# CATÁLOGO DE VEHÍCULOS
# ===============================================

class CatalogoVehiculosView(APIView):
    """GET /api/cliente/vehiculos/"""
    permission_classes = [] # El catálogo puede ser público para visitantes

    def get(self, request):
        # Solo mostrar vehículos disponibles
        qs = Vehiculo.objects.filter(estado='disponible').order_by('tarifa_diaria')
        
        # Filtros opcionales
        marca = request.query_params.get('marca')
        tipo = request.query_params.get('tipo_combustible')
        transmision = request.query_params.get('transmision')
        es_premium = request.query_params.get('es_premium')
        
        if marca:
            qs = qs.filter(marca__iexact=marca)
        if tipo:
            qs = qs.filter(tipo_combustible=tipo)
        if transmision:
            qs = qs.filter(transmision=transmision)
        if es_premium is not None:
            qs = qs.filter(es_premium=es_premium.lower() == 'true')
            
        serializer = VehiculoResumenSerializer(qs, many=True)
        return Response({'total': qs.count(), 'vehiculos': serializer.data})


class DetalleVehiculoCatalogoView(APIView):
    """GET /api/cliente/vehiculos/<id>/"""
    permission_classes = [] 

    def get(self, request, pk):
        try:
            # Puedes ver detalles aunque no esté disponible, pero se mostrará su estado real
            vehiculo = Vehiculo.objects.get(pk=pk)
            return Response(VehiculoDetalleSerializer(vehiculo).data)
        except Vehiculo.DoesNotExist:
            return Response({'error': 'Vehículo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)


# ===============================================
# GESTIÓN DE RENTAS (RESERVAS)
# ===============================================

class MisRentalesView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/rentales/"""
    
    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        qs = Rental.objects.filter(cliente=cliente).order_by('-creado_en')
        estado = request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
            
        serializer = RentalResumenSerializer(qs, many=True)
        return Response({'total': qs.count(), 'rentales': serializer.data})


class CrearRentalView(ClienteRequiredMixin, APIView):
    """POST /api/cliente/rentales/crear/"""
    
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        # Opcional: Validar límite de rentas activas por cliente aquí
        
        serializer = CrearRentalSerializer(data=request.data)
        if serializer.is_valid():
            vehiculo = serializer.validated_data['vehiculo']
            f_inicio = serializer.validated_data['fecha_inicio']
            f_fin = serializer.validated_data['fecha_fin']
            
            # Calcular días
            diff = f_fin - f_inicio
            dias = diff.days
            if diff.seconds > 0 or dias == 0:
                dias += 1
                
            costo_total = vehiculo.tarifa_diaria * dias
            
            # Para clientes nivel 'premium' o 'frecuente', se podría aplicar descuento si existen reglas
            # Esto se conectaría con la lógica de 'BeneficioNivel' si es necesario
            
            # Crear rental
            rental = serializer.save(
                cliente=cliente,
                tarifa_diaria=vehiculo.tarifa_diaria,
                numero_dias=dias,
                costo_total=costo_total,
                estado='pendiente' # Queda pendiente hasta el pago
            )
            
            # Cambiar estado del vehículo: evitamos que otro lo rente mientras paga
            vehiculo.estado = 'reservado'
            vehiculo.save(update_fields=['estado'])
            
            return Response({
                'mensaje': 'Reserva creada con éxito. Falta completar el pago para confirmar.',
                'rental_id': rental.id,
                'costo_total': costo_total,
                'numero_dias': dias,
                'tarifa_diaria': vehiculo.tarifa_diaria
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DetalleMiRentalView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/rentales/<id>/"""
    
    def get(self, request, pk):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        try:
            rental = Rental.objects.get(pk=pk, cliente=cliente)
            return Response(RentalDetalleSerializer(rental).data)
        except Rental.DoesNotExist:
            return Response({'error': 'Rental no encontrada o no te pertenece.'}, status=status.HTTP_404_NOT_FOUND)


# ===============================================
# PAGOS
# ===============================================

class IniciarPagoView(ClienteRequiredMixin, APIView):
    """POST /api/cliente/pagos/"""
    
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        serializer = CrearPagoSerializer(data=request.data)
        if serializer.is_valid():
            renta = serializer.validated_data['renta']
            
            # Verificar que la renta pertenezca al cliente
            if renta.cliente != cliente:
                return Response({'error': 'No puedes pagar una renta que no es tuya.'}, status=status.HTTP_403_FORBIDDEN)
                
            pago = serializer.save(estado='completado') # Simulando un pago exitoso directo por ahora
            
            # Actualizar renta a confirmada
            renta.estado = 'confirmada'
            renta.save(update_fields=['estado'])
            
            # Auto-generar factura si no existe
            if not hasattr(renta, 'factura'):
                import uuid
                from decimal import Decimal
                subtotal = renta.costo_total
                iva = subtotal * Decimal('0.16')
                Factura.objects.create(
                    renta=renta,
                    numero_factura=f"FAC-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}",
                    subtotal=subtotal,
                    impuesto_iva=iva,
                    descuento=renta.descuento_aplicado,
                    total=pago.monto
                )
                
            # Generar notificacion para el usuario
            Notificacion.objects.create(
                usuario=cliente,
                titulo='Pago Confirmado',
                mensaje=f'Tu pago de ${pago.monto} ha sido procesado exitosamente. Tu reserva está confirmada.',
                tipo='pago',
                renta=renta,
                pago=pago
            )
            
            return Response({
                'mensaje': 'Pago procesado exitosamente. Tu reserva esta confirmada.',
                'pago': PagoSerializer(pago).data
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===============================================
# DOCUMENTOS
# ===============================================

class MisDocumentosView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/documentos/ y POST /api/cliente/documentos/"""
    
    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        qs = DocumentoUsuario.objects.filter(usuario=cliente).order_by('-creado_en')
        serializer = DocumentoUsuarioSerializer(qs, many=True)
        return Response({'documentos': serializer.data})
        
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        serializer = DocumentoUsuarioSerializer(data=request.data)
        if serializer.is_valid():
            doc = serializer.save(usuario=cliente, verificado=False)
            return Response({'mensaje': 'Documento subido correctamente.', 'documento': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===============================================
# TICKETS DE SOPORTE
# ===============================================

class MisTicketsView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/tickets/ y POST /api/cliente/tickets/"""
    
    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        qs = TicketSoporte.objects.filter(usuario=cliente).order_by('-creado_en')
        serializer = TicketSoporteSerializer(qs, many=True)
        return Response({'tickets': serializer.data})
        
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        serializer = TicketSoporteSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save(usuario=cliente, estado='abierto')
            return Response({'mensaje': 'Ticket creado exitosamente.', 'ticket': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===============================================
# RESEÑAS
# ===============================================

class CrearResenaVehiculoView(ClienteRequiredMixin, APIView):
    """POST /api/cliente/resenas/vehiculos/"""
    
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        # El serializer ResenaVehiculoSerializer verifica que el usuario haya rentado y valida contexto
        # Necesitamos pasar el request en el contexto para validar
        serializer = ResenaVehiculoSerializer(data=request.data, context={'request': request})
        
        # Hack menor para inyectar el user en el request objetively
        request.user_obj = cliente 
        
        if serializer.is_valid():
            resena = serializer.save(usuario=cliente)
            return Response({'mensaje': 'Gracias por tu reseña.', 'resena': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CrearResenaChoferView(ClienteRequiredMixin, APIView):
    """POST /api/cliente/resenas/choferes/"""
    
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        chofer_id = request.data.get('chofer')
        renta_id = request.data.get('renta')
        
        # Validar si el cliente realmente fue transportado por este chofer
        if not Rental.objects.filter(cliente=cliente, chofer_id=chofer_id, id=renta_id, estado='completada').exists():
            return Response({'error': 'Solo puedes reseñar a un chofer con el que hayas completado un viaje.'}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = ResenaChoferSerializer(data=request.data)
        if serializer.is_valid():
            # Actualizar promedio del chofer
            chofer = Usuario.objects.get(id=chofer_id)
            chofer.numero_evaluaciones_chofer += 1
            chofer.calificacion_chofer = ((chofer.calificacion_chofer * (chofer.numero_evaluaciones_chofer - 1)) + serializer.validated_data['calificacion']) / chofer.numero_evaluaciones_chofer
            chofer.save(update_fields=['numero_evaluaciones_chofer', 'calificacion_chofer'])
            
            resena = serializer.save(cliente=cliente)
            return Response({'mensaje': 'Reseña de chofer guardada exitosamente.', 'resena': serializer.data}, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===============================================
# PROMOCIONES
# ===============================================

class ValidarPromocionView(ClienteRequiredMixin, APIView):
    """POST /api/cliente/promociones/validar/"""
    
    def post(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        serializer = ValidarPromocionSerializer(data=request.data)
        if serializer.is_valid():
            codigo = serializer.validated_data['codigo_promocion']
            monto_renta = serializer.validated_data['monto_renta']
            
            try:
                promocion = Promocion.objects.get(codigo_promocion=codigo)
            except Promocion.DoesNotExist:
                return Response({'error': 'Código promocional inválido o no existe.'}, status=status.HTTP_404_NOT_FOUND)
                
            if not promocion.activa or promocion.fecha_fin < timezone.now().date() or promocion.fecha_inicio > timezone.now().date():
                return Response({'error': 'Esta promoción expiró o no está activa.'}, status=status.HTTP_400_BAD_REQUEST)
                
            if promocion.usos_maximos and promocion.usos_actuales >= promocion.usos_maximos:
                return Response({'error': 'Esta promoción ha alcanzado su límite de usos.'}, status=status.HTTP_400_BAD_REQUEST)
                
            if promocion.minimo_monto and monto_renta < promocion.minimo_monto:
                return Response({'error': f'El monto mínimo para usar este código es ${promocion.minimo_monto}.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Calcular descuento
            descuento = 0
            if promocion.tipo_descuento == 'fijo':
                descuento = promocion.valor_descuento
            else: # porcentaje
                descuento = (monto_renta * promocion.valor_descuento) / 100
                if promocion.maximo_descuento and descuento > promocion.maximo_descuento:
                    descuento = promocion.maximo_descuento
                    
            return Response({
                'mensaje': 'Promoción válida.',
                'descuento_aplicable': descuento,
                'codigo': promocion.codigo_promocion,
                'descripcion': promocion.descripcion
            })
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ===============================================
# SEGUIMIENTO GPS
# ===============================================

class SeguimientoGPSChoferView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/rentales/<id>/gps/"""
    
    def get(self, request, pk):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        try:
            rental = Rental.objects.get(pk=pk, cliente=cliente)
        except Rental.DoesNotExist:
            return Response({'error': 'Renta no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            
        if rental.estado not in ['confirmada', 'en_curso']:
            return Response({'error': 'Solo puedes seguir el GPS de rentas activas o confirmadas.'}, status=status.HTTP_400_BAD_REQUEST)
            
        gps_data = SeguimientoGPS.objects.filter(renta=rental).order_by('-timestamp_ubicacion').first()
        
        if not gps_data:
            return Response({'mensaje': 'El chofer aún no ha reportado su ubicación.', 'gps': None})
            
        return Response({
            'mensaje': 'Última ubicación encontrada.',
            'gps': SeguimientoGPSSerializer(gps_data).data
        })


# ===============================================
# FACTURAS
# ===============================================

class MisFacturasView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/facturas/"""
    
    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        qs = Factura.objects.filter(renta__cliente=cliente).order_by('-fecha_emision')
        serializer = FacturaSerializer(qs, many=True)
        return Response({'facturas': serializer.data})


# ===============================================
# NOTIFICACIONES
# ===============================================

class MisNotificacionesView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/notificaciones/"""
    
    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        # Traer ultimas 50 notificaciones
        qs = Notificacion.objects.filter(usuario=cliente).order_by('-creado_en')[:50]
        
        # Marcar como leidas si se envia el parametro
        if request.query_params.get('marcar_leidas') == 'true':
            Notificacion.objects.filter(usuario=cliente, leida=False).update(leida=True, leido_en=timezone.now())
            
        serializer = NotificacionSerializer(qs, many=True)
        return Response({'notificaciones': serializer.data})


# ===============================================
# PROGRAMA DE LEALTAD / NIVELES
# ===============================================

class MiNivelView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/nivel/"""
    
    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error
        
        # Obtener beneficios actuales y siguiente nivel
        from .models import BeneficioNivel
        from .serializers import BeneficioNivelSerializer
        
        beneficios = BeneficioNivel.objects.filter(nivel=cliente.nivel_usuario).first()
        
        # Lógica de progreso (simplificada)
        proximo_nivel = 'frecuente' if cliente.nivel_usuario == 'normal' else 'premium' if cliente.nivel_usuario == 'frecuente' else 'ejecutivo' if cliente.nivel_usuario == 'premium' else None
        requisitos = BeneficioNivel.objects.filter(nivel=proximo_nivel).first() if proximo_nivel else None
        
        return Response({
            'nivel_actual': cliente.nivel_usuario,
            'nivel_display': cliente.get_nivel_usuario_display(),
            'puntos': cliente.puntos_acumulados,
            'total_rentales': cliente.total_rentales,
            'beneficios_actuales': BeneficioNivelSerializer(beneficios).data if beneficios else None,
            'proximo_nivel': {
                'nombre': proximo_nivel,
                'requisitos': {
                    'puntos': requisitos.requisitos_puntos if requisitos else 0,
                    'rentales': requisitos.requisitos_rentales if requisitos else 0
                }
            } if proximo_nivel else None
        })


class ListaPromocionesView(APIView):
    """GET /api/cliente/promociones/"""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            # Solo mostrar promociones activas y que no hayan vencido
            # Import inline to avoid issues
            from django.utils import timezone
            hoy = timezone.localdate()
            
            qs = Promocion.objects.filter(
                activa=True,
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy
            ).order_by('-fecha_fin')
            
            promos = []
            for p in qs:
                promos.append({
                    'id': p.id,
                    'codigo': p.codigo_promocion,
                    'descripcion': p.descripcion or '',
                    'tipo': p.tipo_descuento,
                    'valor': float(p.valor_descuento) if p.valor_descuento else 0.0,
                    'vence': p.fecha_fin
                })
                
            return Response({'total': len(promos), 'promociones': promos})
        except Exception as e:
            print(f"ERROR en ListaPromocionesView: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListaFacturasView(ClienteRequiredMixin, APIView):
    """GET /api/cliente/facturas/"""

    def get(self, request):
        cliente, error = self.get_cliente(request)
        if error: return error

        # Obtener facturas asociadas a los rentales de este cliente
        qs = Factura.objects.filter(pago__rental__cliente=cliente).order_by('-fecha_emision')
        
        data = []
        for f in qs:
            data.append({
                'id': f.id,
                'numero': f.numero_factura,
                'fecha': f.fecha_emision,
                'total': float(f.monto_total),
                'estado': f.estado,
                'rental_uuid': f.pago.rental.uuid,
                'pdf_url': f.archivo_pdf.url if f.archivo_pdf else None
            })

        return Response({'total': len(data), 'facturas': data})

