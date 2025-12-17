from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

# --- FUNCIÓN AUXILIAR (definida al principio) ---
def maintenance_attachment_path(instance, filename):
    return f'maintenance/{instance.request_id}/{filename}'

# --- MODELOS DE LA APLICACIÓN ---

class Profile(models.Model):
    ROLE_CHOICES = [("ADMIN", "Administrador"), ("RESIDENT", "Residente"), ("STAFF", "Personal")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="RESIDENT")
    def __str__(self): return f"{self.full_name or self.user.username} ({self.role})"

class Unit(models.Model):
    code = models.CharField(max_length=30, unique=True)
    tower = models.CharField(max_length=30)
    number = models.CharField(max_length=30)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="units")
    def __str__(self): return self.code

class ExpenseType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    amount_default = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Fee(models.Model):
    STATUS = [("ISSUED", "Emitida"), ("PAID", "Pagada"), ("OVERDUE", "Vencida")]
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="fees")
    expense_type = models.ForeignKey(ExpenseType, on_delete=models.PROTECT)
    period = models.CharField(max_length=7)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=8, choices=STATUS, default="ISSUED")
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    class Meta:
        unique_together = ("unit", "expense_type", "period")
    def __str__(self): return f"{self.unit} {self.period} {self.expense_type}"

class Payment(models.Model):
    fee = models.ForeignKey(Fee, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=30, default="cash")
    note = models.TextField(blank=True)

class NoticeCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default="#888888", help_text="Color en formato hexadecimal, ej. #FF5733")
    def __str__(self): return self.name
    class Meta:
        ordering = ["name"]

class Notice(models.Model):
    title = models.CharField(max_length=120)
    body = models.TextField()
    publish_date = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    category = models.ForeignKey(NoticeCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="notices")
    viewed_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='viewed_notices', blank=True)
    
    class Meta:
        ordering = ["-publish_date"]

class CommonArea(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Reservation(models.Model):
    area = models.ForeignKey(CommonArea, on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.area.name} - {self.user.username} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"

class MaintenanceRequest(models.Model):
    STATUS_CHOICES = [("PENDING", "Pendiente"), ("IN_PROGRESS", "En Progreso"), ("COMPLETED", "Completado")]
    PRIORITY_CHOICES = [("BAJA", "Baja"), ("MEDIA", "Media"), ("ALTA", "Alta"), ("URGENTE", "Urgente")]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="MEDIA", verbose_name="Prioridad")
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_requests")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="maintenance_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_maintenance_requests")
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_maintenance_requests")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de finalización")
    def __str__(self): return self.title

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('USER_LOGIN_SUCCESS', 'Inicio de sesión exitoso'),
        ('USER_LOGOUT_MANUAL', 'Cierre de sesión manual'),
        ('USER_LOGOUT_EXPIRED', 'Cierre de sesión por expiración'),
        ('PAGE_ACCESS', 'Acceso a página'),
        ('CREATE', 'Creación de registro'),
        ('UPDATE', 'Actualización de registro'),
        ('DELETE', 'Eliminación de registro'),
        ('PAYMENT_CREATED', 'Pago creado'),
        ('RESERVATION_CREATED', 'Reservación creada'),
        ('MAINTENANCE_REQUEST', 'Solicitud de mantenimiento'),
        ('NOTICE_PUBLISHED', 'Aviso publicado'),
        ('PROFILE_UPDATED', 'Perfil actualizado'),
        ('PASSWORD_CHANGED', 'Contraseña cambiada'),
        ('AI_FACE_RECOGNITION', 'Reconocimiento facial'),
        ('AI_VEHICLE_RECOGNITION', 'Reconocimiento de vehículo'),
        ('AI_VISITOR_REGISTERED', 'Visitante registrado con IA'),
        ('AI_ANOMALY_DETECTED', 'Anomalía detectada'),
        ('SECURITY_INCIDENT', 'Incidente de seguridad'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.CharField(max_length=255, blank=True)  # Descripción corta de la acción
    details = models.TextField(blank=True, null=True)  # Detalles adicionales en JSON
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)  # Navegador/dispositivo
    path = models.CharField(max_length=255, blank=True)  # URL/ruta accedida
    method = models.CharField(max_length=10, blank=True)  # GET, POST, PUT, DELETE
    timestamp = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)  # Para rastrear sesiones

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self): 
        return f'{self.user.username} - {self.get_action_display()} - {self.ip_address} - {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'

