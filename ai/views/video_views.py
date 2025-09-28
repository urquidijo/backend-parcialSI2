import os
import uuid
import boto3
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from ai.services.video_service import process_video_and_return_events, INPUT_BUCKET
from ai.models.alert import Alert
from ai.serializers import AlertSerializer

ALLOWED_TYPES = {"dog_loose", "dog_waste", "bad_parking"}

s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION","us-east-1"))

class VideoUploadAndProcessView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        camera_id = request.data.get("camera_id", "cam1")
        if not file:
            return Response({"detail":"file requerido"}, status=400)

        # 1) subir a S3
        ext = os.path.splitext(file.name)[1] or ".mp4"
        s3_key = f"videos/{uuid.uuid4().hex}{ext}"
        s3.upload_fileobj(file, INPUT_BUCKET, s3_key, ExtraArgs={"ContentType":"video/mp4"})

        # 2) procesar
        try:
            events = process_video_and_return_events(s3_key, camera_id=camera_id)
        except Exception as e:
            return Response({"detail": f"error analizando video: {e}"}, status=500)

        # 3) guardar en BD (solo tipos permitidos)
        created = []
        for ev in events:
            if ev.get("type") not in ALLOWED_TYPES:
                continue
            a = Alert.objects.create(
                type=ev["type"],
                camera_id=camera_id,
                s3_video_key=ev["s3_video_key"],
                s3_image_key=ev.get("s3_image_key"),
                timestamp_ms=ev["timestamp_ms"],
                confidence=ev.get("confidence", 0.0),
                extra=ev.get("extra", {}),
            )
            created.append(a)

        return Response({
            "ok": True,
            "video_key": s3_key,
            "events": AlertSerializer(created, many=True).data
        }, status=201)

class AlertListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        qs = (Alert.objects
              .filter(type__in=ALLOWED_TYPES)
              .order_by("-created_at")[:50])
        data = AlertSerializer(qs, many=True).data
        return Response(data)
