from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from common.utils import success_response, error_response
from .models import Profile
from .serializers import ProfileSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class MyProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return success_response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data)
        return error_response(errors=serializer.errors)


class UserProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise NotFound(f'User "{username}" not found.')

        profile, _ = Profile.objects.get_or_create(user=user)
        data = ProfileSerializer(profile).data

        # Add whether current user follows this user
        from apps.interactions.models import Follow
        data['is_following'] = Follow.objects.filter(
            follower=request.user, following=user
        ).exists()
        data['is_own_profile'] = (request.user.id == user.id)

        return success_response(data)
