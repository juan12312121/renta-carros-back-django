from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import (
    EstadisticaDiaria, Rental, Pago, Usuario, Vehiculo
)
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Genera las estadísticas diarias del negocio. Debe correrse todos los días a media noche via Cron.'

    def handle(self, *args, **kwargs):
        ayer = timezone.now().date() - timedelta(days=1)
        
        # Verificar si ya existe para evitar duplicados
        if EstadisticaDiaria.objects.filter(fecha=ayer).exists():
            self.stdout.write(self.style.WARNING(f'Las estadísticas para {ayer} ya fueron generadas.'))
            return

        rentales_ayer = Rental.objects.filter(creado_en__date=ayer)
        pagos_ayer = Pago.objects.filter(creado_en__date=ayer)
        
        ingresos = pagos_ayer.filter(estado='completado').aggregate(Sum('monto'))['monto__sum'] or 0

        EstadisticaDiaria.objects.create(
            fecha=ayer,
            total_rentales_nuevas=rentales_ayer.count(),
            total_rentales_completadas=Rental.objects.filter(fecha_devolucion_real__date=ayer, estado='completada').count(),
            total_rentales_canceladas=rentales_ayer.filter(estado='cancelada').count(),
            ingresos_totales=ingresos,
            pagos_completados=pagos_ayer.filter(estado='completado').count(),
            pagos_pendientes=pagos_ayer.filter(estado='pendiente').count(),
            nuevos_clientes=Usuario.objects.filter(role='cliente', creado_en__date=ayer).count(),
            nuevos_choferes=Usuario.objects.filter(role='chofer', creado_en__date=ayer).count(),
            autos_disponibles=Vehiculo.objects.filter(estado='disponible').count(),
            autos_ocupados=Vehiculo.objects.filter(estado='ocupado').count(),
            autos_mantenimiento=Vehiculo.objects.filter(estado='mantenimiento').count()
        )

        self.stdout.write(self.style.SUCCESS(f'Estadísticas generadas exitosamente para {ayer}.'))
