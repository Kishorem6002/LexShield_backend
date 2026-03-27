from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from common.utils import success_response, error_response
from .models import UserSettings
from .serializers import UserSettingsSerializer


class UserSettingsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        return success_response(UserSettingsSerializer(settings_obj).data)

    def patch(self, request):
        settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
        serializer = UserSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data)
        return error_response(errors=serializer.errors)
