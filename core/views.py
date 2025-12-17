# condominio_backend/core/views.py

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Sum, Q, Value, F, Count, DecimalField
from django.conf import settings
from django.db.models.functions import Coalesce
from decimal import Decimal
from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
import mercadopago
from django.db import models
from django.utils import timezone
import os  # 👈 Para las variables de entorno como la API Key
import base64  # 👈 Para procesar la imagen
from openai import OpenAI  # 👈 Para usar la IA
from rest_framework.decorators import api_view, permission_classes # 👈 Para crear la vista de API

from .models import (
    ActivityLog, CommonArea, ExpenseType, FamilyMember, Fee, MaintenanceRequest,
    MaintenanceRequestComment, Notice, NoticeCategory, Notification,
    Payment, Pet, Profile, Reservation, Unit, Vehicle, MaintenanceRequestAttachment,
    Visitor, SecurityIncident
)
from .serializers import (
    ActivityLogSerializer, AdminUserWriteSerializer, CommonAreaSerializer,
    ExpenseTypeSerializer, FamilyMemberSerializer, FeeSerializer,
    MaintenanceRequestCommentSerializer, MaintenanceRequestSerializer,
    NoticeCategorySerializer, NoticeSerializer,
    NotificationSerializer, MaintenanceRequestAttachmentSerializer,
    PaymentSerializer, PetSerializer, ProfileSerializer, ReservationSerializer,
    UnitSerializer, UnitDetailSerializer, UserWithProfileSerializer, VehicleSerializer
)
from .permissions import IsAdmin, IsOwnerOrAdmin
from .services.fees import register_payment

