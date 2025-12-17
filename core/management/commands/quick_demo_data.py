from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import *
from datetime import timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera datos de demostración rápidamente'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Generando datos de demostración...'))
        
        # Obtener usuarios y unidades existentes
        users = list(User.objects.all())
        units = list(Unit.objects.all())
        
        if not users or not units:
            self.stdout.write(self.style.ERROR('❌ Primero ejecuta: python manage.py setup_demo'))
            return
        
        self.stdout.write(f'✓ Encontrados {len(users)} usuarios y {len(units)} unidades')
        
        # 1. Crear cuotas para todas las unidades (últimos 6 meses)
        self.stdout.write('💰 Creando cuotas...')
        expense_types = list(ExpenseType.objects.all())
        if not expense_types:
            expense_types = [
                ExpenseType.objects.create(name='Mantenimiento', amount_default=5000),
                ExpenseType.objects.create(name='Servicios', amount_default=2000),
            ]
        
        fees_created = 0
        for unit in units[:50]:  # Solo primeras 50 unidades para ser más rápido
            for month in range(6):
                due_date = timezone.now() - timedelta(days=30 * month)
                period = due_date.strftime('%Y-%m')
                for expense_type in expense_types:
                    status = random.choice(['PAID', 'PAID', 'PENDING', 'OVERDUE'])
                    fee, created = Fee.objects.get_or_create(
                        unit=unit,
                        expense_type=expense_type,
                        period=period,
                        defaults={
                            'amount': expense_type.amount_default,
                            'due_date': due_date,
                            'status': status
                        }
                    )
                    
                    if created:
                        # Crear pago si está pagada
                        if status == 'PAID' and not fee.payments.exists():
                            Payment.objects.create(
                                fee=fee,
                                amount=fee.amount,
                                method=random.choice(['cash', 'transfer', 'card'])
                            )
                        fees_created += 1
        
        self.stdout.write(f'  ✓ Creadas {fees_created} cuotas')
        
        # 2. Crear visitantes
        self.stdout.write('👥 Creando visitantes...')
        visitors_created = 0
        for _ in range(50):
            entry_time = timezone.now() - timedelta(days=random.randint(0, 180))
            has_exited = random.random() > 0.3
            
            Visitor.objects.create(
                unit=random.choice(units),
                full_name=f'Visitante {visitors_created + 1}',
                entry_time=entry_time,
                exit_time=entry_time + timedelta(hours=random.randint(1, 8)) if has_exited else None
            )
            visitors_created += 1
        
        self.stdout.write(f'  ✓ Creados {visitors_created} visitantes')
        
        # 3. Crear solicitudes de mantenimiento
        self.stdout.write('🔧 Creando solicitudes de mantenimiento...')
        categories = ['PLUMBING', 'ELECTRICAL', 'CARPENTRY', 'PAINTING', 'OTHER']
        maintenance_created = 0
        for _ in range(30):
            MaintenanceRequest.objects.create(
                unit=random.choice(units),
                requester=random.choice(users),
                title=f'Solicitud de mantenimiento #{maintenance_created + 1}',
                description='Descripción de la solicitud',
                category=random.choice(categories),
                priority=random.choice(['LOW', 'MEDIUM', 'HIGH']),
                status=random.choice(['PENDING', 'IN_PROGRESS', 'COMPLETED'])
            )
            maintenance_created += 1
        
        self.stdout.write(f'  ✓ Creadas {maintenance_created} solicitudes')
        
        # 4. Crear incidentes de seguridad
        self.stdout.write('🚨 Creando incidentes de seguridad...')
        incident_types = ['THEFT', 'VANDALISM', 'NOISE', 'SUSPICIOUS', 'OTHER']
        incidents_created = 0
        for _ in range(20):
            SecurityIncident.objects.create(
                incident_type=random.choice(incident_types),
                description=f'Incidente de seguridad #{incidents_created + 1}',
                location='Área común',
                severity=random.choice(['LOW', 'MEDIUM', 'HIGH']),
                reported_by=random.choice(users),
                status=random.choice(['PENDING', 'IN_PROGRESS', 'RESOLVED'])
            )
            incidents_created += 1
        
        self.stdout.write(f'  ✓ Creados {incidents_created} incidentes')
        
        # 5. Crear reservaciones
        self.stdout.write('📅 Creando reservaciones...')
        common_areas = list(CommonArea.objects.all())
        if not common_areas:
            common_areas = [
                CommonArea.objects.create(name='Piscina', capacity=50),
                CommonArea.objects.create(name='Gimnasio', capacity=20),
                CommonArea.objects.create(name='Salón de Eventos', capacity=100),
            ]
        
        reservations_created = 0
        for _ in range(40):
            reservation_date = timezone.now() + timedelta(days=random.randint(-30, 30))
            Reservation.objects.create(
                common_area=random.choice(common_areas),
                unit=random.choice(units),
                reservation_date=reservation_date,
                start_time=f'{random.randint(8, 18):02d}:00',
                end_time=f'{random.randint(10, 20):02d}:00',
                status=random.choice(['PENDING', 'CONFIRMED', 'COMPLETED'])
            )
            reservations_created += 1
        
        self.stdout.write(f'  ✓ Creadas {reservations_created} reservaciones')
        
        # Resumen
        self.stdout.write(self.style.SUCCESS('\n✅ Datos generados exitosamente!'))
        self.stdout.write(f'  💰 Cuotas: {Fee.objects.count()}')
        self.stdout.write(f'  💳 Pagos: {Payment.objects.count()}')
        self.stdout.write(f'  👥 Visitantes: {Visitor.objects.count()}')
        self.stdout.write(f'  🔧 Mantenimiento: {MaintenanceRequest.objects.count()}')
        self.stdout.write(f'  🚨 Incidentes: {SecurityIncident.objects.count()}')
        self.stdout.write(f'  📅 Reservaciones: {Reservation.objects.count()}')
