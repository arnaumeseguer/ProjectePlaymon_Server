from flask import jsonify, Blueprint, request
import jwt
import os
from api.Models.Base import SessionLocal
from api.Models.Watchlist import Watchlist

watchlist_bp = Blueprint("watchlist", __name__)

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


@watchlist_bp.get("/api/watchlist")
def get_watchlist():
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        items = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
        return jsonify([i.to_dict() for i in items])
    finally:
        db.close()


@watchlist_bp.post("/api/watchlist")
def add_to_watchlist():
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
        existing = db.query(Watchlist).filter_by(
            user_id=user_id, tmdb_id=tmdb_id, media_type=media_type
        ).first()
        if existing:
            return jsonify(existing.to_dict()), 200

        item = Watchlist(
            user_id=user_id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            title=data.get("title") or data.get("name"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            overview=data.get("overview"),
            release_date=data.get("release_date"),
            first_air_date=data.get("first_air_date"),
            vote_average=data.get("vote_average"),
            genres=data.get("genres", []),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(item.to_dict()), 201
    finally:
        db.close()


@watchlist_bp.delete("/api/watchlist/<int:tmdb_id>/<string:media_type>")
def remove_from_watchlist(tmdb_id, media_type):
    user_id, err = _get_user_id()
    if err:
        return err
    db = SessionLocal()
    try:
        item = db.query(Watchlist).filter_by(
            user_id=user_id, tmdb_id=tmdb_id, media_type=media_type
        ).first()
        if not item:
            return jsonify({"error": "No trobat"}), 404
        db.delete(item)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
