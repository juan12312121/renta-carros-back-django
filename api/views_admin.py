# -*- coding: utf-8 -*-
"""
Views del Administrador - Sistema de Renta de Carros
Endpoints para gestion completa: usuarios, vehiculos, rentales, pagos, soporte, estadisticas
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.db import transaction
from datetime import date, timedelta

from .models import (
    Usuario, Vehiculo, Rental, Pago, Factura,
    MantenimientoVehiculo, TicketSoporte, Notificacion,
    DocumentoUsuario, HistorialAuditoria, Promocion,
    UsoPromocion, EstadisticaDiaria, BeneficioNivel,
    ResenaVehiculo, ResenaChofer,
)
from .serializers import (
    AdminUsuarioSerializer,
    AdminVehiculoSerializer as VehiculoSerializer,
    RentalDetalleSerializer as RentalSerializer,
    PagoSerializer,
    TicketSoporteSerializer,
    PromocionSerializer,
    NotificacionSerializer,
    DocumentoUsuarioSerializer,
)


# ===============================================
# MIXIN BASE PARA ADMIN
# ===============================================

class AdminRequiredMixin:
    permission_classes = []

    def get_admin(self, request):
        from .authentication import JWTAuthentication
        usuario, error = JWTAuthentication.obtener_usuario_de_request(request)
        if error:
            return None, error
        if usuario.role != 'admin':
            return None, Response(
                {'error': 'Acceso denegado. Se requiere rol de administrador.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return usuario, None

    def registrar_auditoria(self, admin, tabla, registro_id, accion,
                             datos_anteriores=None, datos_nuevos=None, request=None):
        ip = None
        if request:
            ip = request.META.get('REMOTE_ADDR')
        HistorialAuditoria.objects.create(
            usuario=admin,
            tabla_afectada=tabla,
            registro_id=registro_id,
            accion=accion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            direccion_ip=ip,
        )


# ===============================================
# DASHBOARD
# ===============================================

class AdminDashboardView(AdminRequiredMixin, APIView):
    """GET /api/admin/dashboard/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        hoy = date.today()
        hace_30_dias = hoy - timedelta(days=30)
        hace_7_dias = hoy - timedelta(days=7)

        total_clientes = Usuario.objects.filter(role='cliente', activo=True).count()
        total_choferes = Usuario.objects.filter(role='chofer', activo=True).count()
        nuevos_clientes_mes = Usuario.objects.filter(role='cliente', creado_en__date__gte=hace_30_dias).count()
        choferes_pendientes = Usuario.objects.filter(role='chofer', verificado=False, activo=True).count()

        vehiculos_disponibles = Vehiculo.objects.filter(estado='disponible').count()
        vehiculos_ocupados = Vehiculo.objects.filter(estado='ocupado').count()
        vehiculos_mantenimiento = Vehiculo.objects.filter(estado='mantenimiento').count()
        total_vehiculos = Vehiculo.objects.count()

        rentales_activas = Rental.objects.filter(estado='en_curso').count()
        rentales_pendientes = Rental.objects.filter(estado='pendiente').count()
        rentales_mes = Rental.objects.filter(creado_en__date__gte=hace_30_dias).count()
        rentales_semana = Rental.objects.filter(creado_en__date__gte=hace_7_dias).count()

        ingresos_mes = Pago.objects.filter(
            estado='completado', creado_en__date__gte=hace_30_dias
        ).aggregate(total=Sum('monto'))['total'] or 0

        ingresos_semana = Pago.objects.filter(
            estado='completado', creado_en__date__gte=hace_7_dias
        ).aggregate(total=Sum('monto'))['total'] or 0

        pagos_pendientes = Pago.objects.filter(estado='pendiente').count()
        tickets_abiertos = TicketSoporte.objects.filter(estado='abierto').count()
        tickets_urgentes = TicketSoporte.objects.filter(
            estado__in=['abierto', 'en_proceso'], prioridad='urgente'
        ).count()

        return Response({
            'usuarios': {
                'total_clientes': total_clientes,
                'total_choferes': total_choferes,
                'nuevos_clientes_mes': nuevos_clientes_mes,
                'choferes_pendientes_verificacion': choferes_pendientes,
            },
            'vehiculos': {
                'total': total_vehiculos,
                'disponibles': vehiculos_disponibles,
                'ocupados': vehiculos_ocupados,
                'en_mantenimiento': vehiculos_mantenimiento,
            },
            'rentales': {
                'activas': rentales_activas,
                'pendientes_confirmacion': rentales_pendientes,
                'este_mes': rentales_mes,
                'esta_semana': rentales_semana,
            },
            'finanzas': {
                'ingresos_mes': float(ingresos_mes),
                'ingresos_semana': float(ingresos_semana),
                'pagos_pendientes': pagos_pendientes,
            },
            'soporte': {
                'tickets_abiertos': tickets_abiertos,
                'tickets_urgentes': tickets_urgentes,
            },
            'generado_en': timezone.now(),
        })


