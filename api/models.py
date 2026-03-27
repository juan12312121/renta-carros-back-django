"""
Models para el sistema de renta de carros
Sincronizados con la base de datos PostgreSQL
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

# ===============================================
# CHOICES Y CONSTANTES
# ===============================================

ROLE_CHOICES = (
    ('cliente', 'Cliente'),
    ('chofer', 'Chofer'),
    ('admin', 'Administrador'),
)

NIVEL_CHOICES = (
    ('normal', 'Normal'),
    ('frecuente', 'Frecuente'),
    ('premium', 'Premium'),
    ('ejecutivo', 'Ejecutivo'),
)

CAR_STATUS_CHOICES = (
    ('disponible', 'Disponible'),
    ('ocupado', 'Ocupado'),
    ('reservado', 'Reservado'),
    ('mantenimiento', 'Mantenimiento'),
    ('baja', 'Baja'),
)

RENTAL_STATUS_CHOICES = (
    ('pendiente', 'Pendiente'),
    ('confirmada', 'Confirmada'),
    ('en_curso', 'En Curso'),
    ('completada', 'Completada'),
    ('cancelada', 'Cancelada'),
)

PAYMENT_STATUS_CHOICES = (
    ('pendiente', 'Pendiente'),
    ('procesando', 'Procesando'),
    ('completado', 'Completado'),
    ('fallido', 'Fallido'),
    ('reembolsado', 'Reembolsado'),
)

PAYMENT_METHOD_CHOICES = (
    ('tarjeta_credito', 'Tarjeta de Crédito'),
    ('tarjeta_debito', 'Tarjeta de Débito'),
    ('transferencia_bancaria', 'Transferencia Bancaria'),
    ('efectivo', 'Efectivo'),
    ('paypal', 'PayPal'),
    ('stripe', 'Stripe'),
)

TRANSMISSION_CHOICES = (
    ('manual', 'Manual'),
    ('automatica', 'Automática'),
)

FUEL_CHOICES = (
    ('gasolina', 'Gasolina'),
    ('diesel', 'Diesel'),
    ('electrico', 'Eléctrico'),
    ('hibrido', 'Híbrido'),
)

TICKET_STATUS_CHOICES = (
    ('abierto', 'Abierto'),
    ('en_proceso', 'En Proceso'),
    ('resuelto', 'Resuelto'),
    ('cerrado', 'Cerrado'),
)

TICKET_PRIORITY_CHOICES = (
    ('baja', 'Baja'),
    ('media', 'Media'),
    ('alta', 'Alta'),
    ('urgente', 'Urgente'),
)

# ===============================================
# 1. MODELO USUARIO (Cliente, Chofer, Admin)
# ===============================================
class Usuario(models.Model):
    """Modelo unificado para cliente, chofer y admin"""
    
    # Campos básicos
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)
    codigo_postal = models.CharField(max_length=20, blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    
    # Tipo de usuario
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cliente')
    
    # CAMPOS PARA CLIENTES
    nivel_usuario = models.CharField(max_length=20, choices=NIVEL_CHOICES, default='normal')
    puntos_acumulados = models.IntegerField(default=0)
    total_rentales = models.IntegerField(default=0)
    total_gastado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    calificacion_promedio = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    numero_evaluaciones = models.IntegerField(default=0)
    fecha_proximo_upgrade = models.DateField(blank=True, null=True)
    
    # CAMPOS PARA CHOFERES
    numero_licencia_conducir = models.CharField(max_length=50, unique=True, blank=True, null=True)
    vencimiento_licencia = models.DateField(blank=True, null=True)
    numero_registro_conducir = models.CharField(max_length=100, blank=True, null=True)
    banco_nombre = models.CharField(max_length=100, blank=True, null=True)
    cuenta_bancaria = models.CharField(max_length=100, blank=True, null=True)
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True)
    rfc_usuario = models.CharField(max_length=50, blank=True, null=True)
    total_viajes_completados = models.IntegerField(default=0)
    total_ganancias = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    calificacion_chofer = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    numero_evaluaciones_chofer = models.IntegerField(default=0)
    activo_chofer = models.BooleanField(default=False)
    
    # Campos comunes
    numero_identidad = models.CharField(max_length=50, unique=True, blank=True, null=True)
    tipo_identidad = models.CharField(max_length=50, blank=True, null=True)
    verificado = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    ultimo_acceso = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['nivel_usuario']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.get_role_display()})"
    
    def get_nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def es_cliente(self):
        return self.role == 'cliente'
    
    def es_chofer(self):
        return self.role == 'chofer'
    
    def es_admin(self):
        return self.role == 'admin'


# ===============================================
# 2. HISTORIAL DE NIVELES (Auditoría de escalada)
# ===============================================
class HistorialNivelUsuario(models.Model):
    """Registra cada cambio de nivel de usuario"""
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='historial_niveles')
    nivel_anterior = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    nivel_nuevo = models.CharField(max_length=20, choices=NIVEL_CHOICES)
    puntos_alcanzados = models.IntegerField(blank=True, null=True)
    rentales_completados = models.IntegerField(blank=True, null=True)
    monto_gastado = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    razon_upgrade = models.CharField(max_length=255, blank=True, null=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'historial_niveles_usuario'
        verbose_name = 'Historial de Nivel'
        verbose_name_plural = 'Historiales de Nivel'
        ordering = ['-fecha_cambio']
    
    def __str__(self):
        return f"{self.usuario.get_nombre_completo()}: {self.nivel_anterior} → {self.nivel_nuevo}"


# ===============================================
# 3. BENEFICIOS POR NIVEL
# ===============================================
class BeneficioNivel(models.Model):
    """Define los beneficios asociados a cada nivel"""
    
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, unique=True)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    descuento_fijo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    puntos_multiplicador = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    acceso_vip = models.BooleanField(default=False)
    prioridad_soporte = models.CharField(max_length=50, default='normal')
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2, default=5000)
    descuento_adicional_frecuente = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    acceso_vehiculos_premium = models.BooleanField(default=False)
    servicio_concierge = models.BooleanField(default=False)
    seguro_incluido = models.BooleanField(default=False)
    descripcion = models.TextField(blank=True, null=True)
    requisitos_rentales = models.IntegerField(default=0)
    requisitos_puntos = models.IntegerField(default=0)
    requisitos_monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'beneficios_nivel'
        verbose_name = 'Beneficio de Nivel'
        verbose_name_plural = 'Beneficios de Nivel'
    
    def __str__(self):
        return f"Beneficios {self.get_nivel_display()}"


# ===============================================
# 4. VEHÍCULOS
# ===============================================
class Vehiculo(models.Model):
    """Modelo para vehículos disponibles para renta"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=100)
    ano = models.IntegerField(validators=[MinValueValidator(2000)])
    placa = models.CharField(max_length=20, unique=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    vin = models.CharField(max_length=50, unique=True, blank=True, null=True)
    transmision = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, default='automatica')
    tipo_combustible = models.CharField(max_length=20, choices=FUEL_CHOICES, default='gasolina')
    numero_asientos = models.IntegerField(default=5)
    kilometraje_actual = models.IntegerField(default=0)
    numero_registro = models.CharField(max_length=100, unique=True, blank=True, null=True)
    numero_poliza_seguro = models.CharField(max_length=100, blank=True, null=True)
    vencimiento_poliza = models.DateField(blank=True, null=True)
    vencimiento_revision_tecnica = models.DateField(blank=True, null=True)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    tarifa_horaria = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tarifa_fin_semana = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    es_premium = models.BooleanField(default=False)
    disponible_para_ejecutivos = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=CAR_STATUS_CHOICES, default='disponible')
    propietario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='vehiculos_propiedad')
    foto_principal = models.ImageField(upload_to='uploads/', blank=True, null=True)
    foto_2 = models.ImageField(upload_to='uploads/', blank=True, null=True)
    foto_3 = models.ImageField(upload_to='uploads/', blank=True, null=True)
    foto_interior = models.ImageField(upload_to='uploads/', blank=True, null=True)
    documento_registro = models.FileField(upload_to='uploads/', blank=True, null=True)
    documento_seguro = models.FileField(upload_to='uploads/', blank=True, null=True)
    caracteristicas = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vehiculos'
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering = ['marca', 'modelo']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['es_premium']),
            models.Index(fields=['propietario']),
        ]
    
    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.placa}) - {self.get_estado_display()}"


