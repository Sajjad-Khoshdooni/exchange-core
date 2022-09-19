import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import User
from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.views.authentication import CustomTokenAuthentication
from market.models import PairSymbol
from market.serializers.symbol_serializer import SymbolSerializer, SymbolBreifStatsSerializer, SymbolStatsSerializer

from market.serializers import BookMarkPairSymbolSerializer


class SymbolFilter(django_filters.FilterSet):
    asset = django_filters.CharFilter(field_name='asset__symbol')
    base_asset = django_filters.CharFilter(field_name='base_asset__symbol')

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'enable')


class SymbolListAPIView(ListAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    permission_classes = ()
    filter_backends = [DjangoFilterBackend]
    filter_class = SymbolFilter
    filterset_fields = ('strategy_enable', )
    queryset = PairSymbol.objects.filter(enable=True).order_by('-asset__trend', 'asset__order', 'base_asset__trend', '-base_asset__order')

    def get_serializer_class(self):
        if self.request.query_params.get('stats') == '1':
            return SymbolBreifStatsSerializer
        else:
            return SymbolSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        user = self.request.user
        if user.id:
            ctx['bookmarks'] = set(user.account.bookmark_market.values_list('id', flat=True))
        else:
            ctx['bookmarks'] = []

        return ctx


class SymbolDetailedStatsAPIView(RetrieveAPIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    serializer_class = SymbolStatsSerializer
    queryset = PairSymbol.objects.all()
    lookup_field = 'name'


class BookMarkSymbolAPIView(APIView):
    def patch(self, request):
        user = self.request.user
        book_mark_serializer = BookMarkPairSymbolSerializer(
            instance=user,
            data=request.data,
            partial=True
        )
        book_mark_serializer.is_valid(raise_exception=True)
        book_mark_serializer.save()
        return Response({'msg': 'ok'})

    def get_queryset(self):
        return User.objects.filter(user=self.request.user)