User = get_user_model()


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request):
        data = request.data
        identifier = (data.get("email") or data.get("username") or "").strip()
        password = (data.get("password") or "").strip()
        
        if not identifier or not password:
            return Response({"detail": "Faltan credenciales"}, status=status.HTTP_400_BAD_REQUEST)
        
        user_lookup = {"email__iexact": identifier} if "@" in identifier else {"username__iexact": identifier}
        user_obj = User.objects.filter(**user_lookup).first()
        
        if not user_obj:
            return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = authenticate(request, username=user_obj.username, password=password)
        
        if not user:
            return Response({"detail": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Obtener IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Registrar login exitoso con detalles completos
        ActivityLog.objects.create(
            user=user,
            action="USER_LOGIN_SUCCESS",
            description=f"Inició sesión desde {ip_address}",
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            path=request.path,
            method='POST',
            session_key=request.session.session_key if hasattr(request, 'session') else ''
        )
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.profile.full_name if hasattr(user, 'profile') else user.get_full_name()
            }
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Determinar si es logout manual o por expiración
        logout_type = request.data.get('logout_type', 'manual')
        action = 'USER_LOGOUT_MANUAL' if logout_type == 'manual' else 'USER_LOGOUT_EXPIRED'
        
        # Obtener IP del cliente
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Registrar logout con detalles
        ActivityLog.objects.create(
            user=request.user,
            action=action,
            description=f"Cerró sesión {'manualmente' if logout_type == 'manual' else 'por expiración de token'}",
            ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            path=request.path,
            method='POST',
            session_key=request.session.session_key if hasattr(request, 'session') else ''
        )
        
        return Response({"detail": "Sesión cerrada correctamente."})


class MeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    def list(self, request):
        serializer = UserWithProfileSerializer(request.user)
        return Response(serializer.data)
    @action(detail=False, methods=["patch"])
    def update_profile(self, request):
        prof, _ = Profile.objects.get_or_create(user=request.user)
        ser = ProfileSerializer(prof, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related('profile', 'vehicles', 'pets', 'family_members').all().order_by("id")
    permission_classes = [permissions.IsAdminUser]
    def get_serializer_class(self):
        return AdminUserWriteSerializer if self.action in ("create", "update", "partial_update") else UserWithProfileSerializer
    @action(detail=False, methods=['get'])
    def staff_members(self, request):
        staff_users = User.objects.filter(profile__role='STAFF').order_by('username')
        serializer = self.get_serializer(staff_users, many=True)
        return Response(serializer.data)


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.select_related("owner", "owner__profile").all().order_by("code")
    permission_classes = [IsAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'tower', 'number', 'owner__username', 'owner__profile__full_name']
    ordering_fields = ['code', 'tower', 'number', 'owner__username']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UnitDetailSerializer
        return UnitSerializer


class ExpenseTypeViewSet(viewsets.ModelViewSet):
    queryset = ExpenseType.objects.all().order_by("id")
    serializer_class = ExpenseTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_permissions(self):
        if self.action not in ('list', 'retrieve'):
            return [IsAdmin()]
        return super().get_permissions()


class FeeViewSet(viewsets.ModelViewSet):
    queryset = Fee.objects.select_related("unit", "expense_type", "unit__owner").all()
    serializer_class = FeeSerializer
    ordering = ["-issued_at"]

    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.action in ("list", "retrieve") else [IsAdmin()]
    
    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("mine") == "1" and self.request.user.is_authenticated:
            qs = qs.filter(unit__owner=self.request.user)
        if period := self.request.query_params.get("period"):
            qs = qs.filter(period=period)
        return qs

    # --- 👇 AÑADE ESTA NUEVA FUNCIÓN AQUÍ ---
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def pay(self, request, pk=None):
        try:
            fee = self.get_object()
            amount = request.data.get('amount')
            method = request.data.get('method', 'manual')
            note = request.data.get('note', 'Pago registrado por administrador.')

            if not amount:
                return Response({"detail": "El monto es requerido."}, status=status.HTTP_400_BAD_REQUEST)

            # Usamos el servicio para registrar el pago
            result = register_payment(fee_id=fee.id, amount=float(amount), method=method, note=note)
            
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class NoticeCategoryViewSet(viewsets.ModelViewSet):
    queryset = NoticeCategory.objects.all()
    serializer_class = NoticeCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_permissions(self):
        if self.action not in ('list', 'retrieve'):
            return [IsAdmin()]
        return super().get_permissions()

class NoticeViewSet(viewsets.ModelViewSet):
    serializer_class = NoticeSerializer
    def get_queryset(self):
        return Notice.objects.filter(publish_date__lte=timezone.now()).select_related("created_by").order_by("-publish_date")
    def get_permissions(self):
        return [permissions.IsAuthenticated()] if self.action in ("list", "retrieve") else [IsAdmin()]
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # 👇 AÑADE ESTA NUEVA FUNCIÓN DENTRO DE LA CLASE NoticeViewSet 👇
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_as_viewed(self, request, pk=None):
        notice = self.get_object()
        # Añadimos el usuario actual a la lista de 'viewed_by'
        notice.viewed_by.add(request.user)
        return Response({'status': 'notice marked as viewed'}, status=status.HTTP_200_OK)    


class CommonAreaViewSet(viewsets.ModelViewSet):
    queryset = CommonArea.objects.filter(is_active=True).order_by("name")
    serializer_class = CommonAreaSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return super().get_permissions()


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related("area", "user").all()
    serializer_class = ReservationSerializer
    permission_classes = [IsOwnerOrAdmin]
    def get_queryset(self):
        if self.request.user.profile.role == "ADMIN":
            return super().get_queryset().order_by("-start_time")
        return super().get_queryset().filter(user=self.request.user).order_by("-start_time")
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequest.objects.select_related(
        'unit', 'reported_by', 'assigned_to', 'completed_by'
    ).prefetch_related('comments', 'attachments').all().order_by('-created_at')
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if not (user.is_staff or getattr(user.profile, 'role', 'RESIDENT') == 'ADMIN'):
            queryset = queryset.filter(reported_by=user)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)


class MaintenanceRequestCommentViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequestComment.objects.all()
    serializer_class = MaintenanceRequestCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MaintenanceRequestAttachmentViewSet(viewsets.ModelViewSet):
    queryset = MaintenanceRequestAttachment.objects.all()
    serializer_class = MaintenanceRequestAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save()


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAdmin]


class PetViewSet(viewsets.ModelViewSet):
    queryset = Pet.objects.all()
    serializer_class = PetSerializer
    permission_classes = [IsAdmin]


class FamilyMemberViewSet(viewsets.ModelViewSet):
    queryset = FamilyMember.objects.all()
    serializer_class = FamilyMemberSerializer
    permission_classes = [IsAdmin]


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdmin]


