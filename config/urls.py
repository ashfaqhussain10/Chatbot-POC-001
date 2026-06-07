from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.api import MeView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth (D1-11): obtain/refresh JWT for the admin SPA. No public registration.
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", MeView.as_view(), name="me"),
]
