from rest_framework import serializers
from rest_framework.generics import RetrieveUpdateAPIView

from accounts.models import Company
from multimedia.fields import FileField


class DocumentsSerializer(serializers.ModelSerializer):
    company_documents = FileField(write_only=True)

    class Meta:
        model = Company
        fields = ('company_documents', 'status',)
        extra_kwargs = {
            'status': {'read_only': True}
        }


class RegisterDocuments(RetrieveUpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = DocumentsSerializer

    def get_object(self):
        user = self.request.user
        return self.queryset.get(user=user)
