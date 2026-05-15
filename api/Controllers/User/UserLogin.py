from flask import jsonify, Blueprint, request
from werkzeug.security import check_password_hash
from sqlalchemy import text
import jwt
import datetime
import os
import uuid

from api.Models.Base import SessionLocal
from api.Services.UserService import UserService

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

user_login_bp = Blueprint("user_login", __name__)


def _request_meta():
    """Extrau IP i User-Agent de la request, amb suport per proxies."""
    fwd = request.headers.get("X-Forwarded-For", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.remote_addr or "")
    ua = (request.headers.get("User-Agent") or "")[:500]
    return ip, ua


def _log_attempt(db, user_id, success, ip, ua):
    """Registra l'intent (èxit o fallida) a login_history. user_id pot ser None."""
    if user_id is None:
        return
    try:
        db.execute(text("""
            INSERT INTO login_history (user_id, success, ip_address, user_agent)
            VALUES (:uid, :ok, :ip, :ua)
        """), {"uid": user_id, "ok": success, "ip": ip, "ua": ua})
    except Exception:
        pass  # Mai bloquegem el login per un error de log


@user_login_bp.post("/api/login")
def login_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Falta 'username' o 'password'"}), 400

    ip, ua = _request_meta()
    db = SessionLocal()
    try:
        user = UserService.get_by_username(db, username)

        if not user:
            return jsonify({"error": "Credencials incorrectes"}), 401

        password_ok = (
            check_password_hash(user.password_hash, password)
            or user.password_hash == password
        )

        if not password_ok:
            _log_attempt(db, user.id, False, ip, ua)
            db.commit()
            return jsonify({"error": "Credencials incorrectes"}), 401

        if not user.is_active:
            _log_attempt(db, user.id, False, ip, ua)
            db.commit()
            return jsonify({"error": "Compte d'usuari desactivat"}), 403

        # JWT amb jti únic
        jti = str(uuid.uuid4())
        payload = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "jti": jti,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Registra login exitós
        _log_attempt(db, user.id, True, ip, ua)

        # Registra sessió activa
        db.execute(text("""
            INSERT INTO active_sessions (user_id, jti, ip_address, user_agent)
            VALUES (:uid, :jti, :ip, :ua)
        """), {"uid": user.id, "jti": jti, "ip": ip, "ua": ua})

        # Notificació opcional si l'usuari té alertes activades
        if user.login_alerts_enabled:
            db.execute(text("""
                INSERT INTO notifications (user_id, title, message, type, auto_type)
                VALUES (:uid, :title, :msg, 'info', 'login_alert')
            """), {
                "uid": user.id,
                "title": "Nou inici de sessió al teu compte",
                "msg": f"S'ha detectat un nou inici de sessió des de {ip or 'un dispositiu desconegut'}. Si no has estat tu, revisa les teves sessions actives."
            })

        db.commit()

        return jsonify({
            "token": token,
            "user": user.to_dict()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error login", "detail": str(e)}), 500
    finally:
        db.close()
