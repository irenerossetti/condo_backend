# Condominio Backend

Backend para sistema de gestión de condominios construido con Django REST Framework.

## Requisitos

- Python 3.11+
- PostgreSQL 13+
- pip

## Instalación

1. Crear y activar entorno virtual:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
# Copiar el archivo de ejemplo
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac

# Editar .env con tus credenciales
```

4. Ejecutar migraciones:
```bash
python manage.py migrate
```

5. Crear superusuario:
```bash
python manage.py createsuperuser
```

6. Ejecutar servidor de desarrollo:
```bash
python manage.py runserver
```

El servidor estará disponible en http://127.0.0.1:8000

## Estructura del Proyecto

- `config/` - Configuración principal de Django
- `core/` - Aplicación principal con modelos y vistas
- `todos/` - Aplicación de tareas (opcional)
- `media/` - Archivos subidos por usuarios
- `staticfiles/` - Archivos estáticos recopilados

## API Endpoints

- `/api/auth/login/` - Login
- `/api/auth/logout/` - Logout
- `/api/me/` - Información del usuario actual
- `/api/users/` - Gestión de usuarios
- `/api/units/` - Gestión de unidades
- `/api/fees/` - Gestión de cuotas
- `/api/notices/` - Avisos
- `/api/maintenance-requests/` - Solicitudes de mantenimiento
- `/api/reservations/` - Reservas de áreas comunes

## Deployment

Para producción, asegúrate de:

1. Cambiar `DEBUG=0` en `.env`
2. Configurar `SECRET_KEY` segura
3. Configurar `ALLOWED_HOSTS` con tu dominio
4. Ejecutar `python manage.py collectstatic`
5. Usar un servidor WSGI como Gunicorn
