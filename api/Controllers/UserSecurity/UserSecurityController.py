"""
Blueprint user_security_bp: endpoints de seguretat i sessions actives.

GET    /api/users/me/sessions              → llista sessions actives
DELETE /api/users/me/sessions/<id>         → revoca una sessió
DELETE /api/users/me/sessions              → revoca totes (excepte l'actual)
GET    /api/users/me/login-history?limit=N → històric de logins
GET    /api/users/me/security              → flags + recuperació
PUT    /api/users/me/security              → update flags + recuperació
POST   /api/users/me/password              → canvi de contrasenya
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timezone

from api.Models.Base import SessionLocal
from api.Services.AuthMiddleware import require_auth

user_security_bp = Blueprint("user_security", __name__)


# ── GET /api/users/me/sessions ────────────────────────────────────────────────
@user_security_bp.get("/api/users/me/sessions")
@require_auth()
def list_sessions():
    uid = request.user_id
    current_jti = request.jti

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT id, jti, created_at, last_seen, ip_address, user_agent
            FROM active_sessions
            WHERE user_id = :uid AND revoked_at IS NULL
            ORDER BY last_seen DESC
        """), {"uid": uid}).fetchall()

        sessions = [{
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            "ip_address": r.ip_address,
            "user_agent": r.user_agent,
            "is_current": (r.jti == current_jti),
        } for r in rows]

        return jsonify(sessions), 200
    finally:
        db.close()


# ── DELETE /api/users/me/sessions/<id> ────────────────────────────────────────
@user_security_bp.delete("/api/users/me/sessions/<int:session_id>")
@require_auth()
def revoke_session(session_id):
    uid = request.user_id
    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT id FROM active_sessions WHERE id = :sid AND user_id = :uid"
        ), {"sid": session_id, "uid": uid}).fetchone()

        if not row:
            return jsonify({"error": "Sessió no trobada"}), 404

        db.execute(text("""
            UPDATE active_sessions
            SET revoked_at = :now
            WHERE id = :sid AND revoked_at IS NULL
        """), {"sid": session_id, "now": datetime.now(timezone.utc)})
        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── DELETE /api/users/me/sessions (totes excepte l'actual) ────────────────────
@user_security_bp.delete("/api/users/me/sessions")
@require_auth()
def revoke_all_other_sessions():
    uid = request.user_id
    current_jti = request.jti
    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE active_sessions
            SET revoked_at = :now
            WHERE user_id = :uid AND revoked_at IS NULL AND jti != :jti
        """), {"uid": uid, "jti": current_jti or "", "now": datetime.now(timezone.utc)})
        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── GET /api/users/me/login-history ───────────────────────────────────────────
@user_security_bp.get("/api/users/me/login-history")
@require_auth()
def login_history():
    uid = request.user_id
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 100))

    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT id, created_at, ip_address, user_agent, success, country
            FROM login_history
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT :lim
        """), {"uid": uid, "lim": limit}).fetchall()

        return jsonify([{
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "ip_address": r.ip_address,
            "user_agent": r.user_agent,
            "success": r.success,
            "country": r.country,
        } for r in rows]), 200
    finally:
        db.close()


# ── GET /api/users/me/security ────────────────────────────────────────────────
@user_security_bp.get("/api/users/me/security")
@require_auth()
def get_security():
    uid = request.user_id
    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT two_factor_enabled, login_alerts_enabled,
                   recovery_email, recovery_phone,
                   password_changed_at, telefon, idioma
            FROM users WHERE id = :uid
        """), {"uid": uid}).fetchone()

        if not row:
            return jsonify({"error": "Usuari no trobat"}), 404

        active_count = db.execute(text("""
            SELECT COUNT(*) AS c FROM active_sessions
            WHERE user_id = :uid AND revoked_at IS NULL
        """), {"uid": uid}).fetchone().c

        return jsonify({
            "two_factor_enabled": row.two_factor_enabled,
            "login_alerts_enabled": row.login_alerts_enabled,
            "recovery_email": row.recovery_email,
            "recovery_phone": row.recovery_phone,
            "telefon": row.telefon,
            "idioma": row.idioma,
            "password_changed_at": row.password_changed_at.isoformat() if row.password_changed_at else None,
            "active_sessions_count": int(active_count or 0),
        }), 200
    finally:
        db.close()


# ── PUT /api/users/me/security ────────────────────────────────────────────────
@user_security_bp.put("/api/users/me/security")
@require_auth()
def update_security():
    uid = request.user_id
    data = request.get_json(silent=True) or {}

    allowed = {
        "login_alerts_enabled": bool,
        "recovery_email": str,
        "recovery_phone": str,
    }
    updates = {}
    for key, typ in allowed.items():
        if key in data:
            val = data[key]
            if val is None or val == "":
                updates[key] = None
            else:
                try:
                    updates[key] = typ(val)
                except Exception:
                    return jsonify({"error": f"Camp invàlid: {key}"}), 400

    if not updates:
        return jsonify({"error": "Cap camp vàlid per actualitzar"}), 400

    set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
    params = {**updates, "uid": uid}

    db = SessionLocal()
    try:
        db.execute(text(f"UPDATE users SET {set_clause} WHERE id = :uid"), params)
        db.commit()
        return jsonify({"ok": True, **updates}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── POST /api/users/me/password ───────────────────────────────────────────────
@user_security_bp.post("/api/users/me/password")
@require_auth()
def change_password():
    uid = request.user_id
    current_jti = request.jti
    data = request.get_json(silent=True) or {}
    current_password = (data.get("current_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not current_password or not new_password:
        return jsonify({"error": "Falten 'current_password' o 'new_password'"}), 400
    if len(new_password) < 8:
        return jsonify({"error": "La nova contrasenya ha de tenir mínim 8 caràcters"}), 400
    if new_password == current_password:
        return jsonify({"error": "La nova contrasenya no pot ser igual a l'actual"}), 400

    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT password_hash FROM users WHERE id = :uid"
        ), {"uid": uid}).fetchone()

        if not row:
            return jsonify({"error": "Usuari no trobat"}), 404

        password_ok = (
            check_password_hash(row.password_hash, current_password)
            or row.password_hash == current_password
        )
        if not password_ok:
            return jsonify({"error": "Contrasenya actual incorrecta"}), 401

        new_hash = generate_password_hash(new_password)
        now = datetime.now(timezone.utc)

        db.execute(text("""
            UPDATE users
            SET password_hash = :ph, password_changed_at = :now
            WHERE id = :uid
        """), {"ph": new_hash, "now": now, "uid": uid})

        # Revoca totes les altres sessions
        db.execute(text("""
            UPDATE active_sessions
            SET revoked_at = :now
            WHERE user_id = :uid AND revoked_at IS NULL AND jti != :jti
        """), {"uid": uid, "jti": current_jti or "", "now": now})

        # Notificació de canvi de contrasenya
        db.execute(text("""
            INSERT INTO notifications (user_id, title, message, type, auto_type)
            VALUES (:uid, :title, :msg, 'info', 'password_changed')
        """), {
            "uid": uid,
            "title": "Contrasenya actualitzada",
            "msg": "La teva contrasenya s'ha canviat correctament. Les altres sessions s'han tancat per seguretat."
        })

        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
