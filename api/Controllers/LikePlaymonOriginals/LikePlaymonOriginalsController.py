from flask import jsonify, Blueprint, request
from sqlalchemy import func
import jwt
import os
from api.Models.Base import SessionLocal
from api.Models.LikePlaymonOriginals import LikePlaymonOriginals

like_playmon_originals_bp = Blueprint("like_playmon_originals", __name__)

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


@like_playmon_originals_bp.get("/api/like-playmon-originals")
def get_likes():
    """Returns my liked video_ids + global counts for all videos."""
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        my_rows = db.query(LikePlaymonOriginals.video_id).filter(
            LikePlaymonOriginals.user_id == user_id
        ).all()
        my_likes = [r.video_id for r in my_rows]

        count_rows = db.query(
            LikePlaymonOriginals.video_id,
            func.count(LikePlaymonOriginals.id).label("cnt")
        ).group_by(LikePlaymonOriginals.video_id).all()
        counts = {str(r.video_id): r.cnt for r in count_rows}

        return jsonify({"my_likes": my_likes, "counts": counts})
    finally:
        db.close()


@like_playmon_originals_bp.post("/api/like-playmon-originals")
def add_like():
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
        existing = db.query(LikePlaymonOriginals).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if existing:
            return jsonify({"ok": True}), 200
        db.add(LikePlaymonOriginals(user_id=user_id, video_id=video_id))
        db.commit()
        return jsonify({"ok": True}), 201
    finally:
        db.close()


@like_playmon_originals_bp.delete("/api/like-playmon-originals/<int:video_id>")
def remove_like(video_id):
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        item = db.query(LikePlaymonOriginals).filter_by(
            user_id=user_id, video_id=video_id
        ).first()
        if item:
            db.delete(item)
            db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
