from django.conf import settings
from django.http import HttpResponseBadRequest

class DynamicCsrfMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
