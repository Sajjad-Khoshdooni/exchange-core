from rest_framework import serializers
from rest_framework.views import APIView
from accounts.models import User
from rest_framework.response import Response


class AfterSignUpStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('after_sign_up_status',)


class ChangeAfterSignUpStatus(APIView):

    def patch(self, request):
        user = self.request.user
        after_sign_up_status_serializer = AfterSignUpStatusSerializer(
            instance=user,
            data=request.data,
            partial=True,
        )
        after_sign_up_status_serializer.is_valid(raise_exception=True)
        after_sign_up_status_serializer.save()
        return Response({'msg': 'status update successfully'})
