from flask import jsonify, Blueprint, request
import jwt
import os
from api.Models.Base import SessionLocal
from api.Models.VisitesOriginals import VisitesOriginals
from api.Models.VisitesOriginalsGenerals import VisitesOriginalsGenerals

visites_originals_bp = Blueprint("visites_originals", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


def _get_user_id():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, (jsonify({"error": "Token no proporcionat"}), 401)
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        uid = payload.get("id")
        if not uid:
            return None, (jsonify({"error": "Token invàlid"}), 401)
        return uid, None
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Token expirat"}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"error": "Token invàlid"}), 401)


@visites_originals_bp.get("/api/visites-originals/counts")
def get_counts():
    """Returns total view counts per video from visites_originals_generals."""
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        rows = db.query(VisitesOriginalsGenerals).all()
        counts = {str(r.video_id): r.view_count for r in rows}
        return jsonify({"counts": counts})
    finally:
        db.close()


@visites_originals_bp.post("/api/visites-originals")
def record_view():
    """
    Records a view for a video.
    - visites_originals: upsert (unique per user-video, tracks unique viewers)
    - visites_originals_generals: increments total counter
    Returns new total view_count.
    """
    user_id, err = _get_user_id()
    if err:
        return err
    data = request.get_json() or {}
    try:
        video_id = int(data.get("video_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "video_id invàlid"}), 400

    db = SessionLocal()
    try:
        # Unique viewer tracking (ignore if already viewed)
        existing = db.query(VisitesOriginals).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if not existing:
            db.add(VisitesOriginals(user_id=user_id, video_id=video_id))

        # General counter: always increment (client deduplicates per session)
        general = db.query(VisitesOriginalsGenerals).filter_by(video_id=video_id).first()
        if general:
            general.view_count += 1
        else:
            general = VisitesOriginalsGenerals(video_id=video_id, view_count=1)
            db.add(general)

        db.commit()
        db.refresh(general)
        return jsonify({"view_count": general.view_count}), 200
    finally:
        db.close()
