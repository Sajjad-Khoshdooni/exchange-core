from django.conf import settings
from django.utils.translation import activate


class SetLocaleMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if '/admin' in request.path:
            activate(settings.LANGUAGE_CODE)

        return response
