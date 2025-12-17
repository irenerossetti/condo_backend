from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Fee, Notification, User

class Command(BaseCommand):
    help = 'Finds overdue fees and creates notifications for the owners.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting payment reminder process ---'))

        # Buscamos cuotas vencidas (OVERDUE) que no hayan sido notificadas aún
        overdue_fees = Fee.objects.filter(status='OVERDUE')

        users_to_notify = {}

        for fee in overdue_fees:
            owner = fee.unit.owner
            if owner.id not in users_to_notify:
                users_to_notify[owner.id] = {'owner': owner, 'count': 0}
            users_to_notify[owner.id]['count'] += 1

        notifications_created = 0
        for user_id, data in users_to_notify.items():
            owner = data['owner']
            count = data['count']

            message = f"Tienes {count} cuota(s) vencida(s). Por favor, revisa tu estado de cuenta."

            # Creamos una única notificación por usuario deudor
            # El 'defaults' asegura que no se creen notificaciones duplicadas si el comando se corre varias veces
            notification, created = Notification.objects.get_or_create(
                user=owner,
                message=message,
                is_read=False,
                link='/fees', # Dirige al usuario a la página de cuotas
            )
            if created:
                notifications_created += 1

        self.stdout.write(self.style.SUCCESS(f'--- Process finished. Created {notifications_created} new reminders. ---'))