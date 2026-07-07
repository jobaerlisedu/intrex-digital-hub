import time
from django.http import HttpResponse

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        ip = self._get_ip(request)

        if path.startswith('/login/'):
            if not self._check_limit(f"rl:login:{ip}", 10, 60):
                return HttpResponse("Too many login attempts. Try again in 60 seconds.", status=429)
        elif path.startswith('/api/'):
            if not self._check_limit(f"rl:api:{ip}", 120, 60):
                return HttpResponse("API rate limit exceeded. Try again later.", status=429)

        return self.get_response(request)

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _check_limit(self, key, max_requests, window_seconds):
        import threading
        if not hasattr(self, '_store'):
            self._store = {}
            self._lock = threading.Lock()
        now = time.time()
        with self._lock:
            records = self._store.get(key, [])
            records = [t for t in records if now - t < window_seconds]
            if len(records) >= max_requests:
                return False
            records.append(now)
            self._store[key] = records
        return True
