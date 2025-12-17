# condominio_backend/core/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from django.db.models import Sum
from django.db import transaction
from .models import (
    Profile, Unit, ExpenseType, Fee, Payment, Notice,
    CommonArea, Reservation, MaintenanceRequest, ActivityLog, MaintenanceRequestComment,
    Vehicle, Pet, FamilyMember, NoticeCategory, Notification, MaintenanceRequestAttachment,
    FaceEncoding, Visitor, SecurityIncident, AccessLog, Conversation, Message, MessageReadStatus
)
User = get_user_model()

# --- Serializers para modelos relacionados ---
class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class PetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pet
        fields = '__all__'

class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = '__all__'

# --- Serializers Principales ---
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "is_staff", "date_joined"]

class UserLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["full_name", "phone", "role"]

class UserWithProfileSerializer(UserSerializer):
    profile = ProfileSerializer(read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True)
    pets = PetSerializer(many=True, read_only=True)
    family_members = FamilyMemberSerializer(many=True, read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["profile", "vehicles", "pets", "family_members"]

class AdminUserWriteSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.ChoiceField(write_only=True, choices=Profile.ROLE_CHOICES, required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "full_name", "phone", "role", "is_active"]
        extra_kwargs = { 'username': {'required': False}, 'email': {'required': False} }

    @transaction.atomic
    def create(self, validated_data):
        profile_data = {
            "full_name": validated_data.pop("full_name", ""),
            "phone": validated_data.pop("phone", ""),
            "role": validated_data.pop("role", "RESIDENT"),
        }
        password = validated_data.pop("password", None)
        user_instance = User.objects.create_user(**validated_data, password=password)
        Profile.objects.create(user=user_instance, **profile_data)
        return user_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        
        password = validated_data.get('password')
        if password:
            instance.set_password(password)
        
        instance.save()

        profile_instance, _ = Profile.objects.get_or_create(user=instance)
        profile_instance.full_name = validated_data.get('full_name', profile_instance.full_name)
        profile_instance.phone = validated_data.get('phone', profile_instance.phone)
        profile_instance.role = validated_data.get('role', profile_instance.role)
        profile_instance.save()

        return instance

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "paid_at", "method", "note"]

