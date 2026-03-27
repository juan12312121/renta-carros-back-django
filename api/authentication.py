"""
Sistema de autenticación JWT para el sistema de renta de carros
Maneja login, registro, tokens y permisos por rol
"""

import jwt
import datetime
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from django.utils import timezone

from .models import Usuario
from .serializers import (
    LoginSerializer,
    RegistroClienteSerializer,
    RegistroChoferSerializer,
    RegistroAdminSerializer,
    CambiarPasswordSerializer,
    PerfilClienteSerializer,
    PerfilChoferSerializer,
)


# ===============================================
# UTILIDADES JWT
# ===============================================

def generar_tokens(usuario):
    """Genera access token y refresh token para un usuario"""

    # Admin gets longer-lived tokens to keep session alive
    if usuario.role == 'admin':
        access_hours = 24
        refresh_days = 30
    else:
        access_hours = 1
        refresh_days = 7

    access_payload = {
        'user_id': usuario.id,
        'email': usuario.email,
        'role': usuario.role,
        'nivel': usuario.nivel_usuario,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=access_hours),
        'iat': datetime.datetime.utcnow(),
        'type': 'access'
    }

    refresh_payload = {
        'user_id': usuario.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=refresh_days),
        'iat': datetime.datetime.utcnow(),
        'type': 'refresh'
    }

    access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')

    return {
        'access': access_token,
        'refresh': refresh_token
    }


def verificar_token(token, tipo='access'):
    """Verifica y decodifica un JWT. Retorna el payload o lanza excepción."""
    try:
        # print(f"Decodificando token tipo {tipo}...") # Demasiado ruido si hay muchos gets
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        if payload.get('type') != tipo:
            print(f"ERROR: Tipo de token esperado {tipo}, recibido {payload.get('type')}")
            raise jwt.InvalidTokenError("Tipo de token incorrecto.")
        return payload
    except jwt.ExpiredSignatureError:
        print("ERROR: El token ha expirado (ExpiredSignatureError)")
        raise Exception("El token ha expirado.")
    except jwt.InvalidTokenError as e:
        print(f"ERROR: Token inválido ({str(e)})")
        raise Exception(f"Token inválido: {str(e)}")
    except Exception as e:
        print(f"ERRORinesperada verificando token: {str(e)}")
        raise e


# ===============================================
# MIDDLEWARE / AUTENTICACIÓN EN VIEWS
# ===============================================

