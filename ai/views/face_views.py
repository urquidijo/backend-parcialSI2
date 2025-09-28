# recognition/views.py
import os
import uuid
import boto3
from botocore.exceptions import ClientError

from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..services.face_service import enroll_face, search_by_image 
from ..models import UserFace

# ========= AWS config =========
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1").strip()
BUCKET                = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
COLLECTION            = os.getenv("AWS_COLLECTION_ID", "").strip()
FACE_THRESHOLD        = int(os.getenv("FACE_THRESHOLD", "90"))

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
rekognition = boto3.client(
    "rekognition",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

def _upload_blob_to_s3(file_obj, key: str):
    """Sube file_obj a S3 con ContentType image/jpeg."""
    extra = {"ContentType": "image/jpeg"}
    if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
        file_obj.seek(0)
        s3.upload_fileobj(file_obj, BUCKET, key, ExtraArgs=extra)
    else:
        s3.upload_file(file_obj, BUCKET, key, ExtraArgs=extra)


User = get_user_model()


# ========= ENROLL =========
class FaceEnrollView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        user_id = request.data.get("user_id")
        if not file or not user_id:
            return Response({"detail": "file y user_id son requeridos"}, status=400)

        try:
            result = enroll_face(user_id, file)

            # Persistencia opcional en BD
            try:
                UserFace.objects.update_or_create(
                    user_id=int(user_id),
                    defaults={
                        "external_image_id": result.get("external_image_id", str(user_id)),
                        "face_id": result.get("face_id") or "",
                        "collection_id": result.get("collection_id", COLLECTION),
                        "s3_key": result.get("s3_key", ""),
                        "status": "active",
                    },
                )
            except Exception as e:
                # No romper si la BD falla
                print("WARN saving UserFace:", e)

            return Response({"ok": True, "result": result}, status=201)

        except ClientError as e:
            msg = e.response.get("Error", {}).get("Message", str(e))
            return Response({"ok": False, "detail": f"AWS error: {msg}"}, status=400)
        except Exception as e:
            return Response({"ok": False, "detail": str(e)}, status=500)


# ========= LOGIN =========
class FaceLoginView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "file es requerido"}, status=400)

        # Buscar coincidencia
        external_id, similarity, s3key, _raw = search_by_image(file)
        if not external_id:
            return Response({"recognized": False}, status=200)

        # Buscar usuario por external_id (guardamos el id del usuario como ExternalImageId)
        try:
            user = User.objects.get(pk=int(external_id))
        except (ValueError, User.DoesNotExist):
            return Response({"recognized": False}, status=200)

        # Generar tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Rol del usuario (si tu User tiene FK 'role')
        role_name = getattr(getattr(user, "role", None), "name", None)

        # Permisos: intenta 'codename' -> 'code' -> 'name'
        perms = []
        role = getattr(user, "role", None)
        if role is not None and hasattr(role, "permissions"):
            try:
                model_fields = {f.name for f in role.permissions.model._meta.fields}
                if "codename" in model_fields:
                    perms = list(role.permissions.values_list("codename", flat=True))
                elif "code" in model_fields:
                    perms = list(role.permissions.values_list("code", flat=True))
                elif "name" in model_fields:
                    perms = list(role.permissions.values_list("name", flat=True))
                else:
                    perms = []
            except Exception as e:
                print("WARN reading role permissions:", e)
                perms = []

        # Si usas permisos nativos de Django:
        # perms = list(user.get_all_permissions())

        return Response(
            {
                "recognized": True,
                "similarity": similarity,
                "user": {
                    "id": user.id,
                    "email": getattr(user, "email", ""),
                    "first_name": getattr(user, "first_name", ""),
                    "last_name": getattr(user, "last_name", ""),
                    "role": {"name": role_name} if role_name else None,
                },
                "access": str(access),
                "refresh": str(refresh),
                "role": role_name,
                "permissions": perms,
            },
            status=200,
        )


# ========= STATUS / REVOKE (stubs) =========
class FaceStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id: int):
        return Response({"status": "registered", "user_id": user_id})


class FaceRevokeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Aquí podrías eliminar la cara de la collection y marcar en BD.
        return Response({"message": "revoked (stub)"})


# ========= DEBUG (lista primeras 5 caras) =========
class FaceDebugView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        col = os.getenv("AWS_COLLECTION_ID", "").strip()
        reg = os.getenv("AWS_REGION", "us-east-1").strip()
        rek = boto3.client("rekognition", region_name=reg)
        faces = []
        token = None
        while True:
            kw = {"CollectionId": col}
            if token:
                kw["NextToken"] = token
            r = rek.list_faces(**kw)
            faces.extend(r.get("Faces", []))
            token = r.get("NextToken")
            if not token:
                break
        return Response({"collection": col, "count": len(faces), "faces": faces[:5]})
