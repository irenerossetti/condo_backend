# core/management/commands/generate_chart_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import random
from core.models import SecurityIncident, Visitor, MaintenanceRequest, Unit

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera datos de prueba para las gráficas del dashboard'

    def handle(self, *args, **options):
        self.stdout.write('🎨 Generando datos para gráficas...')
        
        # Obtener un usuario admin para asignar incidentes
        admin_user = User.objects.filter(profile__role='ADMIN').first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('❌ No hay usuarios admin. Ejecuta setup_demo primero.'))
            return
        
        # Obtener usuarios residentes
        resident_users = list(User.objects.filter(profile__role='RESIDENT')[:10])
        if not resident_users:
            resident_users = [admin_user]
        
        # Obtener unidades
        units = list(Unit.objects.all()[:20])
        if not units:
            self.stdout.write(self.style.WARNING('⚠️ No hay unidades. Algunas gráficas no tendrán datos.'))
            units = [None]
        
        # 1. Generar incidentes de seguridad
        incident_types = [
            'UNAUTHORIZED_PERSON',
            'LOOSE_PET',
            'PET_WASTE',
            'WRONG_PARKING',
            'SUSPICIOUS_BEHAVIOR',
            'UNAUTHORIZED_VEHICLE',
            'OTHER'
        ]
        
        self.stdout.write('📊 Generando incidentes de seguridad...')
        for _ in range(20):
            incident_type = random.choice(incident_types)
            days_ago = random.randint(0, 180)
            detected_at = timezone.now() - timedelta(days=days_ago)
            
            SecurityIncident.objects.create(
                incident_type=incident_type,
                description=f'Incidente detectado por IA: {incident_type}',
                detected_at=detected_at,
                location=f'Área {random.choice(["A", "B", "C", "D"])} - Piso {random.randint(1, 10)}',
                confidence_score=random.uniform(0.7, 0.99),
                is_resolved=random.choice([True, False]),
                resolved_by=admin_user if random.choice([True, False]) else None
            )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Creados {SecurityIncident.objects.count()} incidentes'))
        
        # 2. Generar visitantes (últimos 6 meses)
        self.stdout.write('📊 Generando visitantes...')
        for month in range(6):
            month_start = timezone.now() - timedelta(days=30 * (5 - month))
            visitors_count = random.randint(10, 50)
            
            for _ in range(visitors_count):
                days_offset = random.randint(0, 29)
                entry_time = month_start + timedelta(days=days_offset, hours=random.randint(8, 20))
                
                Visitor.objects.create(
                    full_name=f'Visitante {random.randint(1000, 9999)}',
                    document_id=f'V{random.randint(10000000, 99999999)}',
                    entry_time=entry_time,
                    exit_time=entry_time + timedelta(hours=random.randint(1, 4)) if random.choice([True, False]) else None,
                    notes=random.choice(['Visita familiar', 'Entrega', 'Servicio técnico', 'Reunión']),
                    authorized_by=admin_user,
                    is_authorized=True
                )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Creados {Visitor.objects.count()} visitantes'))
        
        # 3. Generar solicitudes de mantenimiento
        self.stdout.write('📊 Generando solicitudes de mantenimiento...')
        statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        categories = ['Plomería', 'Electricidad', 'Pintura', 'Jardinería', 'Limpieza', 'Seguridad']
        
        for i in range(30):
            days_ago = random.randint(0, 180)
            created_at = timezone.now() - timedelta(days=days_ago)
            unit = random.choice(units) if units[0] is not None else None
            
            MaintenanceRequest.objects.create(
                title=f'{random.choice(categories)} - Solicitud #{i+1}',
                description=f'Descripción de la solicitud de {random.choice(categories).lower()}',
                unit=unit,
                reported_by=random.choice(resident_users),
                status=random.choice(statuses),
                created_at=created_at
            )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Creadas {MaintenanceRequest.objects.count()} solicitudes de mantenimiento'))
        
        self.stdout.write(self.style.SUCCESS('🎉 Datos de gráficas generados exitosamente!'))
