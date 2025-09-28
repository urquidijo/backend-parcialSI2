import os
import uuid
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.exceptions import AuthenticationFailed

from ai.services.face_service import enroll_face, search_by_image
from ai.serializers import VisitorRegisterSerializer, VisitorLoginSerializer
from ai.models.visitor_session import VisitorSession
from users.models import Role

User = get_user_model()

# Config rol/prefijos
VISITOR_ROLE_NAME      = os.getenv("VISITOR_ROLE_NAME", "Visitante").strip() or "Visitante"
VISITOR_ENROLL_PREFIX  = os.getenv("VISITOR_ENROLL_PREFIX", "faces/visitors/enroll/")
VISITOR_LOGIN_PREFIX   = os.getenv("VISITOR_LOGIN_PREFIX",  "faces/visitors/login/")

def _get_visitor_role() -> Role | None:
    try:
        return Role.objects.get(name=VISITOR_ROLE_NAME)
    except Role.DoesNotExist:
        return None

def _is_visitor(user: User) -> bool:
    r = getattr(user, "role", None)
    return bool(r and r.name in ("Visitante", "VISITOR"))

def _gen_visitor_email() -> str:
    return f"visitor+{uuid.uuid4().hex[:24]}@noemail.local"


# ---------- REGISTRO DE VISITANTE ----------
@method_decorator(csrf_exempt, name="dispatch")
class VisitorRegisterView(APIView):
    """Crea usuario visitante (nombre+apellido) + enroll en Rekognition."""
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    @transaction.atomic
    def post(self, request):
        s = VisitorRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        first_name = s.validated_data["first_name"].strip()
        last_name  = s.validated_data["last_name"].strip()
        file_obj   = s.validated_data["file"]

        role = _get_visitor_role()
        if role is None:
            return Response(
                {"ok": False, "detail": f"Falta crear el rol '{VISITOR_ROLE_NAME}' en /admin (tabla role)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(
            email=_gen_visitor_email(),
            password=None,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )

        enroll_face(user.id, file_obj, key_prefix=VISITOR_ENROLL_PREFIX, is_visitor=True)
        return Response({"ok": True, "user_id": user.id}, status=status.HTTP_201_CREATED)


# ---------- LOGIN DE VISITANTE (CREA SESIÓN) ----------
@method_decorator(csrf_exempt, name="dispatch")
class VisitorLoginView(APIView):
    """Login por rostro; crea una fila en ai_visitor_session."""
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        s = VisitorLoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        external_id, similarity, key, _raw = search_by_image(
            s.validated_data["file"],
            key_prefix=VISITOR_LOGIN_PREFIX,
            is_visitor=True,
        )
        if not external_id:
            return Response({"ok": False, "code": "NOT_VISITOR"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = User.objects.get(id=int(external_id))
        except (User.DoesNotExist, ValueError):
            return Response({"ok": False, "code": "NOT_VISITOR"}, status=status.HTTP_404_NOT_FOUND)

        role = getattr(user, "role", None)
        role_name = getattr(role, "name", None)
        if role_name not in ("Visitante", "VISITOR"):
            return Response({"ok": False, "code": "NOT_VISITOR"}, status=status.HTTP_403_FORBIDDEN)

        # Crea la sesión
        sess = VisitorSession.objects.create(
            user=user,
            similarity=float(similarity or 0.0),
            s3_key=key or "",
            event_type="session",
        )

        # Tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Permisos del rol (compatibles con tu modelo)
        perms = []
        if role is not None and hasattr(role, "permissions"):
            try:
                model_fields = {f.name for f in role.permissions.model._meta.fields}
                if "codename" in model_fields:
                    perms = list(role.permissions.values_list("codename", flat=True))
                elif "code" in model_fields:
                    perms = list(role.permissions.values_list("code", flat=True))
                elif "name" in model_fields:
                    perms = list(role.permissions.values_list("name", flat=True))
            except Exception:
                perms = []

        return Response(
            {
                "ok": True,
                "user_id": user.id,
                "session_id": sess.id,
                "similarity": similarity,
                "access": str(access),
                "refresh": str(refresh),
                "role": role_name,          # 👈 ROLE
                "permissions": perms,       # 👈 PERMISSIONS
                "user": {
                    "id": user.id,
                    "email": getattr(user, "email", ""),
                    "first_name": getattr(user, "first_name", ""),
                    "last_name": getattr(user, "last_name", ""),
                    "role": {"name": role_name} if role_name else None,
                },
            },
            status=status.HTTP_200_OK,
        )


# ---------- LOGOUT DE VISITANTE (CIERRA SESIÓN) ----------
@method_decorator(csrf_exempt, name="dispatch")
class VisitorLogoutView(APIView):
    """Marca logout_at en la última sesión abierta del visitante."""
    permission_classes = [permissions.AllowAny]

    def _user_from_auth(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION") or ""
        if auth.lower().startswith("bearer "):
            token_str = auth.split(" ", 1)[1].strip()
            token = AccessToken(token_str)
            uid = int(token.get("user_id"))
            return User.objects.get(id=uid)
        raise AuthenticationFailed("Sin token")

    def post(self, request):
        # 1) con token
        try:
            user = self._user_from_auth(request)
        except Exception:
            # 2) o con user_id en body
            uid = request.data.get("user_id") or request.POST.get("user_id")
            if not uid:
                return Response({"ok": False, "detail": "Falta token o user_id"}, status=400)
            try:
                user = User.objects.get(id=int(uid))
            except User.DoesNotExist:
                return Response({"ok": False, "detail": "Usuario no existe"}, status=404)

        role_name = getattr(getattr(user, "role", None), "name", None)
        if role_name not in ("Visitante", "VISITOR"):
            return Response({"ok": False, "detail": "Usuario no es Visitante"}, status=403)

        sess = (
            VisitorSession.objects
            .filter(user=user, logout_at__isnull=True)
            .order_by("-login_at")
            .first()
        )

        if sess:
            sess.logout_at = timezone.now()
            sess.save(update_fields=["logout_at"])
        else:
            # si no hay sesión abierta, crea una cerrada inmediata (constancia)
            sess = VisitorSession.objects.create(
                user=user,
                similarity=0.0,
                s3_key="",
                event_type="session",
                logout_at=timezone.now(),
            )

        return Response(
            {
                "ok": True,
                "user_id": user.id,
                "session_id": sess.id,
                "login_at": sess.login_at.isoformat(),
                "logout_at": sess.logout_at.isoformat() if sess.logout_at else None,
            }
        )


# ---------- ÚLTIMO ESTADO (opcional) ----------
@method_decorator(csrf_exempt, name="dispatch")
class VisitorLastStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id: int):
        sess = (
            VisitorSession.objects
            .filter(user_id=user_id)
            .order_by("-login_at")
            .values("login_at", "logout_at", "similarity", "s3_key")
            .first()
        )
        if not sess:
            return Response({"last_event": None, "at": None})
        last_event = "logout" if sess["logout_at"] else "login"
        at = (sess["logout_at"] or sess["login_at"]).isoformat()
        return Response({"last_event": last_event, "at": at})



# ai/views/visitor_auth_views.py  (al final del archivo)

from rest_framework import generics, permissions
from django.db.models import Q
from ai.models.visitor_session import VisitorSession
from ai.serializers import VisitorSessionListSerializer


class VisitorSessionListView(generics.ListAPIView):
    """
    GET /api/ai/visitor/sessions/?q=texto&from=YYYY-MM-DD&to=YYYY-MM-DD&ordering=-login_at&page=1&page_size=20
    Devuelve: id, full_name, login_at, logout_at
    """
    serializer_class = VisitorSessionListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            VisitorSession.objects
            .select_related("user")
            .order_by("-login_at")
        )

        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q)
            )

        date_from = (self.request.query_params.get("from") or "").strip()
        if date_from:
            qs = qs.filter(login_at__date__gte=date_from)

        date_to = (self.request.query_params.get("to") or "").strip()
        if date_to:
            qs = qs.filter(login_at__date__lte=date_to)

        ordering = (self.request.query_params.get("ordering") or "").strip()
        if ordering in {"login_at", "-login_at", "logout_at", "-logout_at"}:
            qs = qs.order_by(ordering)

        return qs

