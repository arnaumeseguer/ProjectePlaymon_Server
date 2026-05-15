from flask import jsonify, Blueprint, request
from werkzeug.security import check_password_hash
from sqlalchemy import text
import jwt
import datetime
import os
import uuid
import pyotp

from api.Models.Base import SessionLocal
from api.Services.UserService import UserService

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
TWOFA_CHALLENGE_TTL_MINUTES = 5

user_login_bp = Blueprint("user_login", __name__)


def _request_meta():
    """Extrau IP i User-Agent de la request, amb suport per proxies."""
    fwd = request.headers.get("X-Forwarded-For", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.remote_addr or "")
    ua = (request.headers.get("User-Agent") or "")[:500]
    return ip, ua


def _log_attempt(db, user_id, success, ip, ua):
    """Registra l'intent (èxit o fallida) a login_history."""
    if user_id is None:
        return
    try:
        db.execute(text("""
            INSERT INTO login_history (user_id, success, ip_address, user_agent)
            VALUES (:uid, :ok, :ip, :ua)
        """), {"uid": user_id, "ok": success, "ip": ip, "ua": ua})
    except Exception:
        pass


def _issue_session_token(db, user, ip, ua, log_success=True):
    """Genera JWT definitiu + insereix sessió activa + notificació opcional."""
    jti = str(uuid.uuid4())
    payload = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "jti": jti,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    if log_success:
        _log_attempt(db, user.id, True, ip, ua)

    db.execute(text("""
        INSERT INTO active_sessions (user_id, jti, ip_address, user_agent)
        VALUES (:uid, :jti, :ip, :ua)
    """), {"uid": user.id, "jti": jti, "ip": ip, "ua": ua})

    if user.login_alerts_enabled:
        db.execute(text("""
            INSERT INTO notifications (user_id, title, message, type, auto_type)
            VALUES (:uid, :title, :msg, 'info', 'login_alert')
        """), {
            "uid": user.id,
            "title": "Nou inici de sessió al teu compte",
            "msg": f"S'ha detectat un nou inici de sessió des de {ip or 'un dispositiu desconegut'}. Si no has estat tu, revisa les teves sessions actives."
        })

    return token


def _issue_2fa_challenge_token(user_id):
    """Token curt (5 min) que només permet validar el codi 2FA — no és sessió."""
    payload = {
        "uid": user_id,
        "scope": "2fa_challenge",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=TWOFA_CHALLENGE_TTL_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


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

        # 2FA: si està activat, no emetem token de sessió encara — emetem
        # un token-challenge curt i el client haurà de validar amb /api/login/2fa
        if user.two_factor_enabled:
            challenge = _issue_2fa_challenge_token(user.id)
            db.commit()
            return jsonify({
                "requires_2fa": True,
                "temp_token": challenge,
            }), 200

        token = _issue_session_token(db, user, ip, ua)
        db.commit()
        return jsonify({"token": token, "user": user.to_dict()}), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error login", "detail": str(e)}), 500
    finally:
        db.close()


@user_login_bp.post("/api/login/2fa")
def login_2fa():
    """
    Segona passa del login quan l'usuari té 2FA activat.
    Espera: { temp_token: <challenge JWT>, code: <6 dígits TOTP> }
    Retorna el token de sessió definitiu si tot quadra.
    """
    data = request.get_json(silent=True) or {}
    temp_token = (data.get("temp_token") or "").strip()
    code = (data.get("code") or "").strip()

    if not temp_token or not code:
        return jsonify({"error": "Falta 'temp_token' o 'code'"}), 400
    if not code.isdigit() or len(code) != 6:
        return jsonify({"error": "Codi invàlid (6 dígits)"}), 400

    try:
        payload = jwt.decode(temp_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Sessió temporal caducada, torna a iniciar sessió"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token temporal invàlid"}), 401

    if payload.get("scope") != "2fa_challenge":
        return jsonify({"error": "Token temporal invàlid"}), 401

    uid = payload.get("uid")
    if not uid:
        return jsonify({"error": "Token temporal invàlid"}), 401

    ip, ua = _request_meta()
    db = SessionLocal()
    try:
        user = UserService.get_by_id(db, uid)
        if not user or not user.is_active:
            return jsonify({"error": "Usuari no vàlid"}), 401
        if not user.two_factor_enabled or not user.two_factor_secret:
            return jsonify({"error": "2FA no està configurat"}), 400

        totp = pyotp.TOTP(user.two_factor_secret)
        if not totp.verify(code, valid_window=2):
            _log_attempt(db, user.id, False, ip, ua)
            db.commit()
            return jsonify({"error": "Codi 2FA incorrecte"}), 400

        token = _issue_session_token(db, user, ip, ua)
        db.commit()
        return jsonify({"token": token, "user": user.to_dict()}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error login 2FA", "detail": str(e)}), 500
    finally:
        db.close()
