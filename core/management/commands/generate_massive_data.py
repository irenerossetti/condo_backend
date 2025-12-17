from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import (
    Profile, Unit, ExpenseType, Fee, Notice, NoticeCategory,
    CommonArea, Reservation, MaintenanceRequest, MaintenanceRequestComment,
    MaintenanceRequestAttachment, Vehicle, Pet, FamilyMember,
    Notification, ActivityLog, Visitor, SecurityIncident,
    FaceEncoding, AccessLog, AuthorizedVehicle, Payment
)
from faker import Faker
from datetime import timedelta
import random

User = get_user_model()
fake = Faker('es_ES')


class Command(BaseCommand):
    help = 'Genera un dataset masivo de 3000+ registros para el sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--total',
            type=int,
            default=3000,
            help='Número total aproximado de registros a generar'
        )

    def handle(self, *args, **options):
        total_target = options['total']
        self.stdout.write(self.style.SUCCESS(f'🚀 Generando dataset masivo de ~{total_target} registros...'))
        
        # Distribución de registros
        num_users = min(100, total_target // 30)
        num_units = min(150, total_target // 20)
        num_fees = num_units * 12  # 12 cuotas por unidad
        num_payments = int(num_fees * 0.7)  # 70% pagadas
        num_notices = min(200, total_target // 15)
        num_reservations = min(300, total_target // 10)
        num_maintenance = min(250, total_target // 12)
        num_visitors = min(400, total_target // 8)
        num_incidents = min(150, total_target // 20)
        num_access_logs = min(800, total_target // 4)
        num_notifications = min(500, total_target // 6)
        num_activity_logs = min(600, total_target // 5)

        # 1. Crear usuarios
        self.stdout.write('📝 Creando usuarios...')
        users = self._create_users(num_users)
        
        # 2. Crear unidades
        self.stdout.write('🏢 Creando unidades...')
        units = self._create_units(num_units, users)
        
        # 3. Crear tipos de gastos
        self.stdout.write('💰 Creando tipos de gastos...')
        expense_types = self._create_expense_types()
        
        # 4. Crear cuotas
        self.stdout.write('📊 Creando cuotas...')
        fees = self._create_fees(num_fees, units, expense_types)
        
        # 5. Crear pagos
        self.stdout.write('💳 Creando pagos...')
        self._create_payments(num_payments, fees)
        
        # 6. Crear categorías y avisos
        self.stdout.write('📢 Creando avisos...')
        categories = self._create_notice_categories()
        self._create_notices(num_notices, categories, users)
        
        # 7. Crear áreas comunes y reservaciones
        self.stdout.write('🏊 Creando reservaciones...')
        common_areas = self._create_common_areas()
        self._create_reservations(num_reservations, common_areas, units)
        
        # 8. Crear solicitudes de mantenimiento
        self.stdout.write('🔧 Creando solicitudes de mantenimiento...')
        self._create_maintenance_requests(num_maintenance, units, users)
        
        # 9. Crear vehículos, mascotas y familiares
        self.stdout.write('🚗 Creando vehículos, mascotas y familiares...')
        self._create_vehicles_pets_family(units)
        
        # 10. Crear visitantes
        self.stdout.write('👥 Creando visitantes...')
        self._create_visitors(num_visitors, units)
        
        # 11. Crear incidentes de seguridad
        self.stdout.write('🚨 Creando incidentes de seguridad...')
        self._create_security_incidents(num_incidents, units)
        
        # 12. Crear logs de acceso
        self.stdout.write('🔐 Creando logs de acceso...')
        self._create_access_logs(num_access_logs, units)
        
        # 13. Crear notificaciones
        self.stdout.write('🔔 Creando notificaciones...')
        self._create_notifications(num_notifications, users)
        
        # 14. Crear logs de actividad
        self.stdout.write('📋 Creando logs de actividad...')
        self._create_activity_logs(num_activity_logs, users)
        
        # Resumen final
        total_created = (
            User.objects.count() +
            Unit.objects.count() +
            Fee.objects.count() +
            Payment.objects.count() +
            Notice.objects.count() +
            Reservation.objects.count() +
            MaintenanceRequest.objects.count() +
            Visitor.objects.count() +
            SecurityIncident.objects.count() +
            AccessLog.objects.count() +
            Notification.objects.count() +
            ActivityLog.objects.count()
        )
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Dataset generado exitosamente!'))
        self.stdout.write(self.style.SUCCESS(f'📊 Total de registros creados: {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'\nDesglose:'))
        self.stdout.write(f'  👤 Usuarios: {User.objects.count()}')
        self.stdout.write(f'  🏢 Unidades: {Unit.objects.count()}')
        self.stdout.write(f'  💰 Cuotas: {Fee.objects.count()}')
        self.stdout.write(f'  💳 Pagos: {Payment.objects.count()}')
        self.stdout.write(f'  📢 Avisos: {Notice.objects.count()}')
        self.stdout.write(f'  🏊 Reservaciones: {Reservation.objects.count()}')
        self.stdout.write(f'  🔧 Mantenimientos: {MaintenanceRequest.objects.count()}')
        self.stdout.write(f'  👥 Visitantes: {Visitor.objects.count()}')
        self.stdout.write(f'  🚨 Incidentes: {SecurityIncident.objects.count()}')
        self.stdout.write(f'  🔐 Logs de acceso: {AccessLog.objects.count()}')
        self.stdout.write(f'  🔔 Notificaciones: {Notification.objects.count()}')
        self.stdout.write(f'  📋 Logs de actividad: {ActivityLog.objects.count()}')

    def _create_users(self, count):
        users = []
        profiles = []
        roles = ['RESIDENT', 'ADMIN', 'STAFF']  # STAFF incluye seguridad y mantenimiento
        
        # Crear usuarios en lotes
        for i in range(count):
            username = f'user{i+1}'
            if not User.objects.filter(username=username).exists():
                user = User(
                    username=username,
                    email=f'{username}@condominio.com',
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                )
                user.set_password('password123')
                users.append(user)
        
        # Insertar usuarios en lote
        if users:
            User.objects.bulk_create(users, batch_size=100)
            self.stdout.write(f'  Creados {len(users)} usuarios')
        
        # Crear perfiles para los usuarios nuevos
        all_users = list(User.objects.filter(username__startswith='user'))
        for user in all_users:
            if not hasattr(user, 'profile'):
                profiles.append(Profile(
                    user=user,
                    full_name=f'{user.first_name} {user.last_name}',
                    phone=fake.phone_number()[:30],  # Limitar longitud
                    role=random.choice(roles)
                ))
        
        if profiles:
            Profile.objects.bulk_create(profiles, batch_size=100)
            self.stdout.write(f'  Creados {len(profiles)} perfiles')
        
        return all_users

    def _create_units(self, count, users):
        units = []
        towers = ['A', 'B', 'C', 'D', 'E']
        
        for i in range(count):
            tower = random.choice(towers)
            floor = random.randint(1, 20)
            apt = random.randint(1, 4)
            code = f'{tower}{floor:02d}{apt:02d}'
            
            unit, created = Unit.objects.get_or_create(
                code=code,
                defaults={
                    'tower': tower,
                    'number': f'{floor:02d}{apt:02d}',
                    'owner': random.choice(users) if users else None
                }
            )
            if created:
                units.append(unit)
        
        return units

    def _create_expense_types(self):
        types_data = [
            {'name': 'Cuota de Mantenimiento', 'amount_default': 5000.00},
            {'name': 'Fondo de Reserva', 'amount_default': 1000.00},
            {'name': 'Servicios Comunes', 'amount_default': 2500.00},
            {'name': 'Seguridad', 'amount_default': 1500.00},
            {'name': 'Limpieza', 'amount_default': 800.00},
        ]
        
        expense_types = []
        for data in types_data:
            et, _ = ExpenseType.objects.get_or_create(
                name=data['name'],
                defaults={'amount_default': data['amount_default']}
            )
            expense_types.append(et)
        
        return expense_types

    def _create_fees(self, count, units, expense_types):
        fees = []
        start_date = timezone.now() - timedelta(days=365)
        
        for unit in units:
            for month in range(12):
                due_date = start_date + timedelta(days=30 * month)
                for expense_type in expense_types:
                    fee = Fee.objects.create(
                        unit=unit,
                        expense_type=expense_type,
                        amount=expense_type.amount_default,
                        due_date=due_date,
                        status=random.choice(['PENDING', 'PAID', 'OVERDUE'])
                    )
                    fees.append(fee)
        
        return fees[:count]

    def _create_payments(self, count, fees):
        paid_fees = [f for f in fees if f.status == 'PAID'][:count]
        
        for fee in paid_fees:
            Payment.objects.create(
                fee=fee,
                amount=fee.amount,
                payment_date=fee.due_date + timedelta(days=random.randint(1, 10)),
                payment_method=random.choice(['CASH', 'TRANSFER', 'CARD', 'MERCADOPAGO']),
                reference_number=f'PAY-{fake.uuid4()[:8]}'
            )

    def _create_notice_categories(self):
        categories_data = [
            {'name': 'Mantenimiento', 'color': '#FF5733'},
            {'name': 'Eventos', 'color': '#33FF57'},
            {'name': 'Seguridad', 'color': '#3357FF'},
            {'name': 'Administrativo', 'color': '#F39C12'},
            {'name': 'Emergencia', 'color': '#E74C3C'},
        ]
        
        categories = []
        for data in categories_data:
            cat, _ = NoticeCategory.objects.get_or_create(
                name=data['name'],
                defaults={'color': data['color']}
            )
            categories.append(cat)
        
        return categories

    def _create_notices(self, count, categories, users):
        for i in range(count):
            Notice.objects.create(
                title=fake.sentence(nb_words=6),
                content=fake.text(max_nb_chars=500),
                category=random.choice(categories),
                author=random.choice(users) if users else None,
                priority=random.choice(['LOW', 'MEDIUM', 'HIGH', 'URGENT']),
                is_active=random.choice([True, True, True, False])
            )

    def _create_common_areas(self):
        areas_data = [
            {'name': 'Piscina', 'capacity': 50},
            {'name': 'Gimnasio', 'capacity': 20},
            {'name': 'Salón de Eventos', 'capacity': 100},
            {'name': 'Cancha de Tenis', 'capacity': 4},
            {'name': 'BBQ Area', 'capacity': 30},
            {'name': 'Sala de Juegos', 'capacity': 15},
        ]
        
        areas = []
        for data in areas_data:
            area, _ = CommonArea.objects.get_or_create(
                name=data['name'],
                defaults={
                    'capacity': data['capacity'],
                    'hourly_rate': random.randint(500, 2000)
                }
            )
            areas.append(area)
        
        return areas

    def _create_reservations(self, count, common_areas, units):
        start_date = timezone.now() - timedelta(days=180)
        
        for i in range(count):
            reservation_date = start_date + timedelta(days=random.randint(0, 180))
            Reservation.objects.create(
                common_area=random.choice(common_areas),
                unit=random.choice(units),
                reservation_date=reservation_date,
                start_time=f'{random.randint(8, 18):02d}:00',
                end_time=f'{random.randint(10, 20):02d}:00',
                status=random.choice(['PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED']),
                notes=fake.sentence() if random.random() > 0.5 else ''
            )

    def _create_maintenance_requests(self, count, units, users):
        for i in range(count):
            created_at = timezone.now() - timedelta(days=random.randint(0, 365))
            status = random.choice(['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'])
            
            request = MaintenanceRequest.objects.create(
                unit=random.choice(units),
                requester=random.choice(users) if users else None,
                title=fake.sentence(nb_words=5),
                description=fake.text(max_nb_chars=300),
                category=random.choice(['PLUMBING', 'ELECTRICAL', 'CARPENTRY', 'PAINTING', 'OTHER']),
                priority=random.choice(['LOW', 'MEDIUM', 'HIGH', 'URGENT']),
                status=status,
                created_at=created_at
            )
            
            if status == 'COMPLETED':
                request.completed_at = created_at + timedelta(days=random.randint(1, 30))
                request.save()
            
            # Agregar comentarios
            if random.random() > 0.5:
                MaintenanceRequestComment.objects.create(
                    request=request,
                    author=random.choice(users) if users else None,
                    comment=fake.text(max_nb_chars=200)
                )

    def _create_vehicles_pets_family(self, units):
        for unit in random.sample(list(units), min(len(units), 80)):
            # Vehículos
            if random.random() > 0.3:
                Vehicle.objects.create(
                    unit=unit,
                    license_plate=fake.license_plate(),
                    brand=random.choice(['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan']),
                    model=fake.word(),
                    color=random.choice(['Blanco', 'Negro', 'Gris', 'Rojo', 'Azul']),
                    vehicle_type=random.choice(['CAR', 'MOTORCYCLE', 'TRUCK'])
                )
            
            # Mascotas
            if random.random() > 0.5:
                Pet.objects.create(
                    unit=unit,
                    name=fake.first_name(),
                    species=random.choice(['DOG', 'CAT', 'BIRD', 'OTHER']),
                    breed=fake.word(),
                    age=random.randint(1, 15)
                )
            
            # Familiares
            for _ in range(random.randint(1, 4)):
                FamilyMember.objects.create(
                    unit=unit,
                    full_name=fake.name(),
                    relationship=random.choice(['SPOUSE', 'CHILD', 'PARENT', 'SIBLING', 'OTHER']),
                    phone=fake.phone_number(),
                    age=random.randint(1, 80)
                )

    def _create_visitors(self, count, units):
        for i in range(count):
            entry_time = timezone.now() - timedelta(days=random.randint(0, 180), hours=random.randint(0, 23))
            has_exited = random.random() > 0.3
            
            Visitor.objects.create(
                unit=random.choice(units),
                full_name=fake.name(),
                document_id=fake.ssn(),
                entry_time=entry_time,
                exit_time=entry_time + timedelta(hours=random.randint(1, 8)) if has_exited else None,
                notes=fake.sentence() if random.random() > 0.7 else ''
            )

    def _create_security_incidents(self, count, units):
        for i in range(count):
            created_at = timezone.now() - timedelta(days=random.randint(0, 365))
            is_resolved = random.random() > 0.4
            
            SecurityIncident.objects.create(
                incident_type=random.choice(['THEFT', 'VANDALISM', 'NOISE', 'SUSPICIOUS', 'EMERGENCY', 'OTHER']),
                description=fake.text(max_nb_chars=300),
                location=fake.address(),
                severity=random.choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
                reported_by=random.choice(units).owner if random.choice(units).owner else None,
                status='RESOLVED' if is_resolved else random.choice(['PENDING', 'IN_PROGRESS']),
                created_at=created_at,
                resolved_at=created_at + timedelta(days=random.randint(1, 30)) if is_resolved else None
            )

    def _create_access_logs(self, count, units):
        for i in range(count):
            AccessLog.objects.create(
                unit=random.choice(units),
                access_type=random.choice(['ENTRY', 'EXIT', 'VISITOR', 'DELIVERY', 'MAINTENANCE']),
                person_name=fake.name(),
                vehicle_plate=fake.license_plate() if random.random() > 0.5 else '',
                timestamp=timezone.now() - timedelta(days=random.randint(0, 180), hours=random.randint(0, 23)),
                notes=fake.sentence() if random.random() > 0.7 else ''
            )

    def _create_notifications(self, count, users):
        for i in range(count):
            Notification.objects.create(
                user=random.choice(users),
                title=fake.sentence(nb_words=5),
                message=fake.text(max_nb_chars=200),
                notification_type=random.choice(['INFO', 'WARNING', 'SUCCESS', 'ERROR']),
                is_read=random.choice([True, False, False])
            )

    def _create_activity_logs(self, count, users):
        actions = [
            'USER_LOGIN', 'USER_LOGOUT', 'PAYMENT_CREATED', 'RESERVATION_CREATED',
            'MAINTENANCE_REQUEST', 'NOTICE_PUBLISHED', 'PROFILE_UPDATED'
        ]
        
        for i in range(count):
            ActivityLog.objects.create(
                user=random.choice(users),
                action=random.choice(actions),
                timestamp=timezone.now() - timedelta(days=random.randint(0, 365), hours=random.randint(0, 23)),
                ip_address=fake.ipv4()
            )
