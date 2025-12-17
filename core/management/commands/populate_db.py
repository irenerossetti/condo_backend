import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker
from core.models import Profile, Unit, Vehicle, Pet, CommonArea, ExpenseType, Notice, MaintenanceRequest, Fee, Payment

User = get_user_model()

class Command(BaseCommand):
    help = 'Populates the database with a large, realistic set of test data including financial history.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting database population process ---'))

        # --- ORDEN DE BORRADO CORREGIDO ---
        self.stdout.write('Step 1: Cleaning old data...')
        Payment.objects.all().delete()
        Fee.objects.all().delete()
        MaintenanceRequest.objects.all().delete()
        Notice.objects.all().delete()
        Vehicle.objects.all().delete()
        Pet.objects.all().delete()
        Unit.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        CommonArea.objects.all().delete()
        ExpenseType.objects.all().delete()

        fake = Faker('es_ES')

        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('FATAL: No superuser found. Please run "python manage.py createsuperuser" first.'))
            return

        # --- Crear 75 Residentes ---
        self.stdout.write('Step 2: Creating 75 residents...')
        residents = []
        for i in range(75):
            first_name, last_name = fake.first_name(), fake.last_name()
            username = f"{first_name.lower()}.{last_name.lower()}{i}"
            user = User.objects.create_user(username=username, email=f"{username}@example.com", password='password123', first_name=first_name, last_name=last_name)
            Profile.objects.create(user=user, role='RESIDENT', full_name=f"{first_name} {last_name}", phone=fake.phone_number())
            residents.append(user)
        self.stdout.write(self.style.SUCCESS(f'   > Created {len(residents)} residents.'))
        
        staff_user = User.objects.create_user(username='juan.perez', email='staff@condo.com', password='password123', first_name='Juan', last_name='Pérez')
        Profile.objects.create(user=staff_user, role='STAFF', full_name='Juan Pérez', phone=fake.phone_number())

        # --- Crear Unidades ---
        self.stdout.write('Step 3: Creating 75 units...')
        units = []
        for i, resident in enumerate(residents):
            tower = ['A', 'B', 'C', 'D', 'E'][i // 15]
            number = f"{(i % 15) + 1:02d}"
            unit, _ = Unit.objects.get_or_create(code=f'T{tower}-{number}', defaults={'tower': tower, 'number': number, 'owner': resident})
            units.append(unit)
        self.stdout.write(self.style.SUCCESS(f'   > Created {len(units)} units.'))

        # --- Crear Vehículos y Mascotas ---
        self.stdout.write('Step 4: Creating vehicles and pets...')
        for resident in residents:
            Vehicle.objects.create(owner=resident, plate=fake.license_plate(), brand=random.choice(['Toyota', 'Suzuki', 'Nissan']), model=random.choice(['Corolla', 'Swift', 'Sentra']), color=fake.safe_color_name())
            Pet.objects.create(owner=resident, name=fake.first_name(), species=random.choice(['Perro', 'Gato']))
        
        # --- Crear Áreas Comunes y Tipos de Expensas ---
        self.stdout.write('Step 5: Creating common areas and expense types...')
        CommonArea.objects.create(name='Piscina', capacity=20)
        CommonArea.objects.create(name='Gimnasio', capacity=15)
        CommonArea.objects.create(name='Salón de Eventos', capacity=50)
        expense_types = [
            ExpenseType.objects.create(name='Cuota de Mantenimiento', amount_default=550.50),
            ExpenseType.objects.create(name='Fondo de Reserva', amount_default=120.00),
            ExpenseType.objects.create(name='Cuota Extraordinaria (Pintura)', amount_default=250.00)
        ]

        # --- Crear Historial de Deudas y Pagos ---
        self.stdout.write('Step 6: Creating financial history (fees and payments)...')
        today = date.today()
        for i in range(6, -1, -1):
            # Usamos timedelta para calcular la fecha de cada mes pasado
            current_month_date = today - timedelta(days=i*30)
            period = current_month_date.strftime("%Y-%m")
            self.stdout.write(f'   > Generating data for period: {period}')

            for unit in units:
                for et in expense_types:
                    # La cuota extraordinaria solo se cobra cada 3 meses
                    if 'Extraordinaria' in et.name and current_month_date.month % 3 != 0:
                        continue

                    fee = Fee.objects.create(unit=unit, expense_type=et, period=period, amount=et.amount_default, status='ISSUED')
                    
                    if i > 0: # No simular pagos para el mes actual para que aparezcan deudas
                        rand_val = random.random()
                        if rand_val > 0.85:
                            fee.status = 'OVERDUE'
                            fee.save()
                        elif rand_val > 0.3:
                            Payment.objects.create(fee=fee, amount=fee.amount, method='bank_transfer')
                            fee.status = 'PAID'
                            fee.save()
                        else:
                            partial_amount = round(float(fee.amount) * random.uniform(0.3, 0.7), 2)
                            Payment.objects.create(fee=fee, amount=partial_amount, method='cash')
                            fee.status = 'OVERDUE'
                            fee.save()
        
        # --- Crear Avisos y Mantenimientos ---
        self.stdout.write('Step 7: Creating notices and maintenance requests...')
        Notice.objects.create(created_by=admin_user, title='Mantenimiento de Piscina', body='La piscina estará cerrada este sábado.')
        MaintenanceRequest.objects.create(reported_by=random.choice(residents), unit=random.choice(units), title='Foco quemado en pasillo', description='El foco del pasillo del 3er piso, Torre A, está quemado.', status='PENDING', priority='BAJA')
        MaintenanceRequest.objects.create(reported_by=random.choice(residents), unit=random.choice(units), title='Fuga de agua en baño', description='Hay una fuga constante en el lavamanos.', status='IN_PROGRESS', priority='ALTA', assigned_to=staff_user)

        self.stdout.write(self.style.SUCCESS('\n--- Database population complete! ---'))