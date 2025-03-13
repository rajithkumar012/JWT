import redis
from django.conf import settings
from django.http import JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication

# Initialize Redis client
redis_client = redis.StrictRedis.from_url(settings.CACHES["default"]["LOCATION"], decode_responses=True)

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = self.get_user_id(request)
        if user_id:
            rate_limit_key = f"rate_limit:user:{user_id}"
            request_count = redis_client.get(rate_limit_key)

            if request_count is None:
                redis_client.setex(rate_limit_key, 3600, 1)  # 1-hour expiry
            else:
                request_count = int(request_count)
                if request_count >= 100:
                    return JsonResponse({"error": "Rate limit exceeded. Try again later."}, status=429)
                redis_client.incr(rate_limit_key)

        return self.get_response(request)

    def get_user_id(self, request):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                return validated_token["user_id"]
            except Exception:
                return None
        return None
