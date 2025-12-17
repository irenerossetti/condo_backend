# core/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message, MessageReadStatus

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        
        # Verificar que el usuario esté autenticado
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verificar permisos
        has_permission = await self.check_permission()
        if not has_permission:
            await self.close(code=4001)
            return
        
        # Unirse al grupo de la conversación
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notificar que el usuario está online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def disconnect(self, close_code):
        # Notificar que el usuario está offline
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_offline',
                    'user_id': self.user.id
                }
            )
            
            # Salir del grupo
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'message.send':
                await self.handle_message_send(data.get('data', {}))
            elif message_type == 'typing.start':
                await self.handle_typing_start()
            elif message_type == 'typing.stop':
                await self.handle_typing_stop()
            elif message_type == 'message.read':
                await self.handle_message_read(data.get('data', {}))
            else:
                await self.send_error('INVALID_MESSAGE_TYPE', 'Tipo de mensaje inválido')
        
        except json.JSONDecodeError:
            await self.send_error('INVALID_JSON', 'JSON inválido')
        except Exception as e:
            await self.send_error('INTERNAL_ERROR', str(e))
    
    async def handle_message_send(self, data):
        text = data.get('text', '').strip()
        message_type = data.get('type', 'TEXT')
        
        if not text and message_type == 'TEXT':
            await self.send_error('EMPTY_MESSAGE', 'El mensaje no puede estar vacío')
            return
        
        # Guardar mensaje en la base de datos
        message = await self.save_message(text, message_type)
        
        if message:
            # Serializar mensaje
            message_data = await self.serialize_message(message)
            
            # Broadcast a todos en el grupo
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_new',
                    'message': message_data
                }
            )
    
    async def handle_typing_start(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_start',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def handle_typing_stop(self):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_stop',
                'user_id': self.user.id
            }
        )
    
    async def handle_message_read(self, data):
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)
            
            # Notificar al remitente
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'user_id': self.user.id,
                    'read_at': None  # Se llenará en el handler
                }
            )
    
    # Handlers para eventos del grupo
    async def message_new(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message.new',
            'data': event['message']
        }))
    
    async def typing_start(self, event):
        # No enviar al usuario que está escribiendo
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing.start',
                'data': {
                    'user_id': event['user_id'],
                    'username': event['username']
                }
            }))
    
    async def typing_stop(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing.stop',
                'data': {
                    'user_id': event['user_id']
                }
            }))
    
    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message.read',
            'data': {
                'message_id': event['message_id'],
                'user_id': event['user_id'],
                'read_at': event.get('read_at')
            }
        }))
    
    async def user_online(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user.online',
                'data': {
                    'user_id': event['user_id'],
                    'username': event.get('username')
                }
            }))
    
    async def user_offline(self, event):
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user.offline',
                'data': {
                    'user_id': event['user_id']
                }
            }))
    
    async def send_error(self, error_code, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'data': {
                'code': error_code,
                'message': message
            }
        }))
    
    # Database operations
    @database_sync_to_async
    def check_permission(self):
        """Verifica que el usuario sea participante de la conversación"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, text, message_type):
        """Guarda el mensaje en la base de datos"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                type=message_type,
                text=text
            )
            
            # Actualizar último mensaje de la conversación
            conversation.update_last_message(message)
            
            return message
        except Exception as e:
            print(f"Error saving message: {e}")
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """Serializa el mensaje para enviar por WebSocket"""
        return {
            'id': message.id,
            'sender': {
                'id': message.sender.id,
                'username': message.sender.username,
                'full_name': message.sender.profile.full_name if hasattr(message.sender, 'profile') else message.sender.username,
            },
            'type': message.type,
            'text': message.text,
            'attachment': None,  # TODO: Implementar cuando se agregue subida de archivos
            'created_at': message.created_at.isoformat(),
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            'is_deleted': message.is_deleted,
            'is_read': False
        }
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Marca un mensaje como leído"""
        try:
            message = Message.objects.get(id=message_id)
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=self.user
            )
            return True
        except Message.DoesNotExist:
            return False
