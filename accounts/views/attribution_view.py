from datetime import datetime

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Attribution


class AttributionAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        params = request.query_params

        clicked_at = None
        if params.get('clicked_at'):
            clicked_at = datetime.fromtimestamp(float(params.get('clicked_at')) / 1000).astimezone()

        installed_at = None
        if params.get('installed_at'):
            installed_at = datetime.fromtimestamp(float(params.get('installed_at')) / 1000).astimezone()

        Attribution.objects.get_or_create(
            gps_adid=params.get('gps_adid') or '',
            ip_address=params.get('ip_address'),
            user_agent=params.get('user_agent') or '',
            installed_at=installed_at,
            defaults={
                'tracker_code': params.get('tracker_code') or '',
                'network_name': params.get('network_name') or '',
                'campaign_name': params.get('campaign_name') or '',
                'adgroup_name': params.get('adgroup_name') or '',
                'creative_name': params.get('creative_name') or '',
                'action_name': params.get('action_name') or '',
                'reinstalled': params.get('reinstalled') == 'true',
                'tracker_user_id': params.get('metrix_user_id') or '',
                'clicked_at': clicked_at,
                'country': params.get('country') or '',
                'city': params.get('city') or '',
            }
        )

        return Response(status=200)
