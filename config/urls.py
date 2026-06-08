from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.conversations.api import MessageViewSet, SessionViewSet
from apps.flows.api import FlowOptionViewSet, FlowStepViewSet
from apps.tenants.api import TenantViewSet
from config.api import MeView

router = DefaultRouter()
router.register("tenants", TenantViewSet)
router.register("flow-steps", FlowStepViewSet, basename="flowstep")
router.register("flow-options", FlowOptionViewSet, basename="flowoption")
router.register("sessions", SessionViewSet, basename="session")
router.register("messages", MessageViewSet, basename="message")

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth (D1-11): obtain/refresh JWT for the admin SPA. No public registration.
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", MeView.as_view(), name="me"),
    # Admin API (C-06): tenant CRUD/config, flow builder data, conversation logs.
    path("api/", include(router.urls)),
]
