from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from common.utils import success_response, created_response, error_response
from .serializers import RegisterSerializer, UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return created_response(UserSerializer(user).data, message='Account created.')
        return error_response(errors=serializer.errors)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return success_response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh_token = request.data.get('refresh', '')
        if not refresh_token:
            return error_response(message='Refresh token is required.')
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass
        return success_response(message='Logged out.')


class AdminLoginView(APIView):
    """Separate login for admin portal — only allows is_admin=True users."""
    permission_classes = (AllowAny,)

    def post(self, request):
        email    = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return error_response(message='Email and password are required.')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response(message='Invalid credentials.', status_code=401)

        if not user.check_password(password):
            return error_response(message='Invalid credentials.', status_code=401)

        if not user.is_active:
            return error_response(message='Account is disabled.', status_code=403)

        if not (user.is_admin or user.is_superuser):
            return error_response(
                message='Access denied. Admin privileges required.',
                status_code=403,
            )

        refresh = RefreshToken.for_user(user)
        # Embed admin claims
        refresh['username']     = user.username
        refresh['is_admin']     = user.is_admin
        refresh['is_moderator'] = user.is_moderator

        return success_response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    UserSerializer(user).data,
        }, message='Admin login successful.')

