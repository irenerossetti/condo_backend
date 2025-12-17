# core/management/commands/create_test_conversations.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Conversation, Message

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea conversaciones de prueba para el sistema de chat'

    def handle(self, *args, **options):
        # Obtener usuarios
        try:
            admin = User.objects.get(username='admin')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Usuario admin no encontrado'))
            return

        # Obtener otros usuarios
        residents = User.objects.filter(profile__role='RESIDENT')[:3]
        
        if not residents:
            self.stdout.write(self.style.WARNING('No hay residentes para crear conversaciones'))
            return

        # Crear conversación entre admin y residente
        for resident in residents:
            conversation, created = Conversation.objects.get_or_create(
                type='DIRECT',
                name=f'Chat con {resident.profile.full_name if hasattr(resident, "profile") else resident.username}',
            )
            
            if created:
                conversation.participants.add(admin, resident)
                
                # Crear algunos mensajes de prueba
                Message.objects.create(
                    conversation=conversation,
                    sender=admin,
                    type='TEXT',
                    text=f'Hola {resident.profile.full_name if hasattr(resident, "profile") else resident.username}, ¿en qué puedo ayudarte?'
                )
                
                Message.objects.create(
                    conversation=conversation,
                    sender=resident,
                    type='TEXT',
                    text='Hola, tengo una consulta sobre las cuotas del mes.'
                )
                
                Message.objects.create(
                    conversation=conversation,
                    sender=admin,
                    type='TEXT',
                    text='Claro, dime en qué puedo ayudarte con las cuotas.'
                )
                
                conversation.update_last_message(conversation.messages.last())
                
                self.stdout.write(
                    self.style.SUCCESS(f'Conversación creada con {resident.username}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Conversación con {resident.username} ya existe')
                )

        # Crear conversación grupal
        group_conv, created = Conversation.objects.get_or_create(
            type='GROUP',
            name='Grupo General - Torre A',
        )
        
        if created:
            group_conv.participants.add(admin, *residents)
            
            Message.objects.create(
                conversation=group_conv,
                sender=admin,
                type='TEXT',
                text='Bienvenidos al grupo de la Torre A. Aquí podrán comunicarse entre todos.'
            )
            
            group_conv.update_last_message(group_conv.messages.last())
            
            self.stdout.write(
                self.style.SUCCESS('Conversación grupal creada')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Conversación grupal ya existe')
            )

        self.stdout.write(
            self.style.SUCCESS('✅ Conversaciones de prueba creadas exitosamente')
        )
