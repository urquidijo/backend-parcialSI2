# ai/services/face_service.py
from __future__ import annotations
import os, uuid, boto3
from typing import Optional, Tuple, Dict, Any
from botocore.exceptions import ClientError
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

from ai.models import UserFace  # persiste en BD

# ---------------------------
# Env y clientes AWS
# ---------------------------
def _getenv(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

AWS_ACCESS_KEY_ID     = _getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = _getenv("AWS_REGION", "us-east-1")
BUCKET                = _getenv("AWS_STORAGE_BUCKET_NAME")
COLLECTION            = _getenv("AWS_COLLECTION_ID", "usuarios_faces")
FACE_THRESHOLD        = int(_getenv("FACE_THRESHOLD", "85"))

# Prefijos (usuarios normales)
FACE_ENROLL_PREFIX = _getenv("FACE_ENROLL_PREFIX", "faces/enroll/")
FACE_LOGIN_PREFIX  = _getenv("FACE_LOGIN_PREFIX",  "faces/login/")
# Prefijos (visitantes)
VISITOR_ENROLL_PREFIX = _getenv("VISITOR_ENROLL_PREFIX", "faces/visitors/enroll/")
VISITOR_LOGIN_PREFIX  = _getenv("VISITOR_LOGIN_PREFIX",  "faces/visitors/login/")

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

# ---------------------------
# Helpers
# ---------------------------
def _upload_blob_to_s3(file_obj, key: str) -> None:
    """Soporta InMemoryUploadedFile / TemporaryUploadedFile / path."""
    extra = {"ContentType": "image/jpeg"}
    if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
        file_obj.seek(0)
        s3.upload_fileobj(file_obj, BUCKET, key, ExtraArgs=extra)
    else:
        s3.upload_file(file_obj, BUCKET, key, ExtraArgs=extra)

def _ensure_collection() -> None:
    """Crea la colección si no existe (idempotente)."""
    try:
        rekognition.describe_collection(CollectionId=COLLECTION)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ResourceNotFoundException":
            rekognition.create_collection(CollectionId=COLLECTION)
        else:
            raise

def _upsert_userface(user_id: int | str, face_id: Optional[str], s3_key: str) -> UserFace:
    """Crea/actualiza fila en BD para (user, collection)."""
    uf, _ = UserFace.objects.update_or_create(
        user_id=int(user_id),
        collection_id=COLLECTION,
        defaults={
            "external_image_id": str(user_id),
            "face_id": face_id,
            "s3_key": s3_key,
            "status": "registered" if face_id else "pending",
        },
    )
    return uf

def _norm_prefix(prefix: str | None, fallback: str) -> str:
    p = (prefix or fallback).strip().rstrip("/")
    return f"{p}/" if p else ""

# ---------------------------
# API de servicio
# ---------------------------
def enroll_face(user_id: int | str, file_obj, *, key_prefix: str | None = None, is_visitor: bool = False) -> Dict[str, Any]:
    """
    Sube imagen de enrolamiento a S3, indexa en Rekognition con ExternalImageId=user_id
    y persiste/actualiza en BD (ai_userface).

    - key_prefix: prefijo S3 custom (opcional)
    - is_visitor: si True usa VISITOR_ENROLL_PREFIX por defecto
    """
    if not BUCKET or not COLLECTION:
        raise RuntimeError("Config AWS incompleta: BUCKET/COLLECTION")

    _ensure_collection()

    default_prefix = VISITOR_ENROLL_PREFIX if is_visitor else FACE_ENROLL_PREFIX
    prefix = _norm_prefix(key_prefix, default_prefix)
    key = f"{prefix}{uuid.uuid4()}.jpg"
    _upload_blob_to_s3(file_obj, key)

    resp = rekognition.index_faces(
        CollectionId=COLLECTION,
        Image={"S3Object": {"Bucket": BUCKET, "Name": key}},
        ExternalImageId=str(user_id),
        DetectionAttributes=["DEFAULT"],
        MaxFaces=1,
        QualityFilter="AUTO",
    )

    face_records = resp.get("FaceRecords", [])
    face_id = face_records[0]["Face"]["FaceId"] if face_records else None

    uf = _upsert_userface(user_id=user_id, face_id=face_id, s3_key=key)

    return {
        "ok": True,
        "user_id": int(user_id),
        "external_image_id": str(user_id),
        "face_id": face_id,
        "collection_id": COLLECTION,
        "s3_key": key,
        "db_id": uf.id,
        "raw": resp,
    }

def search_by_image(file_obj, *, key_prefix: str | None = None, is_visitor: bool = False) -> Tuple[Optional[str], Optional[float], str, Dict[str, Any]]:
    """
    Sube imagen de login a S3 y busca coincidencias en Rekognition.
    Retorna: (external_id, similarity, s3_key, raw_response)

    - key_prefix: prefijo S3 custom (opcional)
    - is_visitor: si True usa VISITOR_LOGIN_PREFIX por defecto
    """
    if not BUCKET or not COLLECTION:
        raise RuntimeError("Config AWS incompleta: BUCKET/COLLECTION")

    _ensure_collection()

    default_prefix = VISITOR_LOGIN_PREFIX if is_visitor else FACE_LOGIN_PREFIX
    prefix = _norm_prefix(key_prefix, default_prefix)
    key = f"{prefix}{uuid.uuid4()}.jpg"
    _upload_blob_to_s3(file_obj, key)

    resp = rekognition.search_faces_by_image(
        CollectionId=COLLECTION,
        Image={"S3Object": {"Bucket": BUCKET, "Name": key}},
        MaxFaces=5,
        FaceMatchThreshold=FACE_THRESHOLD,
    )

    matches = resp.get("FaceMatches", [])
    if not matches:
        return (None, None, key, resp)

    matches.sort(key=lambda m: m.get("Similarity", 0.0), reverse=True)
    best = matches[0]
    external_id = best["Face"].get("ExternalImageId")
    similarity = float(best.get("Similarity", 0.0))

    return (external_id, similarity, key, resp)