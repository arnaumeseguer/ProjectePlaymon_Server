from flask import jsonify, Blueprint, request
from datetime import datetime, timezone
import jwt, os
from api.Models.Base import SessionLocal
from api.Models.PlaymonSeguirViendo import PlaymonSeguirViendo

playmon_seguir_viendo_bp = Blueprint("playmon_seguir_viendo", __name__)

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


@playmon_seguir_viendo_bp.get("/api/playmon-seguir-viendo")
def get_seguir_viendo():
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        items = db.query(PlaymonSeguirViendo).filter(
            PlaymonSeguirViendo.user_id == user_id
        ).order_by(PlaymonSeguirViendo.updated_at.desc()).all()
        return jsonify([i.to_dict() for i in items])
    finally:
        db.close()


@playmon_seguir_viendo_bp.post("/api/playmon-seguir-viendo")
def save_progress():
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
        existing = db.query(PlaymonSeguirViendo).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if existing:
            existing.progress = data.get("progress", existing.progress)
            existing.duration = data.get("duration", existing.duration)
            existing.title = data.get("title", existing.title)
            existing.thumbnail_url = data.get("thumbnail_url", existing.thumbnail_url)
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(existing)
            return jsonify(existing.to_dict()), 200

        item = PlaymonSeguirViendo(
            user_id=user_id,
            video_id=video_id,
            title=data.get("title"),
            thumbnail_url=data.get("thumbnail_url"),
            progress=data.get("progress", 0),
            duration=data.get("duration", 0),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(item.to_dict()), 201
    finally:
        db.close()


@playmon_seguir_viendo_bp.delete("/api/playmon-seguir-viendo/<int:video_id>")
def remove_progress(video_id):
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        item = db.query(PlaymonSeguirViendo).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if not item:
            return jsonify({"ok": True})
        db.delete(item)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