class MaintenanceRequestComment(models.Model):
    request = models.ForeignKey('MaintenanceRequest', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='maintenance_comments')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
    def __str__(self): return f"Comentario de {self.user.username} en solicitud {self.request.id}"

class Vehicle(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vehicles")
    plate = models.CharField(max_length=20, default='', help_text="Placa del vehículo")
    brand = models.CharField(max_length=50, blank=True, help_text="Marca (ej. Toyota)")
    # 👇 LA COMILLA FALTANTE ESTABA AQUÍ
    model = models.CharField(max_length=50, blank=True, help_text="Modelo (ej. Corolla)")
    color = models.CharField(max_length=30, blank=True)
    def __str__(self): return f"{self.plate} ({self.owner.username})"

class Pet(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pets")
    name = models.CharField(max_length=100, default='')
    species = models.CharField(max_length=50, blank=True, help_text="Especie (ej. Perro, Gato)")
    breed = models.CharField(max_length=50, blank=True, help_text="Raza (ej. Labrador)")
    def __str__(self): return f"{self.name} ({self.owner.username})"

class FamilyMember(models.Model):
    resident = models.ForeignKey(User, on_delete=models.CASCADE, related_name="family_members")
    full_name = models.CharField(max_length=200, blank=True, default='')
    relationship = models.CharField(max_length=50, blank=True, default='', help_text="Parentesco (ej. Esposo/a, Hijo/a)")
    phone = models.CharField(max_length=30, blank=True)
    def __str__(self): return f"{self.full_name} ({self.relationship} de {self.resident.username})"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True, help_text="URL a la que debe dirigir la notificación")
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return f"Notificación para {self.user.username}: {self.message}"

class MaintenanceRequestAttachment(models.Model):
    request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.ImageField(upload_to=maintenance_attachment_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Adjunto para la solicitud {self.request.id}"

# ... (al final de tus otros modelos como Profile, Unit, etc.)

class AuthorizedVehicle(models.Model):
    license_plate = models.CharField(max_length=10, unique=True, verbose_name="Placa")
    owner_name = models.CharField(max_length=100, verbose_name="Nombre del Propietario")
    is_active = models.BooleanField(default=True, verbose_name="Acceso Activo")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.license_plate} - {self.owner_name}"

# --- MODELOS PARA IA Y SEGURIDAD ---

class FaceEncoding(models.Model):
    """Almacena encodings faciales de residentes para reconocimiento"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="face_encodings")
    encoding_data = models.TextField(help_text="Encoding facial en formato JSON")
    photo = models.ImageField(upload_to='face_photos/', help_text="Foto de referencia")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Face encoding para {self.user.username}"

class Visitor(models.Model):
    """Registro de visitantes con foto y reconocimiento automático"""
    full_name = models.CharField(max_length=200)
    document_id = models.CharField(max_length=50, blank=True)
    photo = models.ImageField(upload_to='visitors/')
    visiting_unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, related_name="visitors")
    entry_time = models.DateTimeField(auto_now_add=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    authorized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="authorized_visitors")
    notes = models.TextField(blank=True)
    is_authorized = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-entry_time']
    
    def __str__(self):
        return f"{self.full_name} - {self.entry_time.strftime('%Y-%m-%d %H:%M')}"

class SecurityIncident(models.Model):
    """Incidentes detectados por IA"""
    INCIDENT_TYPES = [
        ('UNAUTHORIZED_PERSON', 'Persona No Autorizada'),
        ('LOOSE_PET', 'Mascota Suelta'),
        ('PET_WASTE', 'Mascota Haciendo Necesidades'),
        ('WRONG_PARKING', 'Vehículo Mal Estacionado'),
        ('SUSPICIOUS_BEHAVIOR', 'Comportamiento Sospechoso'),
        ('UNAUTHORIZED_VEHICLE', 'Vehículo No Autorizado'),
        ('OTHER', 'Otro'),
    ]
    
    incident_type = models.CharField(max_length=30, choices=INCIDENT_TYPES)
    description = models.TextField()
    photo = models.ImageField(upload_to='incidents/', null=True, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=200, blank=True, help_text="Ubicación del incidente")
    confidence_score = models.FloatField(default=0.0, help_text="Nivel de confianza de la IA (0-1)")
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_incidents")
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-detected_at']
    
    def __str__(self):
        return f"{self.get_incident_type_display()} - {self.detected_at.strftime('%Y-%m-%d %H:%M')}"

class AccessLog(models.Model):
    """Log de accesos con reconocimiento facial/vehicular"""
    ACCESS_TYPES = [
        ('FACIAL', 'Reconocimiento Facial'),
        ('VEHICLE', 'Reconocimiento Vehicular'),
        ('MANUAL', 'Manual'),
        ('VISITOR', 'Visitante'),
    ]
    
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs")
    visitor = models.ForeignKey(Visitor, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_logs")
    timestamp = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to='access_logs/', null=True, blank=True)
    was_granted = models.BooleanField(default=True)
    confidence_score = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        person = self.user.username if self.user else (self.visitor.full_name if self.visitor else "Desconocido")
        return f"{self.get_access_type_display()} - {person} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
  


# --- MODELOS PARA SISTEMA DE CHAT ---

class Conversation(models.Model):
    """Conversación entre usuarios (directa o grupo)"""
    CONVERSATION_TYPES = [
        ('DIRECT', 'Conversación Directa'),
        ('GROUP', 'Grupo'),
    ]
    
    type = models.CharField(max_length=10, choices=CONVERSATION_TYPES)
    name = models.CharField(max_length=200, blank=True, help_text="Nombre del grupo (solo para grupos)")
    description = models.TextField(blank=True, help_text="Descripción del grupo")
    participants = models.ManyToManyField(User, related_name='conversations')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Metadata para optimización
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_preview = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-last_message_at']
        indexes = [
            models.Index(fields=['-last_message_at']),
            models.Index(fields=['type']),
        ]
    
    def __str__(self):
        if self.type == 'DIRECT':
            return f"Chat directo #{self.id}"
        return self.name or f"Grupo #{self.id}"
    
    def get_other_user(self, current_user):
        """Para conversaciones directas, obtiene el otro usuario"""
        if self.type == 'DIRECT':
            return self.participants.exclude(id=current_user.id).first()
        return None
    
    def update_last_message(self, message):
        """Actualiza el preview del último mensaje"""
        self.last_message_at = message.created_at
        if message.type == 'TEXT':
            self.last_message_preview = message.text[:200]
        elif message.type == 'IMAGE':
            self.last_message_preview = "📷 Imagen"
        elif message.type == 'FILE':
            self.last_message_preview = f"📎 {message.attachment_name}"
        else:
            self.last_message_preview = message.text[:200]
        self.save(update_fields=['last_message_at', 'last_message_preview'])


class Message(models.Model):
    """Mensaje dentro de una conversación"""
    MESSAGE_TYPES = [
        ('TEXT', 'Texto'),
        ('IMAGE', 'Imagen'),
        ('FILE', 'Archivo'),
        ('SYSTEM', 'Sistema'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='TEXT')
    text = models.TextField(blank=True)
    
    # Adjuntos
    attachment = models.FileField(upload_to='chat_attachments/%Y/%m/', null=True, blank=True)
    attachment_thumbnail = models.ImageField(upload_to='chat_thumbnails/%Y/%m/', null=True, blank=True)
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_size = models.IntegerField(null=True, blank=True, help_text="Tamaño en bytes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Estado
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender']),
        ]
    
    def __str__(self):
        return f"Mensaje de {self.sender.username} en {self.conversation}"
    
    def mark_as_read_by(self, user):
        """Marca el mensaje como leído por un usuario"""
        MessageReadStatus.objects.get_or_create(message=self, user=user)
    
    def is_read_by(self, user):
        """Verifica si el mensaje fue leído por un usuario"""
        return MessageReadStatus.objects.filter(message=self, user=user).exists()
    
    def get_read_by_users(self):
        """Obtiene la lista de usuarios que leyeron el mensaje"""
        return User.objects.filter(read_messages__message=self)


class MessageReadStatus(models.Model):
    """Estado de lectura de mensajes"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_messages')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')
        indexes = [
            models.Index(fields=['message', 'user']),
        ]
        verbose_name_plural = "Message read statuses"
    
    def __str__(self):
        return f"{self.user.username} leyó mensaje #{self.message.id}"
