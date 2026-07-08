from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .views import FirestoreTokenObtainPairView, FirestoreTokenRefreshView, LogoutView

urlpatterns = [
    path("token/", FirestoreTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", FirestoreTokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
]
