# Condominium Management System - Backend

Backend del sistema de gestión de condominios construido con Django REST Framework y Django Channels.

## 🚀 Características

- ✅ API RESTful completa
- ✅ Autenticación JWT
- ✅ WebSockets para chat en tiempo real
- ✅ Funcionalidades de IA para seguridad
- ✅ Reportes avanzados con exportación (PDF, Excel, CSV)
- ✅ Gestión completa de condominios

## 📋 Requisitos

- Python 3.11+
- PostgreSQL (o SQLite para desarrollo)
- Redis (para WebSockets)

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/irenerossetti/condo_backend.git
cd condo_backend
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus configuraciones:

```env
SECRET_KEY=tu-secret-key-aqui
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174
```

### 5. Ejecutar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Cargar datos de prueba (opcional)

```bash
python manage.py setup_demo
```

### 8. Iniciar servidor

```bash
python manage.py runserver 8003
```

El servidor estará disponible en `http://localhost:8003`

## 📚 Endpoints Principales

### Autenticación
- `POST /api/auth/login/` - Login
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/token/` - Obtener token JWT
- `POST /api/auth/refresh/` - Refrescar token

### Reportes
- `GET /api/reports/advanced/` - Reportes avanzados
- `GET /api/reports/export/` - Exportar reportes (PDF/Excel/CSV)
- `GET /api/reports/dashboard-stats/` - Estadísticas del dashboard

### Chat (WebSocket)
- `ws://localhost:8003/ws/chat/<conversation_id>/` - Chat en tiempo real

### IA y Seguridad
- `POST /api/ai/recognize-face/` - Reconocimiento facial
- `POST /api/ai/detect-anomaly/` - Detección de anomalías
- `POST /api/ai/analyze-image/` - Análisis de imágenes

## ⚙️ Configuración Importante

### Exportación de Reportes

Para que la exportación funcione correctamente, asegúrate de que `config/settings.py` tenga:

```python
REST_FRAMEWORK = {
    ...
    "URL_FORMAT_OVERRIDE": None,  # Crítico para exportación
}
```

### WebSockets

Asegúrate de tener Redis corriendo:

```bash
redis-server
```

## 🧪 Testing

```bash
python manage.py test
```

## 📦 Dependencias Principales

- Django 5.2
- djangorestframework
- channels
- channels-redis
- djangorestframework-simplejwt
- reportlab (PDF)
- openpyxl (Excel)
- Pillow (imágenes)

## 🔗 Repositorio Frontend

Frontend: https://github.com/irenerossetti/condo_frontend.git

## 📝 Licencia

Privado - Uso interno

---

**Última actualización**: Diciembre 2025
