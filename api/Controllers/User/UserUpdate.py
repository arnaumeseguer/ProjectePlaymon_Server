from flask import jsonify, Blueprint, request
from werkzeug.security import generate_password_hash
from datetime import datetime, timezone, timedelta
from api.Models.Base import SessionLocal
from api.Services.UserService import UserService
from sqlalchemy import text
import sqlalchemy.exc

user_update_bp = Blueprint("user_update", __name__)

PAID_PLANS = ('super', 'ultra')


@user_update_bp.put("/api/users/<int:user_id>")
def update_user(user_id):
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"message": "Cap camp per actualitzar"}), 200

    valid_keys = ["username", "name", "email", "role", "avatar", "pla_pagament", "is_active"]
    update_data = {k: data[k] for k in valid_keys if k in data}

    if "password" in data:
        update_data["password_hash"] = generate_password_hash(data["password"].strip())

    if not update_data:
        return jsonify({"message": "Cap camp vàlid per actualitzar"}), 200

    db = SessionLocal()
    try:
        # Obtenir pla actual per comparar
        current = db.execute(text(
            "SELECT pla_pagament FROM users WHERE id = :uid"
        ), {"uid": user_id}).fetchone()
        old_plan = (current.pla_pagament or '') if current else ''
        new_plan = update_data.get('pla_pagament', old_plan)

        # Gestionar dates de subscripció i notificació quan canvia el pla
        if 'pla_pagament' in update_data and new_plan != old_plan:
            if new_plan in PAID_PLANS:
                fi = datetime.now(timezone.utc) + timedelta(days=30)
                update_data['subscripcio_fi'] = fi
                # Crear notificació de renovació
                pla_nom = 'Super' if new_plan == 'super' else 'Ultra'
                db.execute(text("""
                    INSERT INTO notifications (user_id, title, message, type, auto_type)
                    VALUES (:uid, :title, :msg, 'info', 'renewed')
                """), {
                    "uid": user_id,
                    "title": f"Subscripció {pla_nom} activada ✓",
                    "msg": f"Benvingut/da al Pla {pla_nom}! La teva subscripció és vàlida fins al {fi.strftime('%d/%m/%Y')}.",
                })
                # Eliminar avisos de caducitat antics (ja no rellevants)
                db.execute(text("""
                    DELETE FROM notifications
                    WHERE user_id = :uid AND auto_type IN ('expiry_7d','expiry_3d','expiry_1d','expired')
                """), {"uid": user_id})
            elif new_plan == 'basic':
                update_data['subscripcio_fi'] = None

        user = UserService.update(db, user_id, update_data)
        if not user:
            return jsonify({"error": "Usuari no trobat"}), 404

        db.commit()
        return jsonify(user.to_dict()), 200

    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        return jsonify({"error": "username o email ja existeix"}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error BD", "detail": str(e)}), 500
    finally:
        db.close()