# ===============================================
# 5. MANTENIMIENTO DE VEHÍCULOS
# ===============================================
class MantenimientoVehiculo(models.Model):
    """Registro de mantenimiento de vehículos"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='mantenimientos')
    tipo_mantenimiento = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fecha_mantenimiento = models.DateField()
    fecha_proximo_mantenimiento = models.DateField(blank=True, null=True)
    kilometraje_durante_mantenimiento = models.IntegerField(blank=True, null=True)
    notas_tecnicas = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'mantenimiento_vehiculos'
        verbose_name = 'Mantenimiento de Vehículo'
        verbose_name_plural = 'Mantenimientos de Vehículos'
        ordering = ['-fecha_mantenimiento']
    
    def __str__(self):
        return f"{self.vehiculo.placa} - {self.tipo_mantenimiento}"


# ===============================================
# 6. RENTALES
# ===============================================
class Rental(models.Model):
    """Modelo para registrar rentales"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cliente = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='rentales_cliente')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.RESTRICT, related_name='rentales')
    chofer = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='rentales_chofer', limit_choices_to={'role': 'chofer'})
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    fecha_devolucion_real = models.DateTimeField(blank=True, null=True)
    lugar_recogida = models.CharField(max_length=255)
    latitud_recogida = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_recogida = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    lugar_entrega = models.CharField(max_length=255)
    latitud_entrega = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitud_entrega = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    tarifa_diaria = models.DecimalField(max_digits=10, decimal_places=2)
    numero_dias = models.IntegerField()
    costo_total = models.DecimalField(max_digits=10, decimal_places=2)
    cargos_adicionales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento_aplicado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=RENTAL_STATUS_CHOICES, default='pendiente')
    solicitudes_especiales = models.TextField(blank=True, null=True)
    kilometraje_inicio = models.IntegerField(blank=True, null=True)
    kilometraje_fin = models.IntegerField(blank=True, null=True)
    condicion_inicio = models.CharField(max_length=255, blank=True, null=True)
    condicion_fin = models.CharField(max_length=255, blank=True, null=True)
    danos_reportados = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rentales'
        verbose_name = 'Rental'
        verbose_name_plural = 'Rentales'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['cliente']),
            models.Index(fields=['vehiculo']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
        ]
    
    def __str__(self):
        return f"Rental #{self.id} - {self.cliente.get_nombre_completo()} ({self.vehiculo.placa})"


