from rest_framework import serializers
from rest_framework.views import APIView
from accounts.models import User
from rest_framework.response import Response


class OnBoardingFlowSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('on_boarding_flow',)


class OnBoardingFlowStatus(APIView):

    def patch(self, request):
        user = self.request.user
        on_boarding_flow_serializer = OnBoardingFlowSerializer(
            instance=user,
            data=request.data,
            partial=True,
        )
        on_boarding_flow_serializer.is_valid(raise_exception=True)
        on_boarding_flow_serializer.save()
        return Response({'msg': 'status update successfully'})
