# ai/views/plate_views.py
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from ai.models.plate import Plate
from ai.services.plate_service import detect_plate  # tu OCR que devuelve la placa

User = get_user_model()


class PlateDetectView(APIView):
    """
    Detecta el número de placa a partir de una imagen.
    Body (multipart/form-data):
      - file: imagen
    Respuesta: { ok: true, plate: "ABC123" | null }
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "file es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = detect_plate(file)
            # tu función puede devolver 'ABC123' o ('ABC123', 's3_key')
            if isinstance(result, (list, tuple)):
                plate = result[0] if result else None
            else:
                plate = result

            if not plate:
                return Response({"ok": True, "plate": None}, status=status.HTTP_200_OK)

            return Response({"ok": True, "plate": plate}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"Error detectando placa: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlateAssignView(APIView):
    """
    Asigna una placa a un usuario.
    Body (JSON):
      - user_id: int
      - number: str
    Respuesta: { ok: true, msg: "...", id: <plate_id> }
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get("user_id")
        number = request.data.get("number")

        if not user_id or not number:
            return Response({"error": "user_id y number son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

        # normalizamos placa
        number = str(number).strip().upper()

        # valida usuario
        try:
            User.objects.only("id").get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuario no existe"}, status=status.HTTP_404_NOT_FOUND)

        try:
            obj = Plate.objects.create(user_id=user_id, number=number)
            return Response({"ok": True, "msg": "Placa asignada", "id": obj.id}, status=status.HTTP_201_CREATED)
        except IntegrityError:
            # por unique_together (user, number) o unique number, según tu modelo
            return Response({"error": "La placa ya está registrada para ese usuario"}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({"error": f"No se pudo asignar la placa: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlateVerifyView(APIView):
    """
    Verifica si una placa existe en la BD.
    Body (JSON):
      - number: str
    Respuesta: { exists: bool }
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        number = request.data.get("number")
        if not number:
            return Response({"error": "number es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        number = str(number).strip().upper()
        exists = Plate.objects.filter(number=number).exists()
        return Response({"exists": exists}, status=status.HTTP_200_OK)