# ===============================================
# 7. PAGOS
# ===============================================
class Pago(models.Model):
    """Modelo para registrar pagos"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    renta = models.OneToOneField(Rental, on_delete=models.CASCADE, related_name='pago')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES)
    estado = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pendiente')
    numero_transaccion = models.CharField(max_length=100, unique=True, blank=True, null=True)
    numero_recibo = models.CharField(max_length=100, unique=True, blank=True, null=True)
    ultimos_digitos_tarjeta = models.CharField(max_length=4, blank=True, null=True)
    banco_tarjeta = models.CharField(max_length=100, blank=True, null=True)
    banco_origen = models.CharField(max_length=100, blank=True, null=True)
    cuenta_origen = models.CharField(max_length=100, blank=True, null=True)
    referencia_transferencia = models.CharField(max_length=100, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    razon_rechazo = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    procesado_en = models.DateTimeField(blank=True, null=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pagos'
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['renta']),
            models.Index(fields=['estado']),
        ]
    
    def __str__(self):
        return f"Pago #{self.id} - ${self.monto} ({self.get_estado_display()})"


# ===============================================
# 8. FACTURAS
# ===============================================
class Factura(models.Model):
    """Modelo para facturas"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    renta = models.OneToOneField(Rental, on_delete=models.CASCADE, related_name='factura')
    numero_factura = models.CharField(max_length=100, unique=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    archivo_pdf = models.FileField(upload_to='facturas/', blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'facturas'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha_emision']
    
    def __str__(self):
        return f"Factura {self.numero_factura}"


# ===============================================
# 9. RESEÑAS DE VEHÍCULOS
# ===============================================
class ResenaVehiculo(models.Model):
    """Modelo para reseñas de vehículos"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='resenas')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_vehiculos')
    renta = models.ForeignKey(Rental, on_delete=models.SET_NULL, null=True, blank=True)
    calificacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True, null=True)
    limpieza = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    condicion_mecanica = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    comodidad = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    puntualidad = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'resenas_vehiculos'
        verbose_name = 'Reseña de Vehículo'
        verbose_name_plural = 'Reseñas de Vehículos'
        unique_together = ('vehiculo', 'usuario')
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"Reseña: {self.vehiculo.placa} - {self.calificacion}⭐"


# ===============================================
# 10. RESEÑAS DE CHOFERES
# ===============================================
class ResenaChofer(models.Model):
    """Modelo para reseñas de choferes"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    chofer = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_recibidas')
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='resenas_choferes_dadas')
    renta = models.ForeignKey(Rental, on_delete=models.SET_NULL, null=True, blank=True)
    calificacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True, null=True)
    cortesia = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    conocimiento_ciudad = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    seguridad_conduccion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    puntualidad = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    limpieza_auto = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'resenas_choferes'
        verbose_name = 'Reseña de Chofer'
        verbose_name_plural = 'Reseñas de Choferes'
        unique_together = ('chofer', 'cliente')
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"Reseña: {self.chofer.get_nombre_completo()} - {self.calificacion}⭐"


