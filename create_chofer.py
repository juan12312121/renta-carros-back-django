import os
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rentacarros.settings')
django.setup()

from api.models import Usuario
from django.contrib.auth.hashers import make_password

username = 'chofer_test'
email = 'chofer@test.com'
password = 'Password123!'

if not Usuario.objects.filter(username=username).exists():
    chofer = Usuario.objects.create(
        username=username,
        email=email,
        password_hash=make_password(password),
        nombre='Juan',
        apellido='Chofer',
        role='chofer',
        verificado=True,
        activo=True,
        activo_chofer=True,
        numero_licencia_conducir='LIC-123456'
    )
    print(f"Chofer creado exitosamente: {username}")
else:
    # Actualizar si ya existe para asegurar que esté verificado
    chofer = Usuario.objects.get(username=username)
    chofer.role = 'chofer'
    chofer.verificado = True
    chofer.activo = True
    chofer.activo_chofer = True
    chofer.save()
    print(f"El chofer {username} ya existe. Se ha verificado su cuenta.")
