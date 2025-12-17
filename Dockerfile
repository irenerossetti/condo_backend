# Usamos una imagen oficial de Python
FROM python:3.11-slim

# Establecemos variables de entorno para producción
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Creamos un directorio para la app
WORKDIR /app

# Copiamos e instalamos las dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el proyecto
COPY . /app/

# El comando que ejecutará Google para iniciar tu servidor
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "config.wsgi:application"]