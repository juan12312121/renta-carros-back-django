"""
Serializers para el sistema de renta de carros
Incluye serializers para Cliente, Chofer y Admin
"""

from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from .models import (
    Usuario, Vehiculo, Rental, Pago, Factura,
    ResenaVehiculo, ResenaChofer, Notificacion,
    TicketSoporte, Promocion, BeneficioNivel,
    HistorialNivelUsuario, DocumentoUsuario,
    MantenimientoVehiculo, EstadisticaDiaria,
    SeguimientoGPS, UsoPromocion, HistorialAuditoria
)


# ===============================================
# SERIALIZERS DE AUTENTICACIÓN
# ===============================================

class RegistroClienteSerializer(serializers.ModelSerializer):
    """Serializer para registrar un cliente nuevo"""
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirmar contraseña")

    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'password', 'password2',
            'nombre', 'apellido', 'telefono'
        ]

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este email.")
        return value

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.password_hash = make_password(password)
        usuario.role = 'cliente'
        usuario.save()
        return usuario


class RegistroChoferSerializer(serializers.ModelSerializer):
    """Serializer para registrar un chofer"""
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Confirmar contraseña")

    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'password', 'password2',
            'nombre', 'apellido', 'telefono',
            'numero_licencia_conducir', 'vencimiento_licencia',
            'banco_nombre', 'cuenta_bancaria', 'tipo_cuenta', 'rfc_usuario'
        ]

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        if not data.get('numero_licencia_conducir'):
            raise serializers.ValidationError({"numero_licencia_conducir": "La licencia es obligatoria."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.password_hash = make_password(password)
        usuario.role = 'chofer'
        usuario.verificado = False  # Admin debe verificar
        usuario.save()
        return usuario


class RegistroAdminSerializer(serializers.ModelSerializer):
    """Serializer para registrar un nuevo administrador"""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = [
            'username', 'email', 'password',
            'nombre', 'apellido'
        ]

    def validate_email(self, value):
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está en uso.")
        return value

    def validate_username(self, value):
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.password_hash = make_password(password)
        usuario.role = 'admin'
        usuario.verificado = True
        usuario.activo = True
        usuario.save()
        return usuario


class LoginSerializer(serializers.Serializer):
    """Serializer para login (email + password)"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        try:
            usuario = Usuario.objects.get(email=email, activo=True)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Credenciales inválidas.")

        if not check_password(password, usuario.password_hash):
            raise serializers.ValidationError("Credenciales inválidas.")

        data['usuario'] = usuario
        return data


class CambiarPasswordSerializer(serializers.Serializer):
    """Serializer para cambiar contraseña"""
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, min_length=8)
    password_nuevo2 = serializers.CharField(write_only=True, label="Confirmar nueva contraseña")

    def validate(self, data):
        if data['password_nuevo'] != data['password_nuevo2']:
            raise serializers.ValidationError({"password_nuevo": "Las contraseñas no coinciden."})
        return data


# ===============================================
# SERIALIZERS DE USUARIO
# ===============================================

class UsuarioResumenSerializer(serializers.ModelSerializer):
    """Versión resumida del usuario (para listas)"""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'uuid', 'nombre_completo', 'email',
            'role', 'nivel_usuario', 'foto_perfil', 'verificado'
        ]

    def get_nombre_completo(self, obj):
        return obj.get_nombre_completo()


class PerfilClienteSerializer(serializers.ModelSerializer):
    """Perfil completo de un cliente"""
    nombre_completo = serializers.SerializerMethodField()
    nivel_display = serializers.CharField(source='get_nivel_usuario_display', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'uuid', 'username', 'email',
            'nombre', 'apellido', 'nombre_completo',
            'telefono', 'direccion', 'ciudad', 'estado', 'codigo_postal',
            'foto_perfil', 'nivel_usuario', 'nivel_display',
            'puntos_acumulados', 'total_rentales', 'total_gastado',
            'calificacion_promedio', 'numero_evaluaciones',
            'numero_identidad', 'tipo_identidad',
            'verificado', 'activo', 'fecha_registro'
        ]
        read_only_fields = [
            'id', 'uuid', 'email', 'nivel_usuario', 'puntos_acumulados',
            'total_rentales', 'total_gastado', 'calificacion_promedio',
            'numero_evaluaciones', 'verificado', 'fecha_registro'
        ]

    def get_nombre_completo(self, obj):
        return obj.get_nombre_completo()


class PerfilChoferSerializer(serializers.ModelSerializer):
    """Perfil completo de un chofer"""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'uuid', 'username', 'email',
            'nombre', 'apellido', 'nombre_completo',
            'telefono', 'foto_perfil',
            'numero_licencia_conducir', 'vencimiento_licencia',
            'banco_nombre', 'cuenta_bancaria', 'tipo_cuenta', 'rfc_usuario',
            'total_viajes_completados', 'total_ganancias',
            'calificacion_chofer', 'numero_evaluaciones_chofer',
            'numero_identidad', 'tipo_identidad',
            'activo_chofer', 'verificado', 'activo', 'fecha_registro'
        ]
        read_only_fields = [
            'id', 'uuid', 'email', 'total_viajes_completados',
            'total_ganancias', 'calificacion_chofer',
            'numero_evaluaciones_chofer', 'verificado', 'fecha_registro'
        ]

    def get_nombre_completo(self, obj):
        return obj.get_nombre_completo()


class AdminUsuarioSerializer(serializers.ModelSerializer):
    """Serializer completo para que el admin vea cualquier usuario"""
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = '__all__'
        read_only_fields = ['id', 'uuid', 'creado_en', 'actualizado_en']

    def get_nombre_completo(self, obj):
        return obj.get_nombre_completo()


# ===============================================
# SERIALIZERS DE RESEÑAS
# ===============================================

class ResenaVehiculoSerializer(serializers.ModelSerializer):
    """Serializer para reseñas de vehículos"""
    usuario_nombre = serializers.CharField(source='usuario.get_nombre_completo', read_only=True)

    class Meta:
        model = ResenaVehiculo
        fields = [
            'id', 'uuid', 'vehiculo', 'usuario', 'usuario_nombre', 'renta',
            'calificacion', 'comentario',
            'limpieza', 'condicion_mecanica', 'comodidad', 'puntualidad',
            'creado_en'
        ]
        read_only_fields = ['id', 'uuid', 'usuario', 'creado_en']

    def validate_vehiculo(self, value):
        usuario = self.context['request'].user_obj
        # Verificar que el usuario haya rentado ese vehículo
        rento = Rental.objects.filter(
            cliente=usuario,
            vehiculo=value,
            estado='completada'
        ).exists()
        if not rento:
            raise serializers.ValidationError("Solo puedes reseñar vehículos que hayas rentado.")
        return value


class ResenaChoferSerializer(serializers.ModelSerializer):
    """Serializer para reseñas de choferes"""
    cliente_nombre = serializers.CharField(source='cliente.get_nombre_completo', read_only=True)

    class Meta:
        model = ResenaChofer
        fields = [
            'id', 'uuid', 'chofer', 'cliente', 'cliente_nombre', 'renta',
            'calificacion', 'comentario',
            'cortesia', 'conocimiento_ciudad', 'seguridad_conduccion',
            'puntualidad', 'limpieza_auto',
            'creado_en'
        ]
        read_only_fields = ['id', 'uuid', 'cliente', 'creado_en']


# ===============================================
# SERIALIZERS DE VEHÍCULOS
# ===============================================

class VehiculoResumenSerializer(serializers.ModelSerializer):
    """Versión resumida del vehículo (para listas y búsquedas)"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    propietario_nombre = serializers.CharField(source='propietario.get_nombre_completo', read_only=True)

    class Meta:
        model = Vehiculo
        fields = [
            'id', 'uuid', 'marca', 'modelo', 'ano', 'placa',
            'color', 'transmision', 'tipo_combustible', 'numero_asientos',
            'tarifa_diaria', 'es_premium', 'estado', 'estado_display',
            'foto_principal', 'propietario_nombre'
        ]


class VehiculoDetalleSerializer(serializers.ModelSerializer):
    """Detalle completo del vehículo"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    propietario = UsuarioResumenSerializer(read_only=True)
    propietario_id = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(role__in=['admin', 'chofer']),
        source='propietario', write_only=True
    )
    calificacion_promedio = serializers.SerializerMethodField()
    resenas = ResenaVehiculoSerializer(many=True, read_only=True)

    class Meta:
        model = Vehiculo
        fields = '__all__'
        read_only_fields = ['id', 'uuid', 'creado_en', 'actualizado_en']

    def get_calificacion_promedio(self, obj):
        resenas = obj.resenas.all()
        if not resenas.exists():
            return None
        total = sum(r.calificacion for r in resenas)
        return round(total / resenas.count(), 2)


class AdminVehiculoSerializer(serializers.ModelSerializer):
    """Serializer completo para que el admin gestione vehículos"""
    propietario_nombre = serializers.CharField(source='propietario.get_nombre_completo', read_only=True)

    class Meta:
        model = Vehiculo
        fields = '__all__'
        read_only_fields = ['id', 'uuid', 'creado_en', 'actualizado_en']


# ===============================================
# SERIALIZERS DE RENTALES
# ===============================================

class RentalResumenSerializer(serializers.ModelSerializer):
    """Versión resumida de un rental (para listas)"""
    cliente_nombre = serializers.CharField(source='cliente.get_nombre_completo', read_only=True)
    vehiculo_marca = serializers.CharField(source='vehiculo.marca', read_only=True)
    vehiculo_modelo = serializers.CharField(source='vehiculo.modelo', read_only=True)
    vehiculo_foto = serializers.ImageField(source='vehiculo.foto_principal', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Rental
        fields = [
            'id', 'uuid', 'cliente_nombre', 'vehiculo_marca', 'vehiculo_modelo', 'vehiculo_foto',
            'fecha_inicio', 'fecha_fin', 'numero_dias', 'lugar_recogida',
            'costo_total', 'estado', 'estado_display', 'creado_en'
        ]


class CrearRentalSerializer(serializers.ModelSerializer):
    """Serializer para que un cliente cree un rental"""
    codigo_promocion = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Rental
        fields = [
            'vehiculo', 'chofer',
            'fecha_inicio', 'fecha_fin',
            'lugar_recogida', 'latitud_recogida', 'longitud_recogida',
            'lugar_entrega', 'latitud_entrega', 'longitud_entrega',
            'solicitudes_especiales', 'codigo_promocion'
        ]

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        vehiculo = data.get('vehiculo')

        if fecha_fin <= fecha_inicio:
            raise serializers.ValidationError("La fecha de fin debe ser posterior a la de inicio.")

        # Verificar que el vehículo esté disponible
        if vehiculo and vehiculo.estado != 'disponible':
            raise serializers.ValidationError("Este vehículo no está disponible.")

        # Verificar que no haya traslape con otro rental
        traslape = Rental.objects.filter(
            vehiculo=vehiculo,
            estado__in=['confirmada', 'en_curso'],
            fecha_inicio__lt=fecha_fin,
            fecha_fin__gt=fecha_inicio
        ).exists()
        if traslape:
            raise serializers.ValidationError("El vehículo ya está reservado en esas fechas.")

        return data

    def create(self, validated_data):
        # Evitar el TypeError extrayendo campos que no existen en el Modelo Rental
        validated_data.pop('codigo_promocion', None)
        return super().create(validated_data)


class RentalDetalleSerializer(serializers.ModelSerializer):
    """Detalle completo de un rental"""
    cliente = PerfilClienteSerializer(read_only=True)
    vehiculo = VehiculoResumenSerializer(read_only=True)
    chofer = PerfilChoferSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    pago_info = serializers.SerializerMethodField()

    class Meta:
        model = Rental
        fields = '__all__'

    def get_pago_info(self, obj):
        try:
            pago = obj.pago
            return {
                'id': pago.id,
                'monto': pago.monto,
                'estado': pago.estado,
                'metodo_pago': pago.metodo_pago
            }
        except Exception:
            return None


class ChoferRentalSerializer(serializers.ModelSerializer):
    """Vista de un rental desde el punto de vista del chofer"""
    cliente = UsuarioResumenSerializer(read_only=True)
    vehiculo = VehiculoResumenSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Rental
        fields = [
            'id', 'uuid', 'cliente', 'vehiculo',
            'fecha_inicio', 'fecha_fin',
            'lugar_recogida', 'lugar_entrega',
            'estado', 'estado_display',
            'kilometraje_inicio', 'kilometraje_fin',
            'condicion_inicio', 'condicion_fin',
            'danos_reportados', 'solicitudes_especiales'
        ]
        read_only_fields = ['id', 'uuid', 'cliente', 'vehiculo', 'fecha_inicio', 'fecha_fin']


# ===============================================
# SERIALIZERS DE PAGOS
# ===============================================

class PagoSerializer(serializers.ModelSerializer):
    """Serializer para pagos"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    metodo_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)

    class Meta:
        model = Pago
        fields = [
            'id', 'uuid', 'renta', 'monto',
            'metodo_pago', 'metodo_display',
            'estado', 'estado_display',
            'numero_transaccion', 'numero_recibo',
            'ultimos_digitos_tarjeta', 'banco_tarjeta',
            'notas', 'creado_en', 'procesado_en'
        ]
        read_only_fields = ['id', 'uuid', 'estado', 'numero_transaccion', 'creado_en', 'procesado_en']


class CrearPagoSerializer(serializers.ModelSerializer):
    """Serializer para iniciar un pago"""
    class Meta:
        model = Pago
        fields = [
            'renta', 'monto', 'metodo_pago',
            'ultimos_digitos_tarjeta', 'banco_tarjeta',
            'banco_origen', 'cuenta_origen', 'referencia_transferencia',
            'notas'
        ]

    def validate_renta(self, value):
        if hasattr(value, 'pago'):
            raise serializers.ValidationError("Esta renta ya tiene un pago registrado.")
        return value


# ===============================================
# SERIALIZERS DE FACTURAS
# ===============================================

class FacturaSerializer(serializers.ModelSerializer):
    """Serializer para facturas"""
    renta_info = serializers.SerializerMethodField()

    class Meta:
        model = Factura
        fields = [
            'id', 'uuid', 'renta', 'renta_info', 'numero_factura',
            'subtotal', 'impuesto_iva', 'descuento', 'total',
            'fecha_emision', 'fecha_vencimiento', 'archivo_pdf',
            'creado_en'
        ]
        read_only_fields = ['id', 'uuid', 'creado_en']

    def get_renta_info(self, obj):
        return f"Renta #{obj.renta.id} - {obj.renta.vehiculo.marca} {obj.renta.vehiculo.modelo}"


# ===============================================
# SERIALIZERS DE NOTIFICACIONES
# ===============================================

class NotificacionSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones"""
    class Meta:
        model = Notificacion
        fields = [
            'id', 'uuid', 'titulo', 'mensaje', 'tipo',
            'leida', 'enviada', 'renta', 'pago',
            'creado_en', 'leido_en'
        ]
        read_only_fields = ['id', 'uuid', 'enviada', 'creado_en']


# ===============================================
# SERIALIZERS DE TICKETS DE SOPORTE
# ===============================================

class TicketSoporteSerializer(serializers.ModelSerializer):
    """Serializer para tickets de soporte"""
    usuario_nombre = serializers.CharField(source='usuario.get_nombre_completo', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)

    class Meta:
        model = TicketSoporte
        fields = [
            'id', 'uuid', 'usuario', 'usuario_nombre', 'renta',
            'titulo', 'descripcion', 'categoria',
            'estado', 'estado_display',
            'prioridad', 'prioridad_display',
            'archivo_url', 'asignado_a', 'notas_internas',
            'creado_en', 'actualizado_en', 'cerrado_en'
        ]
        read_only_fields = ['id', 'uuid', 'usuario', 'estado', 'asignado_a', 'notas_internas', 'creado_en']


class AdminTicketSerializer(serializers.ModelSerializer):
    """Serializer para que el admin gestione tickets"""
    class Meta:
        model = TicketSoporte
        fields = '__all__'


# ===============================================
# SERIALIZERS DE PROMOCIONES
# ===============================================

class PromocionSerializer(serializers.ModelSerializer):
    """Serializer para promociones"""
    tipo_display = serializers.CharField(source='get_tipo_descuento_display', read_only=True)
    esta_vigente = serializers.SerializerMethodField()

    class Meta:
        model = Promocion
        fields = [
            'id', 'uuid', 'codigo_promocion', 'descripcion',
            'tipo_descuento', 'tipo_display', 'valor_descuento',
            'fecha_inicio', 'fecha_fin', 'usos_maximos', 'usos_actuales',
            'minimo_monto', 'maximo_descuento',
            'solo_nuevos_clientes', 'solo_nivel_premium', 'solo_nivel_ejecutivo',
            'activa', 'esta_vigente', 'creado_en'
        ]
        read_only_fields = ['id', 'uuid', 'usos_actuales', 'creado_en']

    def get_esta_vigente(self, obj):
        from django.utils import timezone
        hoy = timezone.now().date()
        return obj.activa and obj.fecha_inicio <= hoy <= obj.fecha_fin


class ValidarPromocionSerializer(serializers.Serializer):
    """Serializer para validar un código promocional"""
    codigo_promocion = serializers.CharField(max_length=50)
    monto_renta = serializers.DecimalField(max_digits=10, decimal_places=2)


# ===============================================
# SERIALIZERS DE BENEFICIOS POR NIVEL
# ===============================================

class BeneficioNivelSerializer(serializers.ModelSerializer):
    """Serializer para beneficios por nivel"""
    nivel_display = serializers.CharField(source='get_nivel_display', read_only=True)

    class Meta:
        model = BeneficioNivel
        fields = '__all__'


# ===============================================
# SERIALIZERS DE HISTORIAL DE NIVEL
# ===============================================

class HistorialNivelSerializer(serializers.ModelSerializer):
    """Serializer para historial de cambios de nivel"""
    usuario_nombre = serializers.CharField(source='usuario.get_nombre_completo', read_only=True)

    class Meta:
        model = HistorialNivelUsuario
        fields = '__all__'
        read_only_fields = ['id', 'fecha_cambio']


# ===============================================
# SERIALIZERS DE DOCUMENTOS
# ===============================================

class DocumentoUsuarioSerializer(serializers.ModelSerializer):
    """Serializer para documentos del usuario"""
    class Meta:
        model = DocumentoUsuario
        fields = [
            'id', 'uuid', 'usuario', 'tipo_documento',
            'nombre_documento', 'url_archivo',
            'verificado', 'razon_rechazo',
            'creado_en', 'actualizado_en'
        ]
        read_only_fields = ['id', 'uuid', 'verificado', 'razon_rechazo', 'creado_en']


# ===============================================
# SERIALIZERS DE MANTENIMIENTO
# ===============================================

class MantenimientoVehiculoSerializer(serializers.ModelSerializer):
    """Serializer para mantenimiento de vehículos"""
    vehiculo_info = serializers.SerializerMethodField()

    class Meta:
        model = MantenimientoVehiculo
        fields = '__all__'
        read_only_fields = ['id', 'uuid', 'creado_en', 'actualizado_en']

    def get_vehiculo_info(self, obj):
        return f"{obj.vehiculo.marca} {obj.vehiculo.modelo} ({obj.vehiculo.placa})"


# ===============================================
# SERIALIZERS DE ESTADÍSTICAS (ADMIN)
# ===============================================

class EstadisticaDiariaSerializer(serializers.ModelSerializer):
    """Serializer para estadísticas diarias"""
    class Meta:
        model = EstadisticaDiaria
        fields = '__all__'
        read_only_fields = ['id', 'creado_en']


class DashboardAdminSerializer(serializers.Serializer):
    """Serializer para el dashboard del administrador"""
    total_usuarios = serializers.IntegerField()
    total_clientes = serializers.IntegerField()
    total_choferes = serializers.IntegerField()
    total_vehiculos = serializers.IntegerField()
    vehiculos_disponibles = serializers.IntegerField()
    vehiculos_ocupados = serializers.IntegerField()
    rentales_activas = serializers.IntegerField()
    rentales_pendientes = serializers.IntegerField()
    ingresos_mes = serializers.DecimalField(max_digits=10, decimal_places=2)
    tickets_abiertos = serializers.IntegerField()


# ===============================================
# SERIALIZERS DE GPS
# ===============================================

class SeguimientoGPSSerializer(serializers.ModelSerializer):
    """Serializer para datos de GPS"""
    class Meta:
        model = SeguimientoGPS
        fields = '__all__'
        read_only_fields = ['id', 'timestamp_ubicacion']


# ===============================================
# SERIALIZERS FALTANTES (Restaurados para evitar caídas de servidor)
# ===============================================

# Note: FacturaSerializer, NotificacionSerializer, PagoSerializer, and CrearPagoSerializer are defined above in their respective sections.