from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import Rental

class Command(BaseCommand):
    help = 'Cancela las reservas que se quedaron en estado pendiente (sin pago) después de 2 horas. Correr cada hora via Cron.'

    def handle(self, *args, **kwargs):
        hace_2_horas = timezone.now() - timedelta(hours=2)
        
        # Consultar rentales pendientes de hace mas de 2 horas
        rentales_caducadas = Rental.objects.filter(
            estado='pendiente',
            creado_en__lte=hace_2_horas
        )
        
        total_canceladas = 0
        for rental in rentales_caducadas:
            # Liberar vehículo
            vehiculo = rental.vehiculo
            vehiculo.estado = 'disponible'
            vehiculo.save(update_fields=['estado'])
            
            # Cancelar rental
            rental.estado = 'cancelada'
            rental.save(update_fields=['estado'])
            
            # Opcional: Generar notificacion para el usuario de que se venció su reserva
            
            total_canceladas += 1

        self.stdout.write(self.style.SUCCESS(f'Se cancelaron {total_canceladas} reservas por falta de pago.'))
