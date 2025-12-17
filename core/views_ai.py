# condominio_backend/core/views_ai.py
"""
Vistas para funcionalidades de Inteligencia Artificial y Visión Artificial
"""

import os
import base64
import json
from decimal import Decimal
from django.utils import timezone
from django.db.models import Avg, Count, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from openai import OpenAI

from .models import (
    FaceEncoding, Visitor, SecurityIncident, AccessLog,
    Vehicle, Fee, User, Unit, Notification
)
from .serializers import (
    FaceEncodingSerializer, VisitorSerializer, SecurityIncidentSerializer,
    AccessLogSerializer
)
from .permissions import IsAdmin

# Configuración del cliente de IA
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
except Exception as e:
    print(f"ERROR: No se pudo inicializar el cliente de OpenAI. Error: {e}")
    client = None


# ============================================
# RECONOCIMIENTO FACIAL
# ============================================

class FaceEncodingViewSet(viewsets.ModelViewSet):
    """Gestión de encodings faciales de residentes"""
    queryset = FaceEncoding.objects.all().order_by('-created_at')
    serializer_class = FaceEncodingSerializer
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def facial_recognition_view(request):
    """
    Reconoce a una persona por su rostro usando IA.
    Recibe una foto y determina si es un residente autorizado.
    """
    if not client:
        return Response(
            {"error": "El servicio de IA no está configurado."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    image_file = request.FILES.get('face_image')
    if not image_file:
        return Response(
            {'error': 'No se proporcionó ninguna imagen.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Convertir imagen a base64
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_data_url = f"data:{image_file.content_type};base64,{image_base64}"

        # Obtener lista de residentes para comparar
        residents = User.objects.filter(is_active=True, profile__role='RESIDENT')
        resident_names = ", ".join([u.profile.full_name or u.username for u in residents[:20]])

        # Llamar a la IA para identificar a la persona
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL", ""),
                "X-Title": os.getenv("SITE_NAME", ""),
            },
            model="x-ai/grok-vision-beta",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analiza esta imagen y describe a la persona que ves.
                            Indica: género aproximado, edad aproximada, características distintivas.
                            Si puedes identificar si es una de estas personas: {resident_names}.
                            Responde en formato JSON con: {{"descripcion": "...", "confianza": 0.0-1.0, "es_residente": true/false}}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url}
                        }
                    ]
                }
            ],
            max_tokens=200,
            temperature=0.3
        )

        ai_response = completion.choices[0].message.content.strip()
        
        # Intentar parsear la respuesta como JSON
        try:
            result = json.loads(ai_response)
        except:
            result = {
                "descripcion": ai_response,
                "confianza": 0.5,
                "es_residente": False
            }

        # Registrar el acceso
        AccessLog.objects.create(
            access_type='FACIAL',
            timestamp=timezone.now(),
            was_granted=result.get('es_residente', False),
            confidence_score=result.get('confianza', 0.0),
            notes=result.get('descripcion', '')
        )

        return Response({
            'status': 'granted' if result.get('es_residente') else 'denied',
            'description': result.get('descripcion'),
            'confidence': result.get('confianza'),
            'is_resident': result.get('es_residente'),
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return Response(
            {'error': f'Error al procesar la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# CONTROL DE VISITANTES
# ============================================

class VisitorViewSet(viewsets.ModelViewSet):
    """Gestión de visitantes con registro fotográfico"""
    queryset = Visitor.objects.all().order_by('-entry_time')
    serializer_class = VisitorSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        # Filtrar por unidad si el usuario no es admin
        if not (self.request.user.is_staff or getattr(self.request.user.profile, 'role', '') == 'ADMIN'):
            qs = qs.filter(visiting_unit__owner=self.request.user)
        
        # Filtros opcionales
        if self.request.query_params.get('active') == '1':
            qs = qs.filter(exit_time__isnull=True)
        
        return qs

    @action(detail=True, methods=['post'])
    def register_exit(self, request, pk=None):
        """Registrar salida de un visitante"""
        visitor = self.get_object()
        visitor.exit_time = timezone.now()
        visitor.save()
        
        return Response({
            'status': 'success',
            'message': 'Salida registrada correctamente',
            'exit_time': visitor.exit_time.isoformat()
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def register_visitor_with_ai(request):
    """
    Registra un visitante automáticamente usando IA para extraer información de la foto.
    """
    if not client:
        return Response(
            {"error": "El servicio de IA no está configurado."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    image_file = request.FILES.get('visitor_photo')
    unit_id = request.data.get('unit_id')
    
    if not image_file or not unit_id:
        return Response(
            {'error': 'Se requiere foto del visitante y unidad a visitar.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Verificar que la unidad existe
        unit = Unit.objects.get(id=unit_id)
        
        # Convertir imagen a base64
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_data_url = f"data:{image_file.content_type};base64,{image_base64}"

        # Llamar a la IA para analizar al visitante
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL", ""),
                "X-Title": os.getenv("SITE_NAME", ""),
            },
            model="x-ai/grok-vision-beta",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analiza esta foto de un visitante y proporciona:
                            1. Descripción física (género, edad aproximada, vestimenta)
                            2. Si lleva algún objeto visible (bolso, paquete, etc.)
                            3. Nivel de confianza en la identificación (0.0-1.0)
                            Responde en formato JSON: {"descripcion": "...", "objetos": "...", "confianza": 0.0}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url}
                        }
                    ]
                }
            ],
            max_tokens=150,
            temperature=0.3
        )

        ai_response = completion.choices[0].message.content.strip()
        
        try:
            ai_data = json.loads(ai_response)
        except:
            ai_data = {"descripcion": ai_response, "confianza": 0.5}

        # Guardar la imagen temporalmente para crear el visitante
        image_file.seek(0)  # Resetear el puntero del archivo
        
        # Crear el registro del visitante
        visitor = Visitor.objects.create(
            full_name=request.data.get('full_name', 'Visitante'),
            document_id=request.data.get('document_id', ''),
            photo=image_file,
            visiting_unit=unit,
            authorized_by=request.user,
            is_authorized=True,
            notes=f"IA: {ai_data.get('descripcion', '')}"
        )

        # Crear log de acceso
        AccessLog.objects.create(
            access_type='VISITOR',
            visitor=visitor,
            was_granted=True,
            confidence_score=ai_data.get('confianza', 0.0),
            notes=ai_data.get('descripcion', '')
        )

        # Notificar al propietario de la unidad
        Notification.objects.create(
            user=unit.owner,
            message=f"Visitante registrado para su unidad {unit.code}: {visitor.full_name}",
            link=f"/visitors/{visitor.id}"
        )

        return Response({
            'status': 'success',
            'visitor_id': visitor.id,
            'ai_analysis': ai_data,
            'message': 'Visitante registrado correctamente'
        }, status=status.HTTP_201_CREATED)

    except Unit.DoesNotExist:
        return Response(
            {'error': 'Unidad no encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Error al registrar visitante: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# DETECCIÓN DE ANOMALÍAS
# ============================================

class SecurityIncidentViewSet(viewsets.ModelViewSet):
    """Gestión de incidentes de seguridad detectados por IA"""
    queryset = SecurityIncident.objects.all().order_by('-detected_at')
    serializer_class = SecurityIncidentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def resolve(self, request, pk=None):
        """Marcar un incidente como resuelto"""
        incident = self.get_object()
        incident.is_resolved = True
        incident.resolved_by = request.user
        incident.resolved_at = timezone.now()
        incident.notes = request.data.get('notes', incident.notes)
        incident.save()
        
        return Response({
            'status': 'success',
            'message': 'Incidente marcado como resuelto'
        })


@api_view(['POST'])
@permission_classes([IsAdmin])
def detect_anomaly(request):
    """
    Analiza una imagen para detectar anomalías (mascotas sueltas, vehículos mal estacionados, etc.)
    """
    if not client:
        return Response(
            {"error": "El servicio de IA no está configurado."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    image_file = request.FILES.get('image')
    location = request.data.get('location', 'Área común')
    
    if not image_file:
        return Response(
            {'error': 'No se proporcionó ninguna imagen.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Convertir imagen a base64
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_data_url = f"data:{image_file.content_type};base64,{image_base64}"

        # Llamar a la IA para detectar anomalías
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL", ""),
                "X-Title": os.getenv("SITE_NAME", ""),
            },
            model="x-ai/grok-vision-beta",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analiza esta imagen de un condominio y detecta anomalías:
                            - Mascotas sueltas sin correa
                            - Mascotas haciendo necesidades en áreas comunes
                            - Vehículos mal estacionados (en zonas prohibidas, doble fila, etc.)
                            - Personas en áreas restringidas
                            - Comportamiento sospechoso
                            - Basura o desorden
                            
                            Responde en JSON:
                            {
                                "anomalia_detectada": true/false,
                                "tipo": "LOOSE_PET|PET_WASTE|WRONG_PARKING|UNAUTHORIZED_PERSON|SUSPICIOUS_BEHAVIOR|OTHER",
                                "descripcion": "descripción detallada",
                                "confianza": 0.0-1.0,
                                "gravedad": "BAJA|MEDIA|ALTA"
                            }"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url}
                        }
                    ]
                }
            ],
            max_tokens=250,
            temperature=0.2
        )

        ai_response = completion.choices[0].message.content.strip()
        
        try:
            result = json.loads(ai_response)
        except:
            result = {
                "anomalia_detectada": False,
                "descripcion": ai_response,
                "confianza": 0.5
            }

        # Si se detectó una anomalía, crear el incidente
        if result.get('anomalia_detectada'):
            image_file.seek(0)  # Resetear el puntero
            
            incident = SecurityIncident.objects.create(
                incident_type=result.get('tipo', 'OTHER'),
                description=result.get('descripcion', ''),
                photo=image_file,
                location=location,
                confidence_score=result.get('confianza', 0.0)
            )

            # Notificar a los administradores
            admins = User.objects.filter(Q(is_staff=True) | Q(profile__role='ADMIN'))
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    message=f"⚠️ Incidente detectado: {incident.get_incident_type_display()} en {location}",
                    link=f"/security/incidents/{incident.id}"
                )

            return Response({
                'status': 'anomaly_detected',
                'incident_id': incident.id,
                'incident_type': result.get('tipo'),
                'description': result.get('descripcion'),
                'confidence': result.get('confianza'),
                'severity': result.get('gravedad', 'MEDIA')
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'status': 'no_anomaly',
                'message': 'No se detectaron anomalías en la imagen',
                'ai_analysis': result.get('descripcion')
            })

    except Exception as e:
        return Response(
            {'error': f'Error al analizar la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# LOGS DE ACCESO
# ============================================

class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Visualización de logs de acceso"""
    queryset = AccessLog.objects.all().order_by('-timestamp')
    serializer_class = AccessLogSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filtros opcionales
        access_type = self.request.query_params.get('type')
        if access_type:
            qs = qs.filter(access_type=access_type)
        
        granted = self.request.query_params.get('granted')
        if granted:
            qs = qs.filter(was_granted=(granted == '1'))
        
        return qs


# ============================================
# ANALÍTICA PREDICTIVA
# ============================================

@api_view(['GET'])
@permission_classes([IsAdmin])
def predict_delinquency(request):
    """
    Predice qué residentes tienen mayor probabilidad de caer en morosidad
    usando análisis de patrones históricos.
    """
    try:
        # Obtener todos los residentes con sus estadísticas de pago
        residents = User.objects.filter(profile__role='RESIDENT', is_active=True)
        predictions = []

        for resident in residents:
            # Obtener cuotas del residente
            fees = Fee.objects.filter(unit__owner=resident)
            total_fees = fees.count()
            
            if total_fees == 0:
                continue

            # Calcular métricas
            paid_fees = fees.filter(status='PAID').count()
            overdue_fees = fees.filter(status='OVERDUE').count()
            payment_rate = (paid_fees / total_fees) * 100 if total_fees > 0 else 0
            
            # Calcular días promedio de retraso
            overdue_days_avg = 0
            if overdue_fees > 0:
                from datetime import date
                overdue_list = fees.filter(status='OVERDUE', due_date__isnull=False)
                if overdue_list.exists():
                    total_days = sum([(date.today() - f.due_date).days for f in overdue_list])
                    overdue_days_avg = total_days / overdue_fees

            # Calcular score de riesgo (0-100, donde 100 es alto riesgo)
            risk_score = 0
            
            # Factor 1: Tasa de pago (40% del score)
            risk_score += (100 - payment_rate) * 0.4
            
            # Factor 2: Cuotas vencidas actuales (30% del score)
            current_overdue_ratio = (overdue_fees / total_fees) * 100 if total_fees > 0 else 0
            risk_score += current_overdue_ratio * 0.3
            
            # Factor 3: Días promedio de retraso (30% del score)
            if overdue_days_avg > 0:
                # Normalizar: 30 días = 100% de este factor
                risk_score += min((overdue_days_avg / 30) * 100, 100) * 0.3

            # Clasificar el riesgo
            if risk_score >= 70:
                risk_level = 'ALTO'
            elif risk_score >= 40:
                risk_level = 'MEDIO'
            else:
                risk_level = 'BAJO'

            predictions.append({
                'user_id': resident.id,
                'username': resident.username,
                'full_name': resident.profile.full_name,
                'risk_score': round(risk_score, 2),
                'risk_level': risk_level,
                'payment_rate': round(payment_rate, 2),
                'total_fees': total_fees,
                'paid_fees': paid_fees,
                'overdue_fees': overdue_fees,
                'avg_overdue_days': round(overdue_days_avg, 1),
                'recommendation': _get_recommendation(risk_level, overdue_fees)
            })

        # Ordenar por score de riesgo descendente
        predictions.sort(key=lambda x: x['risk_score'], reverse=True)

        return Response({
            'total_residents': len(predictions),
            'high_risk_count': len([p for p in predictions if p['risk_level'] == 'ALTO']),
            'medium_risk_count': len([p for p in predictions if p['risk_level'] == 'MEDIO']),
            'low_risk_count': len([p for p in predictions if p['risk_level'] == 'BAJO']),
            'predictions': predictions
        })

    except Exception as e:
        return Response(
            {'error': f'Error al generar predicciones: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _get_recommendation(risk_level, overdue_count):
    """Genera recomendaciones basadas en el nivel de riesgo"""
    if risk_level == 'ALTO':
        return f"⚠️ Contactar urgentemente. Tiene {overdue_count} cuotas vencidas. Considerar plan de pagos."
    elif risk_level == 'MEDIO':
        return f"⚡ Enviar recordatorio. Monitorear de cerca. {overdue_count} cuotas vencidas."
    else:
        return "✅ Buen historial de pagos. Mantener seguimiento regular."


@api_view(['POST'])
@permission_classes([IsAdmin])
def analyze_image_with_ai(request):
    """
    Endpoint genérico para analizar cualquier imagen con IA.
    Útil para casos de uso personalizados.
    """
    if not client:
        return Response(
            {"error": "El servicio de IA no está configurado."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    image_file = request.FILES.get('image')
    prompt = request.data.get('prompt', 'Describe esta imagen en detalle.')
    
    if not image_file:
        return Response(
            {'error': 'No se proporcionó ninguna imagen.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Convertir imagen a base64
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        image_data_url = f"data:{image_file.content_type};base64,{image_base64}"

        # Llamar a la IA
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.getenv("SITE_URL", ""),
                "X-Title": os.getenv("SITE_NAME", ""),
            },
            model="x-ai/grok-vision-beta",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}}
                    ]
                }
            ],
            max_tokens=300,
            temperature=0.5
        )

        ai_response = completion.choices[0].message.content.strip()

        return Response({
            'status': 'success',
            'analysis': ai_response,
            'prompt_used': prompt
        })

    except Exception as e:
        return Response(
            {'error': f'Error al analizar la imagen: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
