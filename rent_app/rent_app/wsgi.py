"""
WSGI config for rent_app project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""
import os
import sys

# Agrega la ruta del proyecto y del módulo principal
sys.path.append('/home/render/INMUEBLESESIME/RENT_APP')  # Ruta absoluta a la carpeta RENT_APP
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RENT_APP.settings')  # Ajusta al nombre correcto

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()