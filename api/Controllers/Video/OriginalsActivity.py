from flask import jsonify, Blueprint, request
import jwt
import os
from api.Models.Base import SessionLocal
from sqlalchemy import text

originals_activity_bp = Blueprint("originals_activity", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


def _get_user_id():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, ({"error": "Token no proporcionat"}, 401)
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        uid = payload.get("id")
        if not uid:
            return None, ({"error": "Token inválid"}, 401)
        return uid, None
    except jwt.ExpiredSignatureError:
        return None, ({"error": "Token expirat"}, 401)
    except jwt.InvalidTokenError:
        return None, ({"error": "Token inválid"}, 401)


# ── Historial ────────────────────────────────────────────────────────────────

@originals_activity_bp.post("/api/originals/history")
def add_history():
    user_id, err = _get_user_id()
    if err:
        return jsonify(err[0]), err[1]

    data = request.get_json(silent=True) or {}
    video_id = data.get("video_id")
    if not video_id:
        return jsonify({"error": "video_id requerit"}), 400

    db = SessionLocal()
    try:
        db.execute(text("""
            INSERT INTO originals_history (user_id, video_id, watched_at)
            VALUES (:uid, :vid, NOW())
            ON CONFLICT (user_id, video_id) DO UPDATE SET watched_at = NOW()
        """), {"uid": user_id, "vid": int(video_id)})
        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@originals_activity_bp.get("/api/originals/history")
def get_history():
    user_id, err = _get_user_id()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT oh.video_id, oh.watched_at
            FROM originals_history oh
            JOIN videos v ON v.id = oh.video_id
            WHERE oh.user_id = :uid
            ORDER BY oh.watched_at DESC
            LIMIT 50
        """), {"uid": user_id}).fetchall()
        return jsonify([
            {"videoId": str(r.video_id), "watchedAt": r.watched_at.isoformat()}
            for r in rows
        ]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@originals_activity_bp.delete("/api/originals/history")
def clear_history():
    user_id, err = _get_user_id()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM originals_history WHERE user_id = :uid"), {"uid": user_id})
        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── Watchlist ────────────────────────────────────────────────────────────────

@originals_activity_bp.post("/api/originals/watchlist/<int:video_id>")
def toggle_watchlist(video_id):
    user_id, err = _get_user_id()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        existing = db.execute(text("""
            SELECT 1 FROM originals_watchlist
            WHERE user_id = :uid AND video_id = :vid
        """), {"uid": user_id, "vid": video_id}).fetchone()

        if existing:
            db.execute(text("""
                DELETE FROM originals_watchlist WHERE user_id = :uid AND video_id = :vid
            """), {"uid": user_id, "vid": video_id})
            saved = False
        else:
            db.execute(text("""
                INSERT INTO originals_watchlist (user_id, video_id) VALUES (:uid, :vid)
            """), {"uid": user_id, "vid": video_id})
            saved = True

        db.commit()
        return jsonify({"ok": True, "saved": saved}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@originals_activity_bp.get("/api/originals/watchlist")
def get_watchlist():
    user_id, err = _get_user_id()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT ow.video_id
            FROM originals_watchlist ow
            JOIN videos v ON v.id = ow.video_id
            WHERE ow.user_id = :uid
            ORDER BY ow.saved_at DESC
        """), {"uid": user_id}).fetchall()
        return jsonify([str(r.video_id) for r in rows]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
