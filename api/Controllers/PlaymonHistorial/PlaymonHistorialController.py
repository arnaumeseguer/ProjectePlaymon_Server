from flask import jsonify, Blueprint, request
from datetime import datetime, timezone
import jwt, os
from api.Models.Base import SessionLocal
from api.Models.PlaymonHistorial import PlaymonHistorial

playmon_historial_bp = Blueprint("playmon_historial", __name__)

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


@playmon_historial_bp.get("/api/playmon-historial")
def get_historial():
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        items = db.query(PlaymonHistorial).filter(
            PlaymonHistorial.user_id == user_id
        ).order_by(PlaymonHistorial.updated_at.desc()).all()
        return jsonify([i.to_dict() for i in items])
    finally:
        db.close()


@playmon_historial_bp.post("/api/playmon-historial")
def add_to_historial():
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
        existing = db.query(PlaymonHistorial).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if existing:
            existing.updated_at = datetime.now(timezone.utc)
            existing.title = data.get("title", existing.title)
            existing.thumbnail_url = data.get("thumbnail_url", existing.thumbnail_url)
            db.commit()
            db.refresh(existing)
            return jsonify(existing.to_dict()), 200

        item = PlaymonHistorial(
            user_id=user_id,
            video_id=video_id,
            title=data.get("title"),
            thumbnail_url=data.get("thumbnail_url"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(item.to_dict()), 201
    finally:
        db.close()


@playmon_historial_bp.delete("/api/playmon-historial/<int:video_id>")
def remove_from_historial(video_id):
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        item = db.query(PlaymonHistorial).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if not item:
            return jsonify({"error": "No trobat"}), 404
        db.delete(item)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
