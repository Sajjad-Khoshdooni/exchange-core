from django.http import Http404
from django.views.generic import TemplateView

from financial.models import Gateway


class ProxyPaymentRedirectView(TemplateView):
    template_name = 'redirect.html'

    def get_context_data(self, **kwargs):
        gateway = self.request.GET.get('gateway')
        authority = self.request.GET.get('authority')

        gateway_class = Gateway.get_gateway_class(gateway)

        if not gateway_class or not authority:
            raise Http404

        return {
            'url': gateway_class.get_payment_url(authority)
        }