class JWTAuthentication:
    """
    Clase auxiliar para verificar JWT en las vistas.
    Se usa como mixin o se llama directamente.
    """

    @staticmethod
    def obtener_usuario_de_request(request):
        """
        Extrae el usuario del header Authorization.
        Retorna (usuario, error_response).
        """
        auth_header = request.headers.get('Authorization', '')
        
        # LOGS DE DEPURACIÓN
        print(f"--- DEBUG AUTH ---")
        print(f"Path: {request.path}")
        print(f"Method: {request.method}")
        print(f"Auth Header Present: {bool(auth_header)}")

        if not auth_header.startswith('Bearer '):
            print("ERROR: Header no empieza con 'Bearer '")
            return None, Response(
                {'error': 'Token de autorización requerido. Formato: Bearer <token>'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token = auth_header.split(' ')[1]

        try:
            payload = verificar_token(token, tipo='access')
            print(f"Token verificado para user_id: {payload.get('user_id')}")
            usuario = Usuario.objects.get(id=payload['user_id'], activo=True)
            print(f"Usuario encontrado: {usuario.username} (Role: {usuario.role})")
            return usuario, None
        except Usuario.DoesNotExist:
            print("ERROR: Usuario no encontrado o inactivo.")
            return None, Response(
                {'error': 'Usuario no encontrado o inactivo.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            print(f"ERROR AUTH: {str(e)}")
            return None, Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

    @staticmethod
    def requiere_rol(*roles_permitidos):
        """
        Decorador para restringir vistas a ciertos roles.
        Uso: @JWTAuthentication.requiere_rol('admin', 'chofer')
        """
        def decorador(func):
            def wrapper(self, request, *args, **kwargs):
                usuario, error = JWTAuthentication.obtener_usuario_de_request(request)
                if error:
                    return error
                if usuario.role not in roles_permitidos:
                    return Response(
                        {'error': f'Acceso denegado. Se requiere rol: {", ".join(roles_permitidos)}'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                request.user_obj = usuario
                return func(self, request, *args, **kwargs)
            return wrapper
        return decorador


# ===============================================
# VISTAS DE AUTENTICACIÓN
# ===============================================

class RegistroClienteView(APIView):
    """POST /api/auth/registro/cliente/ — Registrar un nuevo cliente"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroClienteSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            tokens = generar_tokens(usuario)
            return Response({
                'mensaje': '¡Cuenta creada exitosamente!',
                'usuario': {
                    'id': usuario.id,
                    'nombre': usuario.get_nombre_completo(),
                    'email': usuario.email,
                    'role': usuario.role,
                    'nivel': usuario.nivel_usuario,
                },
                **tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegistroChoferView(APIView):
    """POST /api/auth/registro/chofer/ — Registrar un nuevo chofer"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroChoferSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            return Response({
                'mensaje': 'Solicitud enviada. Un administrador verificará tu cuenta.',
                'usuario': {
                    'id': usuario.id,
                    'nombre': usuario.get_nombre_completo(),
                    'email': usuario.email,
                    'role': usuario.role,
                    'verificado': usuario.verificado,
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegistroAdminView(APIView):
    """POST /api/auth/registro/admin/ — Registrar un nuevo administrador"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegistroAdminSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            tokens = generar_tokens(usuario)
            return Response({
                'mensaje': '¡Administrador creado exitosamente!',
                'usuario': {
                    'id': usuario.id,
                    'nombre': usuario.get_nombre_completo(),
                    'email': usuario.email,
                    'role': usuario.role,
                },
                **tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """POST /api/auth/login/ — Login para todos los roles"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            usuario = serializer.validated_data['usuario']

            # Actualizar último acceso
            usuario.ultimo_acceso = timezone.now()
            usuario.save(update_fields=['ultimo_acceso'])

            tokens = generar_tokens(usuario)

            # Seleccionar el serializer de perfil según el rol
            if usuario.role == 'cliente':
                perfil = PerfilClienteSerializer(usuario).data
            elif usuario.role == 'chofer':
                perfil = PerfilChoferSerializer(usuario).data
            else:
                perfil = {
                    'id': usuario.id,
                    'nombre': usuario.get_nombre_completo(),
                    'email': usuario.email,
                    'role': usuario.role,
                }

            return Response({
                'mensaje': f'Bienvenido, {usuario.nombre}!',
                'usuario': perfil,
                **tokens
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(APIView):
    """POST /api/auth/refresh/ — Renovar el access token con el refresh token"""

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            payload = verificar_token(refresh_token, tipo='refresh')
            usuario = Usuario.objects.get(id=payload['user_id'], activo=True)
            tokens = generar_tokens(usuario)
            return Response(tokens, status=status.HTTP_200_OK)
        except Usuario.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    """POST /api/auth/logout/ — Logout (el cliente borra el token en su lado)"""

    def post(self, request):
        # Con JWT stateless, el logout real ocurre en el cliente borrando el token.
        # Aquí simplemente confirmamos la operación.
        return Response({'mensaje': 'Sesión cerrada exitosamente.'}, status=status.HTTP_200_OK)


class MiPerfilView(APIView):
    """GET /api/auth/me/ — Ver tu propio perfil"""

    def get(self, request):
        usuario, error = JWTAuthentication.obtener_usuario_de_request(request)
        if error:
            return error

        if usuario.role == 'cliente':
            serializer = PerfilClienteSerializer(usuario)
        elif usuario.role == 'chofer':
            serializer = PerfilChoferSerializer(usuario)
        else:
            from .serializers import AdminUsuarioSerializer
            serializer = AdminUsuarioSerializer(usuario)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """PATCH /api/auth/me/ — Actualizar tu propio perfil"""
        usuario, error = JWTAuthentication.obtener_usuario_de_request(request)
        if error:
            return error

        if usuario.role == 'cliente':
            serializer = PerfilClienteSerializer(usuario, data=request.data, partial=True)
        elif usuario.role == 'chofer':
            serializer = PerfilChoferSerializer(usuario, data=request.data, partial=True)
        else:
            from .serializers import AdminUsuarioSerializer
            serializer = AdminUsuarioSerializer(usuario, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'mensaje': 'Perfil actualizado.', 'perfil': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CambiarPasswordView(APIView):
    """POST /api/auth/cambiar-password/ — Cambiar contraseña"""

    def post(self, request):
        from django.contrib.auth.hashers import check_password, make_password

        usuario, error = JWTAuthentication.obtener_usuario_de_request(request)
        if error:
            return error

        serializer = CambiarPasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not check_password(serializer.validated_data['password_actual'], usuario.password_hash):
                return Response(
                    {'error': 'La contraseña actual es incorrecta.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            usuario.password_hash = make_password(serializer.validated_data['password_nuevo'])
            usuario.save(update_fields=['password_hash'])
            return Response({'mensaje': 'Contraseña cambiada exitosamente.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)