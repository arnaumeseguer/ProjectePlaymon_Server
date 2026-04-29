from flask import jsonify, Blueprint, request
import jwt
import os
from api.Models.Base import SessionLocal
from api.Models.LlistaOriginals import LlistaOriginals

llista_originals_bp = Blueprint("llista_originals", __name__)

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


@llista_originals_bp.get("/api/llista-originals")
def get_llista():
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        items = db.query(LlistaOriginals).filter(
            LlistaOriginals.user_id == user_id
        ).order_by(LlistaOriginals.created_at.desc()).all()
        return jsonify([i.to_dict() for i in items])
    finally:
        db.close()


@llista_originals_bp.post("/api/llista-originals")
def add_to_llista():
    user_id, err = _get_user_id()
    if err:
        return err
    data = request.get_json() or {}
    video_id = data.get("video_id")
    if not video_id:
        return jsonify({"error": "video_id requerit"}), 400

    try:
        video_id_int = int(video_id)
    except ValueError:
        return jsonify({"error": "video_id invàlid"}), 400

    db = SessionLocal()
    try:
        existing = db.query(LlistaOriginals).filter_by(
            user_id=user_id, video_id=video_id_int
        ).first()
        if existing:
            return jsonify(existing.to_dict()), 200

        item = LlistaOriginals(
            user_id=user_id,
            video_id=video_id_int,
            title=data.get("title"),
            thumbnail_url=data.get("thumbnail_url"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(item.to_dict()), 201
    finally:
        db.close()


@llista_originals_bp.delete("/api/llista-originals/<int:video_id>")
def remove_from_llista(video_id):
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        item = db.query(LlistaOriginals).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if not item:
            return jsonify({"error": "No trobat"}), 404
        db.delete(item)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
