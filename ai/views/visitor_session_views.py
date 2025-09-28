# ai/views/visitor_session_views.py
from datetime import datetime, date
from django.db.models import Q
from django.utils.timezone import make_aware

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from ai.models.visitor_session import VisitorSession
from ai.serializers import VisitorSessionListSerializer


class SmallPage(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 500


class VisitorSessionListView(ListAPIView):
    """
    GET /api/ai/visitor/sessions/?q=<nombre|email>&from=YYYY-MM-DD&to=YYYY-MM-DD&ordering=-login_at
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = VisitorSessionListSerializer
    pagination_class = SmallPage

    def get_queryset(self):
        qs = (
            VisitorSession.objects
            .select_related("user")
            .order_by("-login_at")
        )

        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q)
            )

        dt_from = self.request.query_params.get("from", "").strip()
        dt_to   = self.request.query_params.get("to", "").strip()

        if dt_from:
            try:
                d = make_aware(datetime.strptime(dt_from, "%Y-%m-%d"))
                qs = qs.filter(login_at__gte=d)
            except Exception:
                pass

        if dt_to:
            try:
                d = make_aware(datetime.strptime(dt_to, "%Y-%m-%d"))
                # incluir todo el día "to" -> sumamos 1 día y usamos < next_day
                from datetime import timedelta
                qs = qs.filter(login_at__lt=d + timedelta(days=1))
            except Exception:
                pass

        ordering = self.request.query_params.get("ordering", "-login_at")
        if ordering:
            # segura (solo permitimos por estas columnas)
            allowed = {"login_at", "-login_at", "logout_at", "-logout_at"}
            if ordering in allowed:
                qs = qs.order_by(ordering)

        return qs


class VisitorSessionStatsView(APIView):
    """
    GET /api/ai/visitor/sessions/stats
    Retorna: activos, hoy, total
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = VisitorSession.objects.all()
        total = qs.count()
        active = qs.filter(logout_at__isnull=True).count()
        today = qs.filter(login_at__date=date.today()).count()
        return Response({
            "active": active,
            "today": today,
            "total": total,
        })
