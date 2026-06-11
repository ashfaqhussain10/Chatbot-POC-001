from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """JWT login with a dedicated brute-force throttle (rate: "login" scope, 5/min).
    Overriding throttle_classes replaces the global user/anon throttles for this view."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(APIView):
    """Returns the authenticated product owner. Doubles as the auth-check endpoint
    the SPA calls on load, and as the reference for a protected DRF view (D1-12)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({"id": u.id, "username": u.username, "email": u.email})
