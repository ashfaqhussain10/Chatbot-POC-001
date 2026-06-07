from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):
    """Returns the authenticated product owner. Doubles as the auth-check endpoint
    the SPA calls on load, and as the reference for a protected DRF view (D1-12)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        return Response({"id": u.id, "username": u.username, "email": u.email})
