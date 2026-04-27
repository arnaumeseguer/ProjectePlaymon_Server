from flask import jsonify, Blueprint, request
import jwt
import os
from datetime import datetime, timezone, timedelta
from api.Models.Base import SessionLocal
from sqlalchemy import text

notifications_bp = Blueprint("notifications", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

PAID_PLANS = ('super', 'ultra')


def _get_user(require_admin=False):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, None, ({"error": "Token no proporcionat"}, 401)
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
        uid = payload.get("id")
        role = payload.get("role", "user")
        if not uid:
            return None, None, ({"error": "Token inválid"}, 401)
        if require_admin and role not in ("admin", "support"):
            return None, None, ({"error": "Accés denegat"}, 403)
        return uid, role, None
    except jwt.ExpiredSignatureError:
        return None, None, ({"error": "Token expirat"}, 401)
    except jwt.InvalidTokenError:
        return None, None, ({"error": "Token inválid"}, 401)


def check_subscription_expiry(db, user_id):
    """Genera notificacions automàtiques de caducitat. Idempotent."""
    row = db.execute(text(
        "SELECT pla_pagament, subscripcio_fi FROM users WHERE id = :uid"
    ), {"uid": user_id}).fetchone()

    if not row or not row.subscripcio_fi or (row.pla_pagament or '') not in PAID_PLANS:
        return

    now = datetime.now(timezone.utc)
    fi = row.subscripcio_fi
    if fi.tzinfo is None:
        fi = fi.replace(tzinfo=timezone.utc)

    days_left = (fi - now).days

    if days_left < 0:
        # Subscripció caducada — baixar a bàsic
        db.execute(text(
            "UPDATE users SET pla_pagament = 'basic', subscripcio_fi = NULL WHERE id = :uid"
        ), {"uid": user_id})
        _ensure_auto_notif(db, user_id, 'expired',
                           'Subscripció caducada',
                           'La teva subscripció ha caducat. Renova-la per continuar gaudint de totes les funcions.',
                           'alert', hours=24)
        return

    # Avisos progressius (només el més urgent si no existeix ja)
    thresholds = [
        (1,  'expiry_1d', '⚠️ La subscripció caduca demà',
         'Queda menys de 24 hores perquè la teva subscripció expiri. Renova-la ara per no perdre l\'accés.',
         'alert'),
        (3,  'expiry_3d', 'La subscripció caduca en 3 dies',
         'La teva subscripció expira el {}. Renova-la per continuar sense interrupcions.'.format(fi.strftime('%d/%m/%Y')),
         'warning'),
        (7,  'expiry_7d', 'La subscripció caduca en 7 dies',
         'Recorda que la teva subscripció expira el {}. Pots renovar-la des de la secció de pagaments.'.format(fi.strftime('%d/%m/%Y')),
         'info'),
    ]
    for days, auto_type, title, message, ntype in thresholds:
        if days_left <= days:
            _ensure_auto_notif(db, user_id, auto_type, title, message, ntype, hours=20)
            break


def _ensure_auto_notif(db, user_id, auto_type, title, message, ntype, hours=20):
    existing = db.execute(text("""
        SELECT 1 FROM notifications
        WHERE user_id = :uid AND auto_type = :at
          AND created_at > NOW() - INTERVAL '{h} hours'
    """.format(h=hours)), {"uid": user_id, "at": auto_type}).fetchone()
    if not existing:
        db.execute(text("""
            INSERT INTO notifications (user_id, title, message, type, auto_type)
            VALUES (:uid, :title, :msg, :type, :at)
        """), {"uid": user_id, "title": title, "msg": message, "type": ntype, "at": auto_type})


# ── GET /api/notifications ────────────────────────────────────────────────────

@notifications_bp.get("/api/notifications")
def get_notifications():
    user_id, _, err = _get_user()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        # Comprova caducitat en cada consulta (lazy check)
        check_subscription_expiry(db, user_id)
        db.commit()

        # Notificacions personals
        personal = db.execute(text("""
            SELECT id, title, message, type, auto_type, is_read, created_at, FALSE as is_global
            FROM notifications
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 50
        """), {"uid": user_id}).fetchall()

        # Notificacions globals (user_id IS NULL), marcant si l'usuari les ha llegit
        global_notifs = db.execute(text("""
            SELECT n.id, n.title, n.message, n.type, n.auto_type, n.created_at, TRUE as is_global,
                   EXISTS (
                       SELECT 1 FROM notification_reads nr
                       WHERE nr.user_id = :uid AND nr.notification_id = n.id
                   ) as is_read
            FROM notifications n
            WHERE n.user_id IS NULL
            ORDER BY n.created_at DESC
            LIMIT 20
        """), {"uid": user_id}).fetchall()

        def row_to_dict(r, is_global):
            return {
                "id": r.id,
                "title": r.title,
                "message": r.message,
                "type": r.type,
                "auto_type": r.auto_type,
                "is_read": bool(r.is_read),
                "is_global": is_global,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }

        result = (
            [row_to_dict(r, False) for r in personal] +
            [row_to_dict(r, True)  for r in global_notifs]
        )
        result.sort(key=lambda x: x["created_at"] or "", reverse=True)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── POST /api/notifications/<id>/read ────────────────────────────────────────

@notifications_bp.post("/api/notifications/<int:notif_id>/read")
def mark_read(notif_id):
    user_id, _, err = _get_user()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        notif = db.execute(text(
            "SELECT user_id FROM notifications WHERE id = :id"
        ), {"id": notif_id}).fetchone()

        if not notif:
            return jsonify({"error": "Notificació no trobada"}), 404

        if notif.user_id is None:
            # Global: inserir a notification_reads
            db.execute(text("""
                INSERT INTO notification_reads (user_id, notification_id)
                VALUES (:uid, :nid) ON CONFLICT DO NOTHING
            """), {"uid": user_id, "nid": notif_id})
        elif notif.user_id == user_id:
            db.execute(text(
                "UPDATE notifications SET is_read = TRUE WHERE id = :id"
            ), {"id": notif_id})
        else:
            return jsonify({"error": "Accés denegat"}), 403

        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── POST /api/notifications/read-all ─────────────────────────────────────────

@notifications_bp.post("/api/notifications/read-all")
def mark_all_read():
    user_id, _, err = _get_user()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        # Personals
        db.execute(text(
            "UPDATE notifications SET is_read = TRUE WHERE user_id = :uid AND is_read = FALSE"
        ), {"uid": user_id})

        # Globals no llegides
        unread_globals = db.execute(text("""
            SELECT n.id FROM notifications n
            WHERE n.user_id IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM notification_reads nr
                  WHERE nr.user_id = :uid AND nr.notification_id = n.id
              )
        """), {"uid": user_id}).fetchall()

        for row in unread_globals:
            db.execute(text("""
                INSERT INTO notification_reads (user_id, notification_id)
                VALUES (:uid, :nid) ON CONFLICT DO NOTHING
            """), {"uid": user_id, "nid": row.id})

        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── DELETE /api/notifications/<id> ───────────────────────────────────────────

@notifications_bp.delete("/api/notifications/<int:notif_id>")
def delete_notification(notif_id):
    user_id, _, err = _get_user()
    if err:
        return jsonify(err[0]), err[1]

    db = SessionLocal()
    try:
        notif = db.execute(text(
            "SELECT user_id FROM notifications WHERE id = :id"
        ), {"id": notif_id}).fetchone()

        if not notif:
            return jsonify({"error": "Notificació no trobada"}), 404

        if notif.user_id is None:
            # Global: marcar com llegida (no esborrem globals per a tots)
            db.execute(text("""
                INSERT INTO notification_reads (user_id, notification_id)
                VALUES (:uid, :nid) ON CONFLICT DO NOTHING
            """), {"uid": user_id, "nid": notif_id})
        elif notif.user_id == user_id:
            db.execute(text("DELETE FROM notifications WHERE id = :id"), {"id": notif_id})
        else:
            return jsonify({"error": "Accés denegat"}), 403

        db.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ── POST /api/admin/notifications ────────────────────────────────────────────

@notifications_bp.post("/api/admin/notifications")
def admin_create_notification():
    user_id, _, err = _get_user(require_admin=True)
    if err:
        return jsonify(err[0]), err[1]

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    message = (data.get("message") or "").strip()
    ntype = data.get("type", "info")
    target_user_id = data.get("user_id")  # None = global

    if not title or not message:
        return jsonify({"error": "title i message requerits"}), 400
    if ntype not in ("info", "warning", "alert"):
        return jsonify({"error": "type ha de ser info, warning o alert"}), 400

    db = SessionLocal()
    try:
        result = db.execute(text("""
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (:uid, :title, :msg, :type)
            RETURNING id
        """), {"uid": target_user_id, "title": title, "msg": message, "type": ntype})
        new_id = result.fetchone().id
        db.commit()
        return jsonify({"ok": True, "id": new_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