class PageAccessLogView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        page_name = request.data.get('page_name')
        if page_name:
            ActivityLog.objects.create(user=request.user, action="PAGE_ACCESS", details=f"Accedió a: {page_name}")
        return Response(status=status.HTTP_201_CREATED)


class DashboardStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        from django.db.models import Count, Q
        from datetime import timedelta
        
        try:
            # Calculamos los totales de todas las cuotas emitidas históricamente
            fee_aggregates = Fee.objects.aggregate(
                total_issued=Coalesce(Sum('amount'), Decimal('0.0')),
                total_paid=Coalesce(Sum('payments__amount'), Decimal('0.0'))
            )

            total_issued = fee_aggregates['total_issued']
            total_paid = fee_aggregates['total_paid']
            total_outstanding = total_issued - total_paid

            # --- NUEVA LÓGICA PARA LOS INDICADORES ---
            delinquency_rate = 0
            collection_rate = 100

            if total_issued > 0:
                # Tasa de Morosidad: (Lo que se debe / Lo que se emitió) * 100
                delinquency_rate = (total_outstanding / total_issued) * 100
                # Tasa de Cobranza: (Lo que se pagó / Lo que se emitió) * 100
                collection_rate = (total_paid / total_issued) * 100

            # --- DATOS PARA GRÁFICAS ---
            
            # 1. Cuotas por estado
            fees_by_status = list(Fee.objects.values('status').annotate(count=Count('id')))
            
            # 2. Usuarios por rol
            users_by_role = list(Profile.objects.values('role').annotate(value=Count('id')))
            for item in users_by_role:
                item['name'] = dict(Profile.ROLE_CHOICES).get(item['role'], item['role'])
            
            # 3. Mantenimiento por estado
            maintenance_by_category = list(
                MaintenanceRequest.objects.values('status')
                .annotate(count=Count('id'))
                .order_by('-count')
            )
            for item in maintenance_by_category:
                item['category'] = item['status']  # Renombrar para compatibilidad con el frontend
            
            # 4. Visitantes por mes (últimos 6 meses)
            six_months_ago = timezone.now() - timedelta(days=180)
            visitors_by_month = []
            for i in range(6):
                month_start = timezone.now() - timedelta(days=30 * (5 - i))
                month_end = month_start + timedelta(days=30)
                count = Visitor.objects.filter(
                    entry_time__gte=month_start,
                    entry_time__lt=month_end
                ).count()
                visitors_by_month.append({
                    'month': month_start.strftime('%b'),
                    'visitors': count
                })
            
            # 5. Incidentes de seguridad por tipo
            incidents_by_type = list(
                SecurityIncident.objects.values('incident_type')
                .annotate(count=Count('id'))
                .order_by('-count')
            )
            for item in incidents_by_type:
                item['type'] = dict(SecurityIncident.INCIDENT_TYPES).get(item['incident_type'], item['incident_type'])
                item.pop('incident_type')

            return Response({
                "total_users": User.objects.count(),
                "active_units": Unit.objects.count(),
                "pending_fees_total": float(total_outstanding),
                "open_maintenance_requests": MaintenanceRequest.objects.filter(status__in=["PENDING", "IN_PROGRESS"]).count(),
                "delinquency_rate": round(delinquency_rate, 2),
                "collection_rate": round(collection_rate, 2),
                
                # Datos para gráficas
                "charts": {
                    "fees_by_status": fees_by_status,
                    "users_by_role": users_by_role,
                    "maintenance_by_category": maintenance_by_category,
                    "visitors_by_month": visitors_by_month,
                    "incidents_by_type": incidents_by_type,
                }
            })
        except Exception as e:
            import traceback
            print(f"Error en DashboardStatsView: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {"error": str(e), "detail": "Error al obtener estadísticas del dashboard"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FinanceReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from_period = request.query_params.get('from')
        to_period = request.query_params.get('to')
        owner_id = request.query_params.get('owner')

        queryset = Fee.objects.select_related('expense_type')

        if from_period:
            queryset = queryset.filter(period__gte=from_period)
        if to_period:
            queryset = queryset.filter(period__lte=to_period)
        if owner_id:
            queryset = queryset.filter(unit__owner_id=owner_id)

        aggregates = queryset.aggregate(
            issued=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()),
            paid=Coalesce(Sum('amount', filter=Q(status='PAID')), Value(0), output_field=DecimalField())
        )
        overall_issued = aggregates['issued']
        overall_paid = aggregates['paid']
        overall_outstanding = overall_issued - overall_paid

        by_type = list(queryset.values('expense_type__name')
            .annotate(
                type=F('expense_type__name'),
                count=Count('id'),
                issued=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()),
                paid=Coalesce(Sum('amount', filter=Q(status='PAID')), Value(0), output_field=DecimalField())
            )
            .annotate(outstanding=F('issued') - F('paid'))
            .values('type', 'count', 'issued', 'paid', 'outstanding')
            .order_by('-issued')
        )
        
        by_period = list(queryset.values('period')
            .annotate(
                issued=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()),
                paid=Coalesce(Sum('amount', filter=Q(status='PAID')), Value(0), output_field=DecimalField())
            )
            .values('period', 'issued', 'paid')
            .order_by('period')
        )

        data = {
            "overall": {
                "issued": float(overall_issued or 0),
                "paid": float(overall_paid or 0),
                "outstanding": float(overall_outstanding or 0),
            },
            "by_type": [
                {**item, 'issued': float(item['issued']), 'paid': float(item['paid']), 'outstanding': float(item['outstanding'])}
                for item in by_type
            ],
            "by_period": [
                {**item, 'issued': float(item['issued']), 'paid': float(item['paid'])}
                for item in by_period
            ],
        }
        
        return Response(data)
    
class FeePaymentPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, fee_id):
        try:
            fee_lookup = {'pk': fee_id}
            if not (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
                fee_lookup['unit__owner'] = request.user
            Fee.objects.get(**fee_lookup)
        except Fee.DoesNotExist:
            return Response({"detail": "Cuota no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        fake_link = f"https://www.mercadopago.com.ar/pagar/con/qr/{fee_id}"
        placeholder_qr_base64 = 'iVBORw0KGgoAAAANSUhEUgAAAQAAAAEAAQMAAABmvDolAAAABlBMVEX///8AAABVwtN+AAABbklEQVR4nO2WsQ3DMAxEFXqBJRgQ3QWLsAwLMEaowGBLYIZgCf5/lW6ECIZ/uW/yvB5k3zJ2lO/ncsP5P+H8IeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J8Q/hPCf0L4Twh/CeE/IfwnhP+E8J/s38A2gUzC8oVoRBAAAAAElFTkSuQmCC'
        
        mock_response = {
            "init_point": fake_link,
            "point_of_interaction": {
                "transaction_data": {
                    "qr_code_base64": placeholder_qr_base64
                }
            }
        }
        
        return Response(mock_response, status=status.HTTP_200_OK)


class MercadoPagoWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_200_OK)
    
# ... (al final del archivo, después de MercadoPagoWebhookView)

# --- Vista para Reconocimiento de Placas y Control de Acceso ---

# Configuración del cliente para la API de IA (OpenRouter)
# Lee la API Key de forma segura desde el archivo .env
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
except Exception as e:
    print(f"ERROR: No se pudo inicializar el cliente de OpenAI. Revisa tu API Key. Error: {e}")
    client = None

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser]) # O [permissions.IsAuthenticated] si cualquier usuario puede usarlo
def vehicle_recognition_view(request):
    """
    Recibe una imagen de un vehículo, extrae la placa usando IA,
    y verifica si el vehículo tiene acceso autorizado.
    """
    if not client:
        return Response(
            {"error": "El servicio de IA no está configurado correctamente en el servidor."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    image_file = request.FILES.get('vehicle_image')
    if not image_file:
        return Response({'error': 'No se proporcionó ninguna imagen.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. Convertir la imagen a formato base64 para enviarla a la API
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        # Usamos el formato "data URI" que la API de OpenAI/OpenRouter entiende
        image_data_url = f"data:{image_file.content_type};base64,{image_base64}"

        # 2. Enviar la imagen a la IA con un prompt específico para OCR de placas
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL", ""),
                "X-Title": os.getenv("SITE_NAME", ""),
            },
            model="x-ai/grok-4-fast:free",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            # ¡Este prompt es clave! Le pedimos a la IA que solo devuelva la placa.
                            "text": "Analiza esta imagen e identifica la placa del vehículo. Responde únicamente con el texto de la placa, sin espacios, guiones ni explicaciones. Si no puedes leer una placa, responde 'ILEGIBLE'."
                        },
                        {
                            "type": "image_url",
                            "image_url": { "url": image_data_url }
                        }
                    ]
                }
            ],
            max_tokens=20, # Limitamos la respuesta para que sea corta y precisa
            temperature=0.1 # Poca creatividad para que no invente placas
        )

        plate_text = completion.choices[0].message.content.strip().upper()

        if not plate_text or 'ILEGIBLE' in plate_text:
            return Response({
                'status': 'denied',
                'reason': 'Placa no detectada o ilegible.',
                'api_response': plate_text
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. Verificar si la placa existe en tu base de datos (modelo Vehicle)
        try:
            # Buscamos un vehículo que coincida con la placa leída
            # y cuyo propietario esté activo.
            vehicle = Vehicle.objects.get(plate__iexact=plate_text, owner__is_active=True)

            # ¡Éxito! El vehículo está registrado y su dueño está activo.
            return Response({
                'status': 'granted',
                'license_plate': plate_text,
                'owner_username': vehicle.owner.username,
                'vehicle_brand': vehicle.brand,
                'vehicle_model': vehicle.model
            })
        except Vehicle.DoesNotExist:
            # La placa fue leída pero no está en la base de datos o el dueño no está activo.
            return Response({
                'status': 'denied',
                'reason': 'Vehículo no autorizado.',
                'license_plate': plate_text
            }, status=status.HTTP_403_FORBIDDEN)

    except Exception as e:
        # Captura cualquier otro error (ej. la API de OpenRouter falla, etc.)
        return Response({'error': f'Ocurrió un error inesperado: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ... (al final de tus otras vistas)
from django.db.models import Count

class OccupancyReportView(APIView):
    permission_classes = [IsAdmin] # Solo los admins pueden ver este reporte

    def get(self, request):
        # Obtenemos todas las unidades, con información del dueño y contando sus vehículos/mascotas
        queryset = Unit.objects.select_related('owner', 'owner__profile').annotate(
            vehicle_count=Count('owner__vehicles', distinct=True),
            pet_count=Count('owner__pets', distinct=True)
        ).order_by('code')

        # Preparamos los datos para enviar al frontend
        report_data = []
        for unit in queryset:
            report_data.append({
                'unit_code': unit.code,
                'owner_username': unit.owner.username,
                'owner_full_name': unit.owner.profile.full_name,
                'owner_email': unit.owner.email,
                'owner_phone': unit.owner.profile.phone,
                'vehicle_count': unit.vehicle_count,
                'pet_count': unit.pet_count,
            })

        return Response(report_data)   


# --- ViewSets para Chat ---
from .serializers import ConversationSerializer, MessageSerializer
from .models import Conversation, Message, MessageReadStatus

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Solo mostrar conversaciones donde el usuario es participante
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants').order_by('-last_message_at')
    
    def perform_create(self, serializer):
        conversation = serializer.save()
        # Asegurar que el creador sea participante
        if self.request.user not in conversation.participants.all():
            conversation.participants.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_all_as_read(self, request, pk=None):
        """Marcar todos los mensajes de la conversación como leídos"""
        conversation = self.get_object()
        messages = conversation.messages.exclude(sender=request.user)
        
        for message in messages:
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=request.user
            )
        
        return Response({'status': 'marked as read'})
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Obtener mensajes de una conversación"""
        conversation = self.get_object()
        messages = conversation.messages.select_related('sender').order_by('created_at')
        
        # Paginación
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='messages')
    def create_message(self, request, pk=None):
        """Crear un mensaje en una conversación"""
        conversation = self.get_object()
        
        serializer = MessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                conversation=conversation,
                sender=request.user
            )
            
            # Actualizar último mensaje de la conversación
            conversation.update_last_message(serializer.instance)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Solo mensajes de conversaciones donde el usuario es participante
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation').order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marcar un mensaje como leído"""
        message = self.get_object()
        MessageReadStatus.objects.get_or_create(
            message=message,
            user=request.user
        )
        return Response({'status': 'marked as read'})


# Vista de prueba para exportación
class TestExportView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request):
        return Response({"message": "Test export endpoint works!"})
