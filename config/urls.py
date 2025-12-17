# config/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core import views as v
from core import views_ai as ai  # 👈 Importar vistas de IA
from core import views_reports as reports  # 👈 Importar vistas de reportes
from django.conf import settings # 👈 Importa settings
from django.conf.urls.static import static # 👈 Importa static

router = DefaultRouter()
router.register(r"me", v.MeViewSet, basename="me")
router.register(r"users", v.UserViewSet)
router.register(r"units", v.UnitViewSet)   
router.register(r"expense-types", v.ExpenseTypeViewSet)
router.register(r"fees", v.FeeViewSet)
router.register(r"notices", v.NoticeViewSet, basename="notice")
router.register(r"notice-categories", v.NoticeCategoryViewSet, basename="noticecategory")
router.register(r"common-areas", v.CommonAreaViewSet)
router.register(r"reservations", v.ReservationViewSet)
router.register(r"maintenance-requests", v.MaintenanceRequestViewSet)
# En config/urls.py, dentro de los registros del router
router.register(r"activity-logs", v.ActivityLogViewSet, basename="activitylog")
router.register(r"maintenance-request-comments", v.MaintenanceRequestCommentViewSet)
router.register(r"vehicles", v.VehicleViewSet, basename="vehicle")
router.register(r"pets", v.PetViewSet, basename="pet")
router.register(r"family-members", v.FamilyMemberViewSet, basename="familymember")
router.register(r"notifications", v.NotificationViewSet, basename="notification")
router.register(r"maintenance-attachments", v.MaintenanceRequestAttachmentViewSet, basename="maintenanceattachment")

# Registros de Chat
router.register(r"conversations", v.ConversationViewSet, basename="conversation")
router.register(r"messages", v.MessageViewSet, basename="message")

# Registros de IA y Seguridad
router.register(r"ai/face-encodings", ai.FaceEncodingViewSet, basename="face-encoding")
router.register(r"ai/visitors", ai.VisitorViewSet, basename="visitor")
router.register(r"ai/security-incidents", ai.SecurityIncidentViewSet, basename="security-incident")
router.register(r"ai/access-logs", ai.AccessLogViewSet, basename="access-log")

urlpatterns = [
    path("admin/", admin.site.urls),

    # Login propio
    path("api/auth/login/", v.LoginView.as_view()),
    path("api/auth/logout/", v.LogoutView.as_view(), name='auth-logout'), # 👈 Nueva línea
    path("api/log/page-access/", v.PageAccessLogView.as_view(), name='page-access-log'), # 👈 Nueva ruta
    # Rutas de Control de Acceso con IA
    path("api/access-control/recognize-vehicle/", v.vehicle_recognition_view, name='recognize-vehicle'),
    path("api/ai/recognize-face/", ai.facial_recognition_view, name='recognize-face'),
    path("api/ai/register-visitor/", ai.register_visitor_with_ai, name='register-visitor-ai'),
    path("api/ai/detect-anomaly/", ai.detect_anomaly, name='detect-anomaly'),
    path("api/ai/predict-delinquency/", ai.predict_delinquency, name='predict-delinquency'),
    path("api/ai/analyze-image/", ai.analyze_image_with_ai, name='analyze-image'),
    # Opcional: endpoints de SimpleJWT (útiles para pruebas)
    path("api/auth/token/", TokenObtainPairView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/reports/finance/", v.FinanceReportView.as_view()),  # <-- NUEVO
    path("api/reports/occupancy/", v.OccupancyReportView.as_view(), name='report-occupancy'),
    path("api/reports/dashboard-stats/", v.DashboardStatsView.as_view()),
    path("api/reports/export/", reports.ExportReportView.as_view(), name='direct-export-report'),  # Export endpoint
    
    path("api/fees/<int:fee_id>/create-payment-preference/", v.FeePaymentPreferenceView.as_view()),
    path("api/payments/webhook/mercadopago/", v.MercadoPagoWebhookView.as_view()),
    
    # Core URLs deben ir ANTES del router
    path("api/", include("core.urls")),
    # Router debe ir al final
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)