# ===============================================
# 11. SEGUIMIENTO GPS
# ===============================================
class SeguimientoGPS(models.Model):
    """Modelo para rastreo GPS en tiempo real"""
    
    id = models.AutoField(primary_key=True)
    renta = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='gps_data')
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    velocidad = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    rumbo = models.IntegerField(blank=True, null=True)
    timestamp_ubicacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'seguimiento_gps'
        verbose_name = 'Seguimiento GPS'
        verbose_name_plural = 'Seguimientos GPS'
        ordering = ['-timestamp_ubicacion']
        indexes = [
            models.Index(fields=['renta']),
            models.Index(fields=['timestamp_ubicacion']),
        ]
    
    def __str__(self):
        return f"GPS #{self.id} - Renta #{self.renta.id}"


# ===============================================
# 12. TICKETS DE SOPORTE
# ===============================================
class TicketSoporte(models.Model):
    """Modelo para tickets de soporte"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tickets_soporte')
    renta = models.ForeignKey(Rental, on_delete=models.SET_NULL, null=True, blank=True)
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    categoria = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=TICKET_STATUS_CHOICES, default='abierto')
    prioridad = models.CharField(max_length=20, choices=TICKET_PRIORITY_CHOICES, default='media')
    archivo_url = models.FileField(upload_to='tickets/', blank=True, null=True)
    asignado_a = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='tickets_asignados', limit_choices_to={'role': 'admin'})
    notas_internas = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    cerrado_en = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'tickets_soporte'
        verbose_name = 'Ticket de Soporte'
        verbose_name_plural = 'Tickets de Soporte'
        ordering = ['-prioridad', '-creado_en']
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['estado']),
            models.Index(fields=['prioridad']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.titulo}"


# ===============================================
# 13. NOTIFICACIONES
# ===============================================
class Notificacion(models.Model):
    """Modelo para notificaciones"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=255)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=50, blank=True, null=True)
    leida = models.BooleanField(default=False)
    enviada = models.BooleanField(default=False)
    renta = models.ForeignKey(Rental, on_delete=models.SET_NULL, null=True, blank=True)
    pago = models.ForeignKey(Pago, on_delete=models.SET_NULL, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    leido_en = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'notificaciones'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['leida']),
        ]
    
    def __str__(self):
        return f"Notificación: {self.titulo}"


