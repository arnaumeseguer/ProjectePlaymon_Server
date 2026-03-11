from flask import jsonify, Blueprint, request
from werkzeug.security import generate_password_hash
from db import fetch_one
from api.Controllers.User.user_helpers import USER_SELECT, row_to_user
import psycopg

user_update_bp = Blueprint("user_update", __name__)

def parse_bool(v, default=True):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "y", "si", "sí"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
    return default

@user_update_bp.put("/api/users/<int:user_id>")
def update_user(user_id):
    data = request.get_json(silent=True) or {}

    fields = []
    params = []

    if "username" in data:
        username = (data.get("username") or "").strip()
        if not username:
            return jsonify({"error": "'username' no pot ser buit"}), 400
        fields.append("username = %s")
        params.append(username)

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "'name' no pot ser buit"}), 400
        fields.append("name = %s")
        params.append(name)

    if "email" in data:
        email = (data.get("email") or "").strip()
        if not email:
            return jsonify({"error": "'email' no pot ser buit"}), 400
        fields.append("email = %s")
        params.append(email)

    if "role" in data:
        role = (data.get("role") or "").strip()
        if role not in ("admin", "support", "user"):
            return jsonify({"error": "role invàlid (admin/support/user)"}), 400
        fields.append("role = %s")
        params.append(role)

    if "is_active" in data:
        fields.append("is_active = %s")
        params.append(parse_bool(data.get("is_active"), True))

    if "password" in data:
        password = (data.get("password") or "").strip()
        if not password:
            return jsonify({"error": "'password' no pot ser buit"}), 400
        fields.append("password_hash = %s")
        params.append(generate_password_hash(password))

    if "pla_pagament" in data or "subscription_plan" in data:
        plan_raw = data.get("pla_pagament", data.get("subscription_plan"))
        plan = (plan_raw or "basic").strip().lower()
        if plan not in ("basic", "super", "master"):
            return jsonify({"error": "Pla de subscripció invàlid (basic/super/master)"}), 400
        fields.append("pla_pagament = %s")
        params.append(plan)

    if not fields:
        return jsonify({"error": "No hi ha camps per actualitzar"}), 400

    params.append(user_id)

    try:
        row = fetch_one(
            f"""
            UPDATE users
            SET {', '.join(fields)}
            WHERE id = %s
            RETURNING {USER_SELECT};
            """,
            tuple(params)
        )

        if not row:
            return jsonify({"error": "Usuari no trobat"}), 404

        return jsonify(row_to_user(row))

    except psycopg.errors.UniqueViolation:
        return jsonify({"error": "username o email ja existeix"}), 409
    except psycopg.Error as e:
        return jsonify({"error": "Error BD", "detail": str(e)}), 500
