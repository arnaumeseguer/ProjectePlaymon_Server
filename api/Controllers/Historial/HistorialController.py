from flask import jsonify, Blueprint, request
from datetime import datetime, timezone
import jwt
import os
from api.Models.Base import SessionLocal
from api.Models.HistorialVisualitzacio import HistorialVisualitzacio

historial_bp = Blueprint("historial", __name__)

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


@historial_bp.get("/api/historial")
def get_historial():
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        items = (
            db.query(HistorialVisualitzacio)
            .filter(HistorialVisualitzacio.user_id == user_id)
            .order_by(HistorialVisualitzacio.updated_at.desc())
            .all()
        )
        return jsonify([i.to_dict() for i in items])
    finally:
        db.close()


@historial_bp.post("/api/historial")
def add_historial():
    user_id, err = _get_user_id()
    if err:
        return err
    data = request.get_json() or {}
    tmdb_id = data.get("tmdb_id") or data.get("id")
    media_type = data.get("media_type", "movie")
    if not tmdb_id:
        return jsonify({"error": "tmdb_id requerit"}), 400

    db = SessionLocal()
    try:
        existing = db.query(HistorialVisualitzacio).filter_by(
            user_id=user_id, tmdb_id=tmdb_id, media_type=media_type
        ).first()
        if existing:
            existing.updated_at = datetime.now(timezone.utc)
            existing.title = data.get("title") or data.get("name") or existing.title
            existing.poster_path = data.get("poster_path") or existing.poster_path
            existing.backdrop_path = data.get("backdrop_path") or existing.backdrop_path
            db.commit()
            return jsonify(existing.to_dict()), 200

        entry = HistorialVisualitzacio(
            user_id=user_id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            title=data.get("title") or data.get("name"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return jsonify(entry.to_dict()), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@historial_bp.delete("/api/historial/<int:tmdb_id>/<string:media_type>")
def remove_historial(tmdb_id, media_type):
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        entry = db.query(HistorialVisualitzacio).filter_by(
            user_id=user_id, tmdb_id=tmdb_id, media_type=media_type
        ).first()
        if not entry:
            return jsonify({"error": "No trobat"}), 404
        db.delete(entry)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@historial_bp.delete("/api/historial")
def clear_historial():
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        db.query(HistorialVisualitzacio).filter_by(user_id=user_id).delete()
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