# ===============================================
# 14. DOCUMENTOS DE USUARIO
# ===============================================
class DocumentoUsuario(models.Model):
    """Modelo para documentos del usuario (DNI, licencia, etc)"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='documentos')
    tipo_documento = models.CharField(max_length=100)
    nombre_documento = models.CharField(max_length=255)
    url_archivo = models.FileField(upload_to='documentos_usuario/')
    verificado = models.BooleanField(default=False)
    razon_rechazo = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documentos_usuario'
        verbose_name = 'Documento de Usuario'
        verbose_name_plural = 'Documentos de Usuario'
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"{self.usuario.get_nombre_completo()} - {self.tipo_documento}"


# ===============================================
# 15. HISTORIAL DE AUDITORÍA
# ===============================================
class HistorialAuditoria(models.Model):
    """Modelo para auditoría de cambios"""
    
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    tabla_afectada = models.CharField(max_length=100)
    registro_id = models.IntegerField(blank=True, null=True)
    accion = models.CharField(max_length=20)  # INSERT, UPDATE, DELETE
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    cambios_resumidos = models.TextField(blank=True, null=True)
    direccion_ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'historial_auditoria'
        verbose_name = 'Historial de Auditoría'
        verbose_name_plural = 'Historial de Auditoría'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['tabla_afectada']),
            models.Index(fields=['creado_en']),
        ]
    
    def __str__(self):
        return f"{self.accion} en {self.tabla_afectada} - {self.creado_en}"


# ===============================================
# 16. PROMOCIONES
# ===============================================
class Promocion(models.Model):
    """Modelo para promociones y códigos de descuento"""
    
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    codigo_promocion = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    tipo_descuento = models.CharField(max_length=20, choices=[('porcentaje', 'Porcentaje'), ('fijo', 'Fijo')])
    valor_descuento = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    usos_maximos = models.IntegerField(blank=True, null=True)
    usos_actuales = models.IntegerField(default=0)
    minimo_monto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    maximo_descuento = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    solo_nuevos_clientes = models.BooleanField(default=False)
    solo_nivel_premium = models.BooleanField(default=False)
    solo_nivel_ejecutivo = models.BooleanField(default=False)
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'promociones'
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-fecha_fin']
        indexes = [
            models.Index(fields=['codigo_promocion']),
            models.Index(fields=['activa']),
        ]
    
    def __str__(self):
        return f"{self.codigo_promocion} - {self.valor_descuento}{self.get_tipo_descuento_display()}"


# ===============================================
# 17. USO DE PROMOCIONES
# ===============================================
class UsoPromocion(models.Model):
    """Modelo para registrar el uso de promociones"""
    
    id = models.AutoField(primary_key=True)
    promocion = models.ForeignKey(Promocion, on_delete=models.CASCADE, related_name='usos')
    renta = models.OneToOneField(Rental, on_delete=models.CASCADE, related_name='promocion_usada')
    monto_descuento = models.DecimalField(max_digits=10, decimal_places=2)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'uso_promociones'
        verbose_name = 'Uso de Promoción'
        verbose_name_plural = 'Usos de Promociones'
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"{self.promocion.codigo_promocion} - Renta #{self.renta.id}"


# ===============================================
# 18. ESTADÍSTICAS DIARIAS
# ===============================================
class EstadisticaDiaria(models.Model):
    """Modelo para estadísticas diarias del negocio"""
    
    id = models.AutoField(primary_key=True)
    fecha = models.DateField(unique=True)
    total_rentales_nuevas = models.IntegerField(default=0)
    total_rentales_completadas = models.IntegerField(default=0)
    total_rentales_canceladas = models.IntegerField(default=0)
    ingresos_totales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pagos_completados = models.IntegerField(default=0)
    pagos_pendientes = models.IntegerField(default=0)
    nuevos_clientes = models.IntegerField(default=0)
    nuevos_choferes = models.IntegerField(default=0)
    autos_disponibles = models.IntegerField(default=0)
    autos_ocupados = models.IntegerField(default=0)
    autos_mantenimiento = models.IntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'estadisticas_diarias'
        verbose_name = 'Estadística Diaria'
        verbose_name_plural = 'Estadísticas Diarias'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['fecha']),
        ]
    
    def __str__(self):
        return f"Estadísticas - {self.fecha}"