class FeeSerializer(serializers.ModelSerializer):
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    owner_username = serializers.CharField(source="unit.owner.username", read_only=True)
    expense_type_name = serializers.CharField(source="expense_type.name", read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    total_paid = serializers.SerializerMethodField()

    class Meta:
        model = Fee
        fields = [ "id", "unit", "unit_code", "owner_username", "expense_type", "expense_type_name", "period", "amount", "status", "issued_at", "due_date", "payments", "total_paid" ]
        read_only_fields = ["id", "status", "issued_at"]

    def get_total_paid(self, obj):
        return obj.payments.aggregate(total=Sum('amount'))['total'] or 0

class MaintenanceRequestCommentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = MaintenanceRequestComment
        fields = ['id', 'request', 'user', 'user_username', 'body', 'created_at']
        read_only_fields = ['user', 'request']

class MaintenanceRequestAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequestAttachment
        fields = ['id', 'file', 'uploaded_at']

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    reported_by_username = serializers.CharField(source="reported_by.username", read_only=True)
    assigned_to_username = serializers.CharField(source="assigned_to.username", read_only=True)
    completed_by_username = serializers.CharField(source="completed_by.username", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    comments = MaintenanceRequestCommentSerializer(many=True, read_only=True)
    attachments = MaintenanceRequestAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = '__all__'
        read_only_fields = ['reported_by']

# --- ESTAS SON LAS CLASES IMPORTANTES PARA LA VISTA DE UNIDADES ---
class UnitSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    owner_full_name = serializers.CharField(source="owner.profile.full_name", read_only=True)

    class Meta:
        model = Unit
        fields = ["id", "code", "tower", "number", "owner", "owner_username", "owner_full_name"]
        read_only_fields = ["id"]

class UnitDetailSerializer(UnitSerializer):
    owner = UserWithProfileSerializer(read_only=True)
    fees = FeeSerializer(many=True, read_only=True)
    maintenance_requests = MaintenanceRequestSerializer(many=True, read_only=True)

    class Meta(UnitSerializer.Meta):
        fields = UnitSerializer.Meta.fields + ["owner", "fees", "maintenance_requests"]

class ExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = ["id", "name", "amount_default", "active"]

class NoticeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = NoticeCategory
        fields = ["id", "name", "color"]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'created_at', 'link']

class NoticeSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    category_color = serializers.CharField(source="category.color", read_only=True, allow_null=True)
    viewed_by = UserLiteSerializer(many=True, read_only=True)

    class Meta:
        model = Notice
        fields = [ "id", "title", "body", "publish_date", "created_by", "created_by_username", "category", "category_name", "category_color", "viewed_by" ]
        read_only_fields = ["id", "created_by", "created_by_username"]

class CommonAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommonArea
        fields = ["id", "name", "description", "capacity", "is_active"]

class ReservationSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Reservation
        fields = [ "id", "area", "area_name", "user", "user_username", "start_time", "end_time", "notes", "created_at" ]
        read_only_fields = ["user", "created_at"]

    def validate(self, data):
        start_time = data.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = data.get('end_time', getattr(self.instance, 'end_time', None))
        area = data.get('area', getattr(self.instance, 'area', None))

        if not all([start_time, end_time, area]):
            return data

        if start_time >= end_time:
            raise serializers.ValidationError("La hora de finalización debe ser posterior a la de inicio.")
        
        if start_time < timezone.now():
            raise serializers.ValidationError("No se pueden crear o modificar reservas en el pasado.")

        conflicting = Reservation.objects.filter(
            area=area,
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        
        if self.instance:
            conflicting = conflicting.exclude(pk=self.instance.pk)

        if conflicting.exists():
            raise serializers.ValidationError("Este horario ya está ocupado. Por favor, elige otro.")
            
        return data

class ActivityLogSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    user_full_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            "id", "user", "user_username", "user_full_name",
            "action", "action_display", "description",
            "ip_address", "user_agent", "path", "method",
            "timestamp", "session_key", "details"
        ]
        read_only_fields = fields
    
    def get_user_full_name(self, obj):
        if hasattr(obj.user, 'profile') and obj.user.profile.full_name:
            return obj.user.profile.full_name
        return obj.user.get_full_name() or obj.user.username

# --- Serializers para IA y Seguridad ---

class FaceEncodingSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = FaceEncoding
        fields = ['id', 'user', 'user_username', 'encoding_data', 'photo', 'created_at', 'is_active']
        read_only_fields = ['created_at']

class VisitorSerializer(serializers.ModelSerializer):
    unit_code = serializers.CharField(source='visiting_unit.code', read_only=True)
    authorized_by_username = serializers.CharField(source='authorized_by.username', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = Visitor
        fields = [
            'id', 'full_name', 'document_id', 'photo', 'visiting_unit', 'unit_code',
            'entry_time', 'exit_time', 'duration', 'authorized_by', 'authorized_by_username',
            'notes', 'is_authorized'
        ]
        read_only_fields = ['entry_time']
    
    def get_duration(self, obj):
        if obj.exit_time:
            delta = obj.exit_time - obj.entry_time
            hours = delta.total_seconds() / 3600
            return round(hours, 2)
        return None

class SecurityIncidentSerializer(serializers.ModelSerializer):
    incident_type_display = serializers.CharField(source='get_incident_type_display', read_only=True)
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True)
    
    class Meta:
        model = SecurityIncident
        fields = [
            'id', 'incident_type', 'incident_type_display', 'description', 'photo',
            'detected_at', 'location', 'confidence_score', 'is_resolved',
            'resolved_by', 'resolved_by_username', 'resolved_at', 'notes'
        ]
        read_only_fields = ['detected_at']

class AccessLogSerializer(serializers.ModelSerializer):
    access_type_display = serializers.CharField(source='get_access_type_display', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    visitor_name = serializers.CharField(source='visitor.full_name', read_only=True)
    
    class Meta:
        model = AccessLog
        fields = [
            'id', 'access_type', 'access_type_display', 'user', 'user_username',
            'visitor', 'visitor_name', 'timestamp', 'photo', 'was_granted',
            'confidence_score', 'notes'
        ]
        read_only_fields = ['timestamp']


# --- Serializers para Chat ---
class MessageSenderSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='profile.full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name']

class MessageSerializer(serializers.ModelSerializer):
    sender = MessageSenderSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'type', 'text', 
                  'attachment', 'created_at', 'edited_at', 'is_deleted']
        read_only_fields = ['sender', 'created_at', 'edited_at']

class ConversationSerializer(serializers.ModelSerializer):
    participants = UserLiteSerializer(many=True, read_only=True)
    participant_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=User.objects.all(), 
        write_only=True,
        source='participants'
    )
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    title = serializers.CharField(source='name', required=False)
    
    class Meta:
        model = Conversation
        fields = ['id', 'type', 'name', 'title', 'participants', 'participant_ids', 
                  'created_at', 'last_message_at', 'last_message_preview', 'unread_count']
        read_only_fields = ['created_at', 'last_message_at']
    
    def get_last_message_preview(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        return last_msg.text[:50] if last_msg else None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        # Contar mensajes no leídos por el usuario actual
        from .models import MessageReadStatus
        read_message_ids = MessageReadStatus.objects.filter(
            user=request.user,
            message__conversation=obj
        ).values_list('message_id', flat=True)
        
        return obj.messages.exclude(
            id__in=read_message_ids
        ).exclude(
            sender=request.user
        ).count()
