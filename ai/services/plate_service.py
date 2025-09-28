import os, uuid, boto3, re
from botocore.exceptions import ClientError
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from ai.models.plate import Plate

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
BUCKET                = os.getenv("AWS_STORAGE_BUCKET_NAME", "")

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
    extra = {"ContentType": "image/jpeg"}
    if isinstance(file_obj, (InMemoryUploadedFile, TemporaryUploadedFile)):
        file_obj.seek(0)
        s3.upload_fileobj(file_obj, BUCKET, key, ExtraArgs=extra)
    else:
        s3.upload_file(file_obj, BUCKET, key, ExtraArgs=extra)

def detect_plate(file_obj):
    key = f"plates/{uuid.uuid4()}.jpg"
    _upload_blob_to_s3(file_obj, key)

    # Llamamos a Rekognition
    resp = rekognition.detect_text(Image={"S3Object": {"Bucket": BUCKET, "Name": key}})

    # Ordenar por confianza, de mayor a menor
    detections = sorted(resp["TextDetections"], key=lambda d: d["Confidence"], reverse=True)

    candidate_plates = []
    for d in detections:
        if d["Type"] == "WORD":
            text = d["DetectedText"].strip().upper()

            # Ignorar palabras comunes
            if text in ["BOLIVIA", "L"]:
                continue

            # Filtrar por patrón: letras y números juntos
            if re.match(r"^[A-Z0-9]{4,10}$", text):
                candidate_plates.append(text)

    # Tomamos la primera coincidencia válida
    plate_number = candidate_plates[0] if candidate_plates else None

    return plate_number, key
