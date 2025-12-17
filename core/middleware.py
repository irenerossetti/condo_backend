# core/middleware.py
from django.utils.deprecation import MiddlewareMixin
from .models import ActivityLog
import json


def get_client_ip(request):
    """Obtiene la IP real del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class ActivityLogMiddleware(MiddlewareMixin):
    """
    Middleware que registra automáticamente todas las acciones de los usuarios
    """
    
    # Rutas que NO queremos registrar (para evitar spam)
    EXCLUDED_PATHS = [
        '/api/activity-logs/',  # No registrar cuando consultan los logs
        '/api/me/',  # No registrar consultas de perfil constantes
        '/static/',
        '/media/',
        '/admin/jsi18n/',
    ]
    
    # Mapeo de rutas a acciones
    PATH_ACTION_MAP = {
        '/api/auth/login/': 'USER_LOGIN_SUCCESS',
        '/api/auth/logout/': 'USER_LOGOUT_MANUAL',
        '/api/fees/': 'PAGE_ACCESS',
        '/api/units/': 'PAGE_ACCESS',
        '/api/notices/': 'PAGE_ACCESS',
        '/api/reservations/': 'PAGE_ACCESS',
        '/api/maintenance-requests/': 'PAGE_ACCESS',
        '/api/ai/visitors/': 'PAGE_ACCESS',
        '/api/ai/security-incidents/': 'PAGE_ACCESS',
        '/api/access-control/recognize-vehicle/': 'AI_VEHICLE_RECOGNITION',
        '/api/ai/recognize-face/': 'AI_FACE_RECOGNITION',
        '/api/ai/register-visitor/': 'AI_VISITOR_REGISTERED',
        '/api/ai/detect-anomaly/': 'AI_ANOMALY_DETECTED',
    }
    
    def process_response(self, request, response):
        # Solo registrar si el usuario está autenticado
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        
        # No registrar rutas excluidas
        path = request.path
        if any(excluded in path for excluded in self.EXCLUDED_PATHS):
            return response
        
        # Solo registrar métodos importantes
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE', 'GET']:
            return response
        
        # Solo registrar respuestas exitosas (200-299) o creaciones (201)
        if not (200 <= response.status_code < 300):
            return response
        
        try:
            # Determinar la acción basada en la ruta y método
            action = self._determine_action(request)
            
            if action:
                # Obtener descripción legible
                description = self._get_description(request, action)
                
                # Crear el log
                ActivityLog.objects.create(
                    user=request.user,
                    action=action,
                    description=description,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    path=path,
                    method=request.method,
                    session_key=request.session.session_key if hasattr(request, 'session') else '',
                    details=self._get_details(request)
                )
        except Exception as e:
            # No queremos que un error en el logging rompa la aplicación
            print(f"Error logging activity: {e}")
        
        return response
    
    def _determine_action(self, request):
        """Determina qué acción registrar basado en la ruta y método"""
        path = request.path
        method = request.method
        
        # Buscar coincidencia exacta en el mapa
        for route, action in self.PATH_ACTION_MAP.items():
            if route in path:
                return action
        
        # Determinar acción por método HTTP
        if method == 'POST':
            if '/payment' in path:
                return 'PAYMENT_CREATED'
            elif '/reservation' in path:
                return 'RESERVATION_CREATED'
            elif '/maintenance' in path:
                return 'MAINTENANCE_REQUEST'
            elif '/notice' in path:
                return 'NOTICE_PUBLISHED'
            return 'CREATE'
        elif method in ['PUT', 'PATCH']:
            if '/profile' in path:
                return 'PROFILE_UPDATED'
            elif '/password' in path:
                return 'PASSWORD_CHANGED'
            return 'UPDATE'
        elif method == 'DELETE':
            return 'DELETE'
        elif method == 'GET':
            # Solo registrar GETs importantes
            if any(keyword in path for keyword in ['/dashboard', '/reports', '/security']):
                return 'PAGE_ACCESS'
        
        return None
    
    def _get_description(self, request, action):
        """Genera una descripción legible de la acción"""
        path = request.path
        method = request.method
        
        # Descripciones personalizadas
        if action == 'PAGE_ACCESS':
            page_name = path.split('/')[-2] if path.endswith('/') else path.split('/')[-1]
            return f'Accedió a {page_name}'
        elif action == 'USER_LOGIN_SUCCESS':
            return 'Inició sesión exitosamente'
        elif action == 'USER_LOGOUT_MANUAL':
            return 'Cerró sesión manualmente'
        elif action == 'CREATE':
            resource = path.split('/')[-2] if path.endswith('/') else path.split('/')[-1]
            return f'Creó {resource}'
        elif action == 'UPDATE':
            resource = path.split('/')[2] if len(path.split('/')) > 2 else 'registro'
            return f'Actualizó {resource}'
        elif action == 'DELETE':
            resource = path.split('/')[2] if len(path.split('/')) > 2 else 'registro'
            return f'Eliminó {resource}'
        
        return f'{method} {path}'
    
    def _get_details(self, request):
        """Obtiene detalles adicionales de la petición"""
        details = {}
        
        # Agregar parámetros de query
        if request.GET:
            details['query_params'] = dict(request.GET)
        
        # Agregar algunos datos del body (sin contraseñas)
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if hasattr(request, 'data'):
                    body = dict(request.data)
                    # Remover campos sensibles
                    sensitive_fields = ['password', 'token', 'secret', 'key']
                    for field in sensitive_fields:
                        body.pop(field, None)
                    details['body'] = body
            except:
                pass
        
        return json.dumps(details) if details else ''
