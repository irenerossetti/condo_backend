from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Profile, Unit, ExpenseType, NoticeCategory
from faker import Faker

User = get_user_model()
fake = Faker('es_ES')


class Command(BaseCommand):
    help = 'Crea datos de demostración para el sistema'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creando datos de demostración...'))

        # 1. Crear tipos de gastos
        expense_types = [
            {'name': 'Cuota de Mantenimiento', 'amount_default': 5000.00},
            {'name': 'Fondo de Reserva', 'amount_default': 1000.00},
            {'name': 'Servicios Comunes', 'amount_default': 2500.00},
        ]
        
        for et_data in expense_types:
            ExpenseType.objects.get_or_create(
                name=et_data['name'],
                defaults={'amount_default': et_data['amount_default']}
            )
        self.stdout.write(self.style.SUCCESS(f'✓ Creados {len(expense_types)} tipos de gastos'))

        # 2. Crear categorías de avisos
        categories = [
            {'name': 'Mantenimiento', 'color': '#FF5733'},
            {'name': 'Eventos', 'color': '#33FF57'},
            {'name': 'Seguridad', 'color': '#3357FF'},
            {'name': 'Administrativo', 'color': '#F39C12'},
        ]
        
        for cat_data in categories:
            NoticeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'color': cat_data['color']}
            )
        self.stdout.write(self.style.SUCCESS(f'✓ Creadas {len(categories)} categorías de avisos'))

        # 3. Crear usuario administrador de prueba
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@condominio.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            Profile.objects.create(
                user=admin_user,
                full_name='Administrador del Condominio',
                phone='+54 11 1234-5678',
                role='ADMIN'
            )
            self.stdout.write(self.style.SUCCESS('✓ Usuario admin creado (usuario: admin, contraseña: admin123)'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Usuario admin ya existe'))

        # 4. Crear usuarios residentes de prueba
        residents_created = 0
        for i in range(1, 6):
            username = f'residente{i}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@condominio.com',
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                }
            )
            if created:
                user.set_password('residente123')
                user.save()
                Profile.objects.create(
                    user=user,
                    full_name=f'{user.first_name} {user.last_name}',
                    phone=fake.phone_number(),
                    role='RESIDENT'
                )
                residents_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Creados {residents_created} usuarios residentes'))

        # 5. Crear unidades de prueba
        units_created = 0
        residents = User.objects.filter(profile__role='RESIDENT')
        towers = ['A', 'B', 'C']
        
        for tower in towers:
            for floor in range(1, 6):
                for apt in range(1, 3):
                    code = f'{tower}{floor}0{apt}'
                    owner = residents[units_created % len(residents)] if residents else admin_user
                    
                    unit, created = Unit.objects.get_or_create(
                        code=code,
                        defaults={
                            'tower': tower,
                            'number': f'{floor}0{apt}',
                            'owner': owner
                        }
                    )
                    if created:
                        units_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'✓ Creadas {units_created} unidades'))

        self.stdout.write(self.style.SUCCESS('\n¡Datos de demostración creados exitosamente!'))
        self.stdout.write(self.style.SUCCESS('\nCredenciales de acceso:'))
        self.stdout.write(self.style.SUCCESS('  Admin: usuario=admin, contraseña=admin123'))
        self.stdout.write(self.style.SUCCESS('  Residentes: usuario=residente1-5, contraseña=residente123'))
