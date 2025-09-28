from __future__ import annotations
import os, io, time, uuid, tempfile, math, boto3
from typing import List, Dict, Any

INPUT_BUCKET  = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
OUTPUT_BUCKET = os.getenv("ALERTS_BUCKET", "condominio-alerts").strip()
MIN_CONF      = float(os.getenv("MIN_CONFIDENCE", "70"))
REGION        = os.getenv("AWS_REGION", "us-east-1").strip()

rek = boto3.client("rekognition", region_name=REGION)
s3  = boto3.client("s3", region_name=REGION)

# =========================================
# Rekognition: corre el job y recoge labels
# =========================================
def start_and_collect_labels(s3_bucket: str, s3_key: str) -> List[Dict[str,Any]]:
    start = rek.start_label_detection(
        Video={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
        MinConfidence=MIN_CONF,
    )
    job_id = start["JobId"]
    labels, token = [], None
    for _ in range(240):  # ~12 min máx
        time.sleep(3)
        kw = {"JobId": job_id, "SortBy": "TIMESTAMP"}
        if token: kw["NextToken"] = token
        resp = rek.get_label_detection(**kw)
        if "Labels" in resp:
            labels += resp["Labels"]
        token = resp.get("NextToken")
        if resp.get("JobStatus") in ("SUCCEEDED","FAILED") and not token:
            break
    if resp.get("JobStatus") != "SUCCEEDED":
        raise RuntimeError(f"Rekognition failed: {resp.get('JobStatus')}")
    return labels

# =============================
# Normalización de labels/tiros
# =============================
def _group_by_ts(labels: List[Dict[str,Any]]) -> Dict[int,set]:
    by_ts = {}
    for it in labels:
        ts = int(it["Timestamp"])
        name = it["Label"]["Name"]
        conf = float(it["Label"].get("Confidence", 0))
        if conf < MIN_CONF:
            continue
        by_ts.setdefault(ts, set()).add(name)
    return by_ts

# ==================================================
# SOLO generamos: dog_loose, dog_waste, bad_parking
# ==================================================
def detect_events(labels: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    by_ts = _group_by_ts(labels)
    tss = sorted(by_ts.keys())
    events = []

    for ts in tss:
        names = by_ts[ts]

        # 1) Perro suelto: Dog sin Person cerca (+/-2s)
        if "Dog" in names:
            person_near = any("Person" in by_ts[t2] for t2 in tss if abs(t2-ts) <= 2000)
            if not person_near:
                events.append({"type": "dog_loose", "timestamp_ms": ts, "confidence": 90.0})

        # 2) Perro haciendo necesidades (heurística simple):
        #    Si aparecen etiquetas relacionadas con "Poop" / "Feces" / "Excrement" junto con Dog
        WASTE_LABELS = {"Poop", "Feces", "Excrement", "Animal Droppings", "Dung"}
        if "Dog" in names and any(lbl in names for lbl in WASTE_LABELS):
            events.append({"type": "dog_waste", "timestamp_ms": ts, "confidence": 85.0})

        # 3) Vehículo mal estacionado (por ahora, cualquier Car/Truck → bad_parking)
        if "Car" in names or "Truck" in names:
            events.append({"type": "bad_parking", "timestamp_ms": ts, "confidence": 80.0})

    # dedup por tipo cada 3s
    events.sort(key=lambda e: (e["type"], e["timestamp_ms"]))
    dedup, last = [], {}
    for e in events:
        t = e["type"]
        if t not in last or abs(e["timestamp_ms"] - last[t]) > 3000:
            dedup.append(e)
            last[t] = e["timestamp_ms"]
    return dedup

# ==================================
# Frame a thumb y subir a S3 (thumbs)
# ==================================
def _download_s3_to_tmp(bucket: str, key: str) -> str:
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(key)[1] or ".mp4")
    os.close(fd)
    s3.download_file(bucket, key, path)
    return path

def extract_frame_and_upload(bucket_in: str, key_in: str, timestamp_ms: int) -> str | None:
    try:
        import cv2  # import perezoso
    except ImportError:
        return None

    local_path = _download_s3_to_tmp(bucket_in, key_in)
    cap = cv2.VideoCapture(local_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_idx = int(round((timestamp_ms / 1000.0) * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None

    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    img_key = f"thumbs/{uuid.uuid4().hex}.jpg"
    s3.put_object(Bucket=OUTPUT_BUCKET, Key=img_key, Body=buf.tobytes(), ContentType="image/jpeg")
    try:
        os.remove(local_path)
    except Exception:
        pass
    return img_key

# ===========================================
# Pipeline principal para un video en S3
# ===========================================
def process_video_and_return_events(s3_key_video: str, camera_id: str | None = None) -> List[Dict[str,Any]]:
    labels = start_and_collect_labels(INPUT_BUCKET, s3_key_video)
    events = detect_events(labels)
    # agrega snapshot a cada evento
    ALLOWED = {"dog_loose", "dog_waste", "bad_parking"}
    out = []
    for e in events:
        if e["type"] not in ALLOWED:
            continue
        img_key = extract_frame_and_upload(INPUT_BUCKET, s3_key_video, e["timestamp_ms"])
        e["s3_image_key"] = img_key
        e["s3_video_key"] = s3_key_video
        e["camera_id"] = camera_id
        out.append(e)
    return out