# ===============================================
# GESTION DE USUARIOS
# ===============================================

class AdminListaUsuariosView(AdminRequiredMixin, APIView):
    """GET /api/admin/usuarios/?role=cliente&activo=true&search=juan"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = Usuario.objects.all().order_by('-creado_en')
        role = request.query_params.get('role')
        activo = request.query_params.get('activo')
        search = request.query_params.get('search')
        verificado = request.query_params.get('verificado')

        if role:
            qs = qs.filter(role=role)
        if activo is not None:
            qs = qs.filter(activo=activo.lower() == 'true')
        if verificado is not None:
            qs = qs.filter(verificado=verificado.lower() == 'true')
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )

        serializer = AdminUsuarioSerializer(qs, many=True)
        return Response({'total': qs.count(), 'usuarios': serializer.data})

    def post(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        from django.contrib.auth.hashers import make_password
        data = request.data.copy()
        
        # Generar username si no viene
        if not data.get('username'):
            data['username'] = data.get('email').split('@')[0]
        
        # Hashear password
        if 'password' in data:
            data['password_hash'] = make_password(data.pop('password'))
        
        serializer = AdminUsuarioSerializer(data=data)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response({
                'mensaje': 'Usuario creado exitosamente.',
                'usuario': AdminUsuarioSerializer(usuario).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDetalleUsuarioView(AdminRequiredMixin, APIView):
    """GET/PATCH/DELETE /api/admin/usuarios/<id>/"""

    def get_usuario(self, pk):
        try:
            return Usuario.objects.get(pk=pk), None
        except Usuario.DoesNotExist:
            return None, Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        usuario, error = self.get_usuario(pk)
        if error:
            return error

        rentales = Rental.objects.filter(
            Q(cliente=usuario) | Q(chofer=usuario)
        ).order_by('-creado_en')[:10]

        return Response({
            'usuario': AdminUsuarioSerializer(usuario).data,
            'ultimas_rentales': RentalSerializer(rentales, many=True).data,
        })

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        usuario, error = self.get_usuario(pk)
        if error:
            return error

        datos_anteriores = AdminUsuarioSerializer(usuario).data
        serializer = AdminUsuarioSerializer(usuario, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            self.registrar_auditoria(admin, 'usuarios', pk, 'UPDATE',
                                     dict(datos_anteriores), serializer.data, request)
            return Response({'mensaje': 'Usuario actualizado.', 'usuario': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        usuario, error = self.get_usuario(pk)
        if error:
            return error

        if usuario.role == 'admin':
            return Response(
                {'error': 'No puedes desactivar a otro administrador.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario.activo = False
        usuario.save(update_fields=['activo'])
        self.registrar_auditoria(admin, 'usuarios', pk, 'DELETE', request=request)
        return Response({'mensaje': f'Usuario {usuario.get_nombre_completo()} desactivado.'})


class AdminVerificarChoferView(AdminRequiredMixin, APIView):
    """POST /api/admin/usuarios/<id>/verificar/"""

    def post(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error

        try:
            chofer = Usuario.objects.get(pk=pk, role='chofer')
        except Usuario.DoesNotExist:
            return Response({'error': 'Chofer no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        verificado = request.data.get('verificado', True)
        chofer.verificado = verificado
        chofer.activo_chofer = verificado
        chofer.save(update_fields=['verificado', 'activo_chofer'])

        Notificacion.objects.create(
            usuario=chofer,
            titulo='Verificacion de cuenta' if verificado else 'Cuenta no verificada',
            mensaje='Tu cuenta ha sido verificada. Ya puedes recibir asignaciones.' if verificado
                    else f'Tu cuenta no fue verificada. Razon: {request.data.get("razon", "Sin especificar")}',
            tipo='verificacion',
        )

        self.registrar_auditoria(admin, 'usuarios', pk, 'UPDATE',
                                 request=request, datos_nuevos={'verificado': verificado})

        return Response({
            'mensaje': f'Chofer {"verificado" if verificado else "rechazado"} exitosamente.',
            'chofer': chofer.get_nombre_completo(),
            'verificado': verificado,
        })


# ===============================================
# GESTION DE VEHICULOS
# ===============================================

class AdminListaVehiculosView(AdminRequiredMixin, APIView):
    """GET /api/admin/vehiculos/ y POST /api/admin/vehiculos/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = Vehiculo.objects.select_related('propietario').exclude(estado='baja')
        estado = request.query_params.get('estado')
        es_premium = request.query_params.get('es_premium')
        search = request.query_params.get('search')

        if estado:
            qs = qs.filter(estado=estado)
        if es_premium is not None:
            qs = qs.filter(es_premium=es_premium.lower() == 'true')
        if search:
            qs = qs.filter(
                Q(marca__icontains=search) |
                Q(modelo__icontains=search) |
                Q(placa__icontains=search)
            )

        serializer = VehiculoSerializer(qs, many=True)
        return Response({'total': qs.count(), 'vehiculos': serializer.data})

    def post(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        serializer = VehiculoSerializer(data=request.data)
        if serializer.is_valid():
            vehiculo = serializer.save()
            self.registrar_auditoria(admin, 'vehiculos', vehiculo.id, 'INSERT',
                                     datos_nuevos=serializer.data, request=request)
            return Response({'mensaje': 'Vehiculo creado.', 'vehiculo': serializer.data},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDetalleVehiculoView(AdminRequiredMixin, APIView):
    """GET/PATCH/DELETE /api/admin/vehiculos/<id>/"""

    def get_vehiculo(self, pk):
        try:
            return Vehiculo.objects.get(pk=pk), None
        except Vehiculo.DoesNotExist:
            return None, Response({'error': 'Vehiculo no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        vehiculo, error = self.get_vehiculo(pk)
        if error:
            return error

        mantenimientos = MantenimientoVehiculo.objects.filter(
            vehiculo=vehiculo).order_by('-fecha_mantenimiento')[:5]
        resenas = ResenaVehiculo.objects.filter(vehiculo=vehiculo).order_by('-creado_en')[:5]
        rentales_count = Rental.objects.filter(vehiculo=vehiculo).count()

        return Response({
            'vehiculo': VehiculoSerializer(vehiculo).data,
            'ultimos_mantenimientos': [
                {
                    'tipo': m.tipo_mantenimiento,
                    'fecha': m.fecha_mantenimiento,
                    'costo': m.costo,
                    'proximo': m.fecha_proximo_mantenimiento,
                } for m in mantenimientos
            ],
            'calificacion_promedio': resenas.aggregate(prom=Avg('calificacion'))['prom'],
            'total_rentales': rentales_count,
            'ultimas_resenas': [
                {'calificacion': r.calificacion, 'comentario': r.comentario} for r in resenas
            ],
        })

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        vehiculo, error = self.get_vehiculo(pk)
        if error:
            return error

        datos_anteriores = VehiculoSerializer(vehiculo).data
        serializer = VehiculoSerializer(vehiculo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            self.registrar_auditoria(admin, 'vehiculos', pk, 'UPDATE',
                                     dict(datos_anteriores), serializer.data, request)
            return Response({'mensaje': 'Vehiculo actualizado.', 'vehiculo': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        vehiculo, error = self.get_vehiculo(pk)
        if error:
            return error

        try:
            # Intentar borrado físico
            placa = vehiculo.placa
            vehiculo.delete()
            self.registrar_auditoria(admin, 'vehiculos', pk, 'DELETE', request=request)
            return Response({'mensaje': f'Vehiculo {placa} eliminado permanentemente.'})
        except Exception:
            # Si hay rentales u otros vínculos, hacer borrado lógico (baja)
            vehiculo.estado = 'baja'
            vehiculo.save(update_fields=['estado'])
            self.registrar_auditoria(admin, 'vehiculos', pk, 'DELETE_SOFT', request=request)
            return Response({'mensaje': f'Vehiculo {vehiculo.placa} dado de baja (no se puede borrar físicamente por tener registros asociados).'})


# ===============================================
# GESTION DE MANTENIMIENTOS
# ===============================================

class AdminListaMantenimientosView(AdminRequiredMixin, APIView):
    """GET/POST /api/admin/mantenimientos/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error: return error
        
        qs = MantenimientoVehiculo.objects.select_related('vehiculo').order_by('-fecha_mantenimiento')
        vehiculo_id = request.query_params.get('vehiculo')
        if vehiculo_id:
            qs = qs.filter(vehiculo_id=vehiculo_id)
            
        from .serializers import MantenimientoVehiculoSerializer
        serializer = MantenimientoVehiculoSerializer(qs, many=True)
        
        # Estadísticas básicas
        total_costo = qs.aggregate(total=Sum('costo'))['total'] or 0
        conteo = qs.count()
        preventivos = qs.filter(tipo_mantenimiento='preventivo').count()
        correctivos = qs.filter(tipo_mantenimiento='correctivo').count()

        return Response({
            'total': conteo,
            'total_invertido': total_costo,
            'preventivos': preventivos,
            'correctivos': correctivos,
            'mantenimientos': serializer.data
        })

    def post(self, request):
        admin, error = self.get_admin(request)
        if error: return error
        
        from .serializers import MantenimientoVehiculoSerializer
        serializer = MantenimientoVehiculoSerializer(data=request.data)
        if serializer.is_valid():
            mantenimiento = serializer.save()
            
            # Cambiar estado del vehiculo a mantenimiento si el parametro existe
            if str(request.data.get('poner_en_mantenimiento', '')).lower() == 'true':
                mantenimiento.vehiculo.estado = 'mantenimiento'
                mantenimiento.vehiculo.save(update_fields=['estado'])
                
            self.registrar_auditoria(admin, 'mantenimiento_vehiculos', mantenimiento.id, 'INSERT',
                                     datos_nuevos=serializer.data, request=request)
            return Response({'mensaje': 'Mantenimiento registrado.', 'mantenimiento': serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminDetalleMantenimientoView(AdminRequiredMixin, APIView):
    """PATCH/DELETE /api/admin/mantenimientos/<id>/"""

    def get_object(self, pk):
        try:
            return MantenimientoVehiculo.objects.get(pk=pk), None
        except MantenimientoVehiculo.DoesNotExist:
            return None, Response({'error': 'Registro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error: return error
        obj, error = self.get_object(pk)
        if error: return error

        from .serializers import MantenimientoVehiculoSerializer
        serializer = MantenimientoVehiculoSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            self.registrar_auditoria(admin, 'mantenimiento_vehiculos', pk, 'UPDATE', 
                                     datos_nuevos=serializer.data, request=request)
            return Response({'mensaje': 'Registro actualizado.', 'mantenimiento': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        admin, error = self.get_admin(request)
        if error: return error
        obj, error = self.get_object(pk)
        if error: return error

        obj.delete()
        self.registrar_auditoria(admin, 'mantenimiento_vehiculos', pk, 'DELETE', request=request)
        return Response({'mensaje': 'Registro eliminado.'})


# ===============================================
# GESTION DE RENTALES
# ===============================================

class AdminListaRentalesView(AdminRequiredMixin, APIView):
    """GET /api/admin/rentales/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = Rental.objects.select_related('cliente', 'vehiculo', 'chofer').order_by('-creado_en')
        estado = request.query_params.get('estado')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        cliente_id = request.query_params.get('cliente_id')
        chofer_id = request.query_params.get('chofer_id')

        if estado:
            qs = qs.filter(estado=estado)
        if fecha_inicio:
            qs = qs.filter(fecha_inicio__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha_fin__date__lte=fecha_fin)
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if chofer_id:
            qs = qs.filter(chofer_id=chofer_id)

        serializer = RentalSerializer(qs, many=True)
        return Response({'total': qs.count(), 'rentales': serializer.data})


class AdminDetalleRentalView(AdminRequiredMixin, APIView):
    """GET/PATCH /api/admin/rentales/<id>/"""

    def get_rental(self, pk):
        try:
            return Rental.objects.select_related('cliente', 'vehiculo', 'chofer').get(pk=pk), None
        except Rental.DoesNotExist:
            return None, Response({'error': 'Rental no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        rental, error = self.get_rental(pk)
        if error:
            return error

        pago = None
        try:
            pago = PagoSerializer(rental.pago).data
        except Exception:
            pass

        return Response({'rental': RentalSerializer(rental).data, 'pago': pago})

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        rental, error = self.get_rental(pk)
        if error:
            return error

        datos_anteriores = RentalSerializer(rental).data
        serializer = RentalSerializer(rental, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            nuevo_estado = request.data.get('estado')
            if nuevo_estado and nuevo_estado != datos_anteriores.get('estado'):
                mensajes = {
                    'confirmada': 'Tu renta ha sido confirmada.',
                    'en_curso': 'Tu renta esta en curso. Buen viaje!',
                    'completada': 'Tu renta ha sido completada. Gracias por usar nuestro servicio.',
                    'cancelada': 'Tu renta ha sido cancelada.',
                }
                if nuevo_estado in mensajes:
                    Notificacion.objects.create(
                        usuario=rental.cliente,
                        titulo=f'Renta #{rental.id} - {nuevo_estado.replace("_", " ").title()}',
                        mensaje=mensajes[nuevo_estado],
                        tipo='rental',
                        renta=rental,
                    )

            self.registrar_auditoria(admin, 'rentales', pk, 'UPDATE',
                                     dict(datos_anteriores), serializer.data, request)
            return Response({'mensaje': 'Rental actualizada.', 'rental': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminAsignarChoferView(AdminRequiredMixin, APIView):
    """POST /api/admin/rentales/<id>/asignar-chofer/"""

    def post(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error

        try:
            rental = Rental.objects.get(pk=pk)
        except Rental.DoesNotExist:
            return Response({'error': 'Rental no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        chofer_id = request.data.get('chofer_id')
        if not chofer_id:
            return Response({'error': 'Se requiere chofer_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chofer = Usuario.objects.get(pk=chofer_id, role='chofer', verificado=True, activo=True)
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Chofer no encontrado o no verificado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        rental.chofer = chofer
        rental.save(update_fields=['chofer'])

        Notificacion.objects.create(
            usuario=chofer,
            titulo='Nueva asignacion',
            mensaje=f'Se te ha asignado la renta #{rental.id}. Cliente: {rental.cliente.get_nombre_completo()}.',
            tipo='asignacion',
            renta=rental,
        )

        return Response({
            'mensaje': f'Chofer {chofer.get_nombre_completo()} asignado a renta #{rental.id}.',
        })


# ===============================================
# GESTION DE PAGOS
# ===============================================

class AdminListaPagosView(AdminRequiredMixin, APIView):
    """GET /api/admin/pagos/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = Pago.objects.select_related('renta').order_by('-creado_en')
        estado = request.query_params.get('estado')
        metodo = request.query_params.get('metodo')

        if estado:
            qs = qs.filter(estado=estado)
        if metodo:
            qs = qs.filter(metodo_pago=metodo)

        total_monto = qs.filter(estado='completado').aggregate(total=Sum('monto'))['total'] or 0

        serializer = PagoSerializer(qs, many=True)
        return Response({
            'total_registros': qs.count(),
            'total_cobrado': float(total_monto),
            'pagos': serializer.data,
        })


class AdminActualizarPagoView(AdminRequiredMixin, APIView):
    """PATCH /api/admin/pagos/<id>/"""

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error

        try:
            pago = Pago.objects.select_related('renta__cliente').get(pk=pk)
        except Pago.DoesNotExist:
            return Response({'error': 'Pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        nuevo_estado = request.data.get('estado')
        notas = request.data.get('notas', '')

        estados_validos = ['pendiente', 'procesando', 'completado', 'fallido', 'reembolsado']
        if nuevo_estado and nuevo_estado not in estados_validos:
            return Response(
                {'error': f'Estado invalido. Opciones: {estados_validos}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            if nuevo_estado:
                pago.estado = nuevo_estado
                if nuevo_estado == 'completado':
                    pago.procesado_en = timezone.now()
                    if pago.renta.estado == 'pendiente':
                        pago.renta.estado = 'confirmada'
                        pago.renta.save(update_fields=['estado'])
                        
                    # Auto-generar factura
                    if not hasattr(pago.renta, 'factura'):
                        import uuid
                        from decimal import Decimal
                        subtotal = pago.renta.costo_total
                        iva = subtotal * Decimal('0.16') # IVA 16%
                        Factura.objects.create(
                            renta=pago.renta,
                            numero_factura=f"FAC-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}",
                            subtotal=subtotal,
                            impuesto_iva=iva,
                            descuento=pago.renta.descuento_aplicado,
                            total=pago.monto
                        )
            if notas:
                pago.notas = notas
            pago.save()

            if nuevo_estado in ['completado', 'fallido', 'reembolsado']:
                mensajes = {
                    'completado': f'Tu pago de ${pago.monto} fue confirmado.',
                    'fallido': f'Tu pago de ${pago.monto} no pudo procesarse.',
                    'reembolsado': f'Se realizo un reembolso de ${pago.monto} a tu cuenta.',
                }
                Notificacion.objects.create(
                    usuario=pago.renta.cliente,
                    titulo=f'Pago #{pago.id} - {nuevo_estado}',
                    mensaje=mensajes[nuevo_estado],
                    tipo='pago',
                    pago=pago,
                    renta=pago.renta,
                )

        return Response({
            'mensaje': f'Pago actualizado a "{nuevo_estado}".',
            'pago': PagoSerializer(pago).data,
        })


# ===============================================
# GESTION DE TICKETS DE SOPORTE
# ===============================================

class AdminListaTicketsView(AdminRequiredMixin, APIView):
    """GET /api/admin/tickets/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = TicketSoporte.objects.select_related('usuario', 'asignado_a').order_by('-prioridad', '-creado_en')
        estado = request.query_params.get('estado')
        prioridad = request.query_params.get('prioridad')

        if estado:
            qs = qs.filter(estado=estado)
        if prioridad:
            qs = qs.filter(prioridad=prioridad)

        serializer = TicketSoporteSerializer(qs, many=True)
        return Response({'total': qs.count(), 'tickets': serializer.data})


class AdminDetalleTicketView(AdminRequiredMixin, APIView):
    """GET/PATCH /api/admin/tickets/<id>/"""

    def get_ticket(self, pk):
        try:
            return TicketSoporte.objects.select_related('usuario', 'asignado_a').get(pk=pk), None
        except TicketSoporte.DoesNotExist:
            return None, Response({'error': 'Ticket no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        ticket, error = self.get_ticket(pk)
        if error:
            return error
        return Response(TicketSoporteSerializer(ticket).data)

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        ticket, error = self.get_ticket(pk)
        if error:
            return error

        nuevo_estado = request.data.get('estado')
        notas_internas = request.data.get('notas_internas')
        asignar_a = request.data.get('asignado_a')

        if nuevo_estado:
            ticket.estado = nuevo_estado
            if nuevo_estado == 'cerrado':
                ticket.cerrado_en = timezone.now()
        if notas_internas:
            ticket.notas_internas = notas_internas
        if asignar_a:
            ticket.asignado_a_id = asignar_a

        ticket.save()

        if nuevo_estado in ['resuelto', 'cerrado']:
            Notificacion.objects.create(
                usuario=ticket.usuario,
                titulo=f'Ticket #{ticket.id} {nuevo_estado}',
                mensaje=f'Tu ticket "{ticket.titulo}" ha sido {nuevo_estado}.',
                tipo='soporte',
            )

        return Response({'mensaje': 'Ticket actualizado.', 'ticket': TicketSoporteSerializer(ticket).data})


# ===============================================
# GESTION DE PROMOCIONES
# ===============================================

class AdminListaPromocionesView(AdminRequiredMixin, APIView):
    """GET/POST /api/admin/promociones/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = Promocion.objects.all().order_by('-fecha_fin')
        activa = request.query_params.get('activa')
        if activa is not None:
            qs = qs.filter(activa=activa.lower() == 'true')

        serializer = PromocionSerializer(qs, many=True)
        return Response({'total': qs.count(), 'promociones': serializer.data})

    def post(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        serializer = PromocionSerializer(data=request.data)
        if serializer.is_valid():
            promocion = serializer.save()
            self.registrar_auditoria(admin, 'promociones', promocion.id, 'INSERT',
                                     datos_nuevos=serializer.data, request=request)
            return Response({'mensaje': 'Promocion creada.', 'promocion': serializer.data},
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDetallePromocionView(AdminRequiredMixin, APIView):
    """GET/PATCH/DELETE /api/admin/promociones/<id>/"""

    def get_promocion(self, pk):
        try:
            return Promocion.objects.get(pk=pk), None
        except Promocion.DoesNotExist:
            return None, Response({'error': 'Promocion no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        promocion, error = self.get_promocion(pk)
        if error:
            return error
        usos = UsoPromocion.objects.filter(promocion=promocion).count()
        return Response({**PromocionSerializer(promocion).data, 'usos_registrados': usos})

    def patch(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        promocion, error = self.get_promocion(pk)
        if error:
            return error

        serializer = PromocionSerializer(promocion, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'mensaje': 'Promocion actualizada.', 'promocion': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error
        promocion, error = self.get_promocion(pk)
        if error:
            return error

        promocion.activa = False
        promocion.save(update_fields=['activa'])
        return Response({'mensaje': f'Promocion "{promocion.codigo_promocion}" desactivada.'})


# ===============================================
# ESTADISTICAS Y REPORTES
# ===============================================

class AdminEstadisticasView(AdminRequiredMixin, APIView):
    """GET /api/admin/estadisticas/?periodo=30"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        dias = int(request.query_params.get('periodo', 30))
        fecha_inicio = date.today() - timedelta(days=dias)

        ingresos_por_dia = list(
            Pago.objects.filter(estado='completado', creado_en__date__gte=fecha_inicio)
            .extra(select={'dia': 'DATE(creado_en)'})
            .values('dia')
            .annotate(total=Sum('monto'), cantidad=Count('id'))
            .order_by('dia')
        )

        rentales_por_estado = list(
            Rental.objects.filter(creado_en__date__gte=fecha_inicio)
            .values('estado')
            .annotate(cantidad=Count('id'))
        )

        top_vehiculos = list(
            Rental.objects.filter(creado_en__date__gte=fecha_inicio)
            .values('vehiculo__marca', 'vehiculo__modelo', 'vehiculo__placa')
            .annotate(total_rentales=Count('id'), ingresos=Sum('costo_total'))
            .order_by('-total_rentales')[:5]
        )

        top_clientes = list(
            Rental.objects.filter(creado_en__date__gte=fecha_inicio)
            .values('cliente__nombre', 'cliente__apellido', 'cliente__email')
            .annotate(total_rentales=Count('id'), total_gastado=Sum('costo_total'))
            .order_by('-total_rentales')[:5]
        )

        metodos_pago = list(
            Pago.objects.filter(estado='completado', creado_en__date__gte=fecha_inicio)
            .values('metodo_pago')
            .annotate(cantidad=Count('id'), total=Sum('monto'))
            .order_by('-cantidad')
        )

        return Response({
            'periodo_dias': dias,
            'fecha_inicio': fecha_inicio,
            'ingresos_por_dia': ingresos_por_dia,
            'rentales_por_estado': rentales_por_estado,
            'top_vehiculos': top_vehiculos,
            'top_clientes': top_clientes,
            'metodos_pago': metodos_pago,
        })


# ===============================================
# VERIFICACION DE DOCUMENTOS
# ===============================================

class AdminDocumentosView(AdminRequiredMixin, APIView):
    """GET /api/admin/documentos/?verificado=false"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        qs = DocumentoUsuario.objects.select_related('usuario').order_by('-creado_en')
        verificado = request.query_params.get('verificado')
        if verificado is not None:
            qs = qs.filter(verificado=verificado.lower() == 'true')

        serializer = DocumentoUsuarioSerializer(qs, many=True)
        return Response({'total': qs.count(), 'documentos': serializer.data})


class AdminVerificarDocumentoView(AdminRequiredMixin, APIView):
    """POST /api/admin/documentos/<id>/verificar/"""

    def post(self, request, pk):
        admin, error = self.get_admin(request)
        if error:
            return error

        try:
            doc = DocumentoUsuario.objects.select_related('usuario').get(pk=pk)
        except DocumentoUsuario.DoesNotExist:
            return Response({'error': 'Documento no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        verificado = request.data.get('verificado', True)
        razon = request.data.get('razon_rechazo', '')

        doc.verificado = verificado
        doc.razon_rechazo = razon if not verificado else ''
        doc.save(update_fields=['verificado', 'razon_rechazo'])

        Notificacion.objects.create(
            usuario=doc.usuario,
            titulo='Documento verificado' if verificado else 'Documento rechazado',
            mensaje=f'Tu documento "{doc.nombre_documento}" fue {"aprobado" if verificado else f"rechazado: {razon}"}.',
            tipo='documento',
        )

        return Response({
            'mensaje': f'Documento {"verificado" if verificado else "rechazado"}.',
            'documento': doc.nombre_documento,
        })


# ===============================================
# NOTIFICACIONES MASIVAS
# ===============================================

class AdminEnviarNotificacionView(AdminRequiredMixin, APIView):
    """
    POST /api/admin/notificaciones/enviar/
    Body: { "titulo": "...", "mensaje": "...", "tipo": "general",
            "destinatarios": "todos" | "clientes" | "choferes" | [lista de ids] }
    """

    def post(self, request):
        admin, error = self.get_admin(request)
        if error:
            return error

        titulo = request.data.get('titulo')
        mensaje = request.data.get('mensaje')
        tipo = request.data.get('tipo', 'general')
        destinatarios = request.data.get('destinatarios', 'todos')

        if not titulo or not mensaje:
            return Response({'error': 'Se requieren titulo y mensaje.'}, status=status.HTTP_400_BAD_REQUEST)

        if destinatarios == 'todos':
            usuarios = Usuario.objects.filter(activo=True).exclude(role='admin')
        elif destinatarios == 'clientes':
            usuarios = Usuario.objects.filter(role='cliente', activo=True)
        elif destinatarios == 'choferes':
            usuarios = Usuario.objects.filter(role='chofer', activo=True)
        elif isinstance(destinatarios, list):
            usuarios = Usuario.objects.filter(id__in=destinatarios, activo=True)
        else:
            return Response({'error': 'destinatarios invalido.'}, status=status.HTTP_400_BAD_REQUEST)

        notificaciones = [
            Notificacion(usuario=u, titulo=titulo, mensaje=mensaje, tipo=tipo)
            for u in usuarios
        ]
        Notificacion.objects.bulk_create(notificaciones)

        return Response({
            'mensaje': f'Notificacion enviada a {len(notificaciones)} usuarios.',
            'total_enviados': len(notificaciones),
        })


# ===============================================
# AUDITORÍA
# ===============================================

class AdminAuditoriaView(AdminRequiredMixin, APIView):
    """GET /api/admin/auditoria/"""

    def get(self, request):
        admin, error = self.get_admin(request)
        if error: return error

        logs_objs = HistorialAuditoria.objects.select_related('usuario').all().order_by('-fecha_accion')
        
        # Filtros
        tabla = request.query_params.get('tabla')
        if tabla:
            logs_objs = logs_objs.filter(tabla_afectada=tabla)
            
        logs = []
        for log in logs_objs[:100]:
            logs.append({
                'id': log.id,
                'usuario_nombre': log.usuario.get_nombre_completo(),
                'tabla': log.tabla_afectada,
                'accion': log.accion,
                'fecha': log.fecha_accion,
                'ip': log.direccion_ip,
                'datos_anteriores': log.datos_anteriores,
                'datos_nuevos': log.datos_nuevos
            })

        return Response({'total': logs_objs.count(), 'logs': logs})