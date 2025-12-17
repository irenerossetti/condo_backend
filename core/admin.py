from django.contrib import admin
from .models import (
    Profile, Unit, ExpenseType, Fee, Payment, Notice,
    CommonArea, Reservation, MaintenanceRequest, Vehicle,
    Pet, FamilyMember, NoticeCategory, Notification,
    ActivityLog, MaintenanceRequestComment, MaintenanceRequestAttachment,
    FaceEncoding, Visitor, SecurityIncident, AccessLog
)

@admin.register(ExpenseType)
class ExpenseTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "amount_default", "active")
    search_fields = ("name",)
    list_filter = ("active",)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "tower", "number", "owner")
    search_fields = ("code", "tower", "number", "owner__username")

@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ("id", "unit", "expense_type", "period", "amount", "status", "issued_at", "due_date")
    list_filter = ("status", "period", "expense_type")
    search_fields = ("unit__code", "unit__owner__username")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "fee", "amount", "paid_at", "method")
    list_filter = ("method",)
    search_fields = ("fee__unit__code",)

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "publish_date", "created_by")
    search_fields = ("title", "body")

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "phone", "role")
    list_filter = ("role",)
    search_fields = ("full_name", "user__username", "user__email")


@admin.register(CommonArea)
class CommonAreaAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "capacity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("id", "area", "user", "start_time", "end_time")
    list_filter = ("area",)
    search_fields = ("user__username", "notes")

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'unit', 'reported_by', 'created_at')
    list_filter = ('status', 'unit')    

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("id", "plate", "brand", "model", "owner")
    search_fields = ("plate", "brand", "model", "owner__username")
    list_filter = ("brand",)

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "species", "breed", "owner")
    search_fields = ("name", "species", "breed", "owner__username")
    list_filter = ("species",)

@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "relationship", "resident", "phone")
    search_fields = ("full_name", "relationship", "resident__username")

@admin.register(NoticeCategory)
class NoticeCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "color")
    search_fields = ("name",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "message")

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action", "timestamp")
    list_filter = ("action", "timestamp")
    search_fields = ("user__username", "action", "details")
    readonly_fields = ("user", "action", "timestamp", "details")

@admin.register(MaintenanceRequestComment)
class MaintenanceRequestCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "user", "created_at")
    search_fields = ("request__title", "user__username", "body")

@admin.register(MaintenanceRequestAttachment)
class MaintenanceRequestAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "uploaded_at")
    readonly_fields = ("uploaded_at",)   


# --- Administración de IA y Seguridad ---

@admin.register(FaceEncoding)
class FaceEncodingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__username', 'user__profile__full_name']
    readonly_fields = ['created_at']

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'visiting_unit', 'entry_time', 'exit_time', 'is_authorized']
    list_filter = ['is_authorized', 'entry_time', 'visiting_unit']
    search_fields = ['full_name', 'document_id', 'visiting_unit__code']
    readonly_fields = ['entry_time']
    date_hierarchy = 'entry_time'

@admin.register(SecurityIncident)
class SecurityIncidentAdmin(admin.ModelAdmin):
    list_display = ['id', 'incident_type', 'location', 'detected_at', 'confidence_score', 'is_resolved']
    list_filter = ['incident_type', 'is_resolved', 'detected_at']
    search_fields = ['description', 'location']
    readonly_fields = ['detected_at']
    date_hierarchy = 'detected_at'
    
    fieldsets = (
        ('Información del Incidente', {
            'fields': ('incident_type', 'description', 'photo', 'location', 'confidence_score')
        }),
        ('Estado', {
            'fields': ('is_resolved', 'resolved_by', 'resolved_at', 'notes')
        }),
        ('Metadatos', {
            'fields': ('detected_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'access_type', 'get_person', 'timestamp', 'was_granted', 'confidence_score']
    list_filter = ['access_type', 'was_granted', 'timestamp']
    search_fields = ['user__username', 'visitor__full_name', 'notes']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def get_person(self, obj):
        if obj.user:
            return f"👤 {obj.user.username}"
        elif obj.visitor:
            return f"🚶 {obj.visitor.full_name}"
        return "Desconocido"
    get_person.short_description = 'Persona'
