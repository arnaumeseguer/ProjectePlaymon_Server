"""
AuthMiddleware: decorador @require_auth reusable per a blueprints protegits.

Funcions:
  1. Valida el JWT del header Authorization: Bearer <token>
  2. Comprova que active_sessions.revoked_at IS NULL per al jti del token
  3. Actualitza last_seen de la sessió
  4. Injecta request.user_id / request.user_role / request.jti

Si qualsevol comprovació falla, retorna 401 i NO crida el handler.
"""

from functools import wraps
from flask import request, jsonify
from sqlalchemy import text
from datetime import datetime, timezone
import jwt
import os

from api.Models.Base import SessionLocal

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


def _extract_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None


def _decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]), None
    except jwt.ExpiredSignatureError:
        return None, ({"error": "Token expirat"}, 401)
    except jwt.InvalidTokenError:
        return None, ({"error": "Token invàlid"}, 401)


def require_auth(require_admin=False):
    """
    Decorador. Si require_admin=True nomes deixa passar role in ('admin','support').

    Ús:
        @user_security_bp.get("/api/users/me/sessions")
        @require_auth()
        def llista_sessions():
            uid = request.user_id
            ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _extract_token()
            if not token:
                return jsonify({"error": "Token no proporcionat"}), 401

            payload, err = _decode_token(token)
            if err:
                body, code = err
                return jsonify(body), code

            user_id = payload.get("id")
            jti = payload.get("jti")
            role = payload.get("role", "user")

            if not user_id:
                return jsonify({"error": "Token invàlid"}), 401

            if require_admin and role not in ("admin", "support"):
                return jsonify({"error": "Accés denegat"}), 403

            # Comprovar la sessió activa (només si el token porta jti — tokens
            # antics emesos abans del refactor encara seran acceptats).
            db = SessionLocal()
            try:
                if jti:
                    row = db.execute(text(
                        "SELECT id, revoked_at FROM active_sessions WHERE jti = :jti"
                    ), {"jti": jti}).fetchone()

                    if row is None:
                        return jsonify({"error": "Sessió no reconeguda"}), 401
                    if row.revoked_at is not None:
                        return jsonify({"error": "Sessió revocada"}), 401

                    # Actualitza last_seen
                    db.execute(text(
                        "UPDATE active_sessions SET last_seen = :now WHERE id = :sid"
                    ), {"now": datetime.now(timezone.utc), "sid": row.id})
                    db.commit()

                # Injectem dades al request perquè el handler les pugui llegir
                request.user_id = user_id
                request.user_role = role
                request.jti = jti

                return fn(*args, **kwargs)
            except Exception as e:
                db.rollback()
                return jsonify({"error": "Error autenticació", "detail": str(e)}), 500
            finally:
                db.close()

        return wrapper
    return decorator
