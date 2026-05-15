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
import base64
import io
import pyotp
import qrcode

from api.Models.Base import SessionLocal
from api.Services.AuthMiddleware import require_auth

user_security_bp = Blueprint("user_security", __name__)

TOTP_ISSUER = "Playmon"


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
    if not current_jti:
        # Token sense jti: no podem identificar quina és la sessió actual,
        # així que rebutgem per no matar-la accidentalment.
        return jsonify({"error": "Token sense identificador de sessió. Torna a iniciar sessió."}), 400
    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE active_sessions
            SET revoked_at = :now
            WHERE user_id = :uid AND revoked_at IS NULL AND jti != :jti
        """), {"uid": uid, "jti": current_jti, "now": datetime.now(timezone.utc)})
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

        # Revoca totes les altres sessions (només si tenim jti per identificar
        # l'actual; si no, deixem-les actives — l'usuari pot fer-ho manualment).
        if current_jti:
            db.execute(text("""
                UPDATE active_sessions
                SET revoked_at = :now
                WHERE user_id = :uid AND revoked_at IS NULL AND jti != :jti
            """), {"uid": uid, "jti": current_jti, "now": now})

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


# ─── 2FA (pyotp) ───────────────────────────────────────────────────────────────

def _generate_qr_data_uri(otpauth_url):
    """Genera una imatge QR base64 (data URI) a partir d'un otpauth URL."""
    img = qrcode.make(otpauth_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ── POST /api/users/me/2fa/enable ─────────────────────────────────────────────
@user_security_bp.post("/api/users/me/2fa/enable")
@require_auth()
def enable_2fa():
    """
    Genera un secret TOTP pendent. L'usuari ha de confirmar amb
    POST /2fa/verify abans que two_factor_enabled passi a TRUE.
    """
    uid = request.user_id
    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT username, email, two_factor_enabled FROM users WHERE id = :uid"
        ), {"uid": uid}).fetchone()

        if not row:
            return jsonify({"error": "Usuari no trobat"}), 404
        if row.two_factor_enabled:
            return jsonify({"error": "2FA ja està activat"}), 400

        secret = pyotp.random_base32()
        otpauth_url = pyotp.totp.TOTP(secret).provisioning_uri(
            name=row.email or row.username,
            issuer_name=TOTP_ISSUER
        )

        db.execute(text(
            "UPDATE users SET two_factor_secret = :s WHERE id = :uid"
        ), {"s": secret, "uid": uid})
        db.commit()

        return jsonify({
            "secret": secret,
            "otpauth_url": otpauth_url,
            "qr_data_uri": _generate_qr_data_uri(otpauth_url),
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── POST /api/users/me/2fa/verify ─────────────────────────────────────────────
@user_security_bp.post("/api/users/me/2fa/verify")
@require_auth()
def verify_2fa():
    """Confirma activació validant un codi TOTP."""
    uid = request.user_id
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"error": "Codi invàlid (6 dígits)"}), 400

    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT two_factor_secret, two_factor_enabled FROM users WHERE id = :uid"
        ), {"uid": uid}).fetchone()

        if not row or not row.two_factor_secret:
            return jsonify({"error": "Cap secret pendent. Genera'n un primer."}), 400
        if row.two_factor_enabled:
            return jsonify({"error": "2FA ja està activat"}), 400

        totp = pyotp.TOTP(row.two_factor_secret)
        if not totp.verify(code, valid_window=2):
            return jsonify({"error": "Codi incorrecte"}), 400

        db.execute(text(
            "UPDATE users SET two_factor_enabled = TRUE WHERE id = :uid"
        ), {"uid": uid})

        db.execute(text("""
            INSERT INTO notifications (user_id, title, message, type, auto_type)
            VALUES (:uid, :title, :msg, 'info', '2fa_enabled')
        """), {
            "uid": uid,
            "title": "Verificació en dos passos activada",
            "msg": "El teu compte ara està protegit amb 2FA."
        })

        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── POST /api/users/me/2fa/disable ────────────────────────────────────────────
@user_security_bp.post("/api/users/me/2fa/disable")
@require_auth()
def disable_2fa():
    """Desactiva 2FA — requereix un codi TOTP vàlid."""
    uid = request.user_id
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()

    if not code or not code.isdigit() or len(code) != 6:
        return jsonify({"error": "Codi invàlid (6 dígits)"}), 400

    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT two_factor_secret, two_factor_enabled FROM users WHERE id = :uid"
        ), {"uid": uid}).fetchone()

        if not row or not row.two_factor_enabled or not row.two_factor_secret:
            return jsonify({"error": "2FA no està activat"}), 400

        totp = pyotp.TOTP(row.two_factor_secret)
        if not totp.verify(code, valid_window=2):
            return jsonify({"error": "Codi incorrecte"}), 400

        db.execute(text("""
            UPDATE users
            SET two_factor_enabled = FALSE, two_factor_secret = NULL
            WHERE id = :uid
        """), {"uid": uid})

        db.execute(text("""
            INSERT INTO notifications (user_id, title, message, type, auto_type)
            VALUES (:uid, :title, :msg, 'warning', '2fa_disabled')
        """), {
            "uid": uid,
            "title": "Verificació en dos passos desactivada",
            "msg": "Has desactivat el 2FA. La teva única protecció ara és la contrasenya."
        })

        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
