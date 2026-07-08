import time
import os
import logging
from django.http import HttpResponse

logger = logging.getLogger('accounts.rate_limit')

_redis_client = None
_use_redis = False


def _get_redis():
    global _redis_client, _use_redis
    if _redis_client is None:
        redis_url = os.environ.get('REDIS_URL', os.environ.get('CELERY_BROKER_URL', ''))
        if redis_url:
            try:
                import redis
                _redis_client = redis.from_url(redis_url, socket_timeout=2)
                _redis_client.ping()
                _use_redis = True
                logger.info("Rate limiter using Redis")
            except Exception as e:
                logger.warning(f"Redis unavailable for rate limiter, falling back to in-memory: {e}")
                _redis_client = False
    return _redis_client


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._store = {}
        self._lock = None

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
        now = time.time()
        redis_client = _get_redis()
        if redis_client and _use_redis:
            try:
                pipe = redis_client.pipeline()
                pipe.zadd(key, {str(now): now})
                pipe.zremrangebyscore(key, '-inf', now - window_seconds)
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                _, _, count, _ = pipe.execute()
                return count <= max_requests
            except Exception as e:
                logger.warning(f"Redis rate limit failed, falling back: {e}")

        import threading
        if self._lock is None:
            self._lock = threading.Lock()
        with self._lock:
            records = self._store.get(key, [])
            records = [t for t in records if now - t < window_seconds]
            if len(records) >= max_requests:
                return False
            records.append(now)
            self._store[key] = records
        return True
