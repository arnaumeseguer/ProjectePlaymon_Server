from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
import psycopg
import os

load_dotenv()

from db import fetch_all, fetch_one

app = Flask(__name__)
CORS(app)

USER_SELECT = """
    id, username, name, email, role, is_active, created_at, updated_at
"""

@app.get("/api/_debug/db")
def debug_db():
    dsn = os.getenv("DATABASE_URL", "")
    if not dsn:
        return jsonify({"ok": False, "error": "DATABASE_URL no definida"}), 500

    # no exposem password
    safe = dsn
    if "://" in safe and "@" in safe:
        prefix, rest = safe.split("://", 1)
        creds, tail = rest.split("@", 1)
        user = creds.split(":", 1)[0]
        safe = f"{prefix}://{user}:***@{tail}"

    return jsonify({
        "ok": True,
        "dsn_masked": safe
    })


def row_to_user(r):
    return {
        "id": r[0],
        "username": r[1],
        "name": r[2],
        "email": r[3],
        "role": r[4],
        "is_active": r[5],
        "created_at": r[6].isoformat() if r[6] else None,
        "updated_at": r[7].isoformat() if r[7] else None,
    }

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

@app.get("/")
def root():
    return "API OK (Postgres en marxa)"

@app.get("/api/users")
def get_users():
    rows = fetch_all(f"SELECT {USER_SELECT} FROM users ORDER BY id;")
    return jsonify([row_to_user(r) for r in rows])

@app.get("/api/users/<int:user_id>")
def get_user(user_id):
    row = fetch_one(
        f"SELECT {USER_SELECT} FROM users WHERE id = %s;",
        (user_id,)
    )
    if not row:
        return jsonify({"error": "Usuari no trobat"}), 404
    return jsonify(row_to_user(row))

@app.post("/api/users")
def create_user():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    role = (data.get("role") or "user").strip()
    is_active = parse_bool(data.get("is_active"), True)

    # Per proves: acceptem "password" i la guardem hashejada
    password = (data.get("password") or "password").strip()
    password_hash = generate_password_hash(password)

    if not username:
        return jsonify({"error": "Falta 'username'"}), 400
    if not name:
        return jsonify({"error": "Falta 'name'"}), 400
    if not email:
        return jsonify({"error": "Falta 'email'"}), 400
    if role not in ("admin", "support", "user"):
        return jsonify({"error": "role invàlid (admin/support/user)"}), 400

    try:
        row = fetch_one(
            f"""
            INSERT INTO users (username, name, email, role, is_active, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING {USER_SELECT};
            """,
            (username, name, email, role, is_active, password_hash)
        )
        return jsonify(row_to_user(row)), 201

    except psycopg.errors.UniqueViolation:
        return jsonify({"error": "username o email ja existeix"}), 409
    except psycopg.Error as e:
        return jsonify({"error": "Error BD", "detail": str(e)}), 500

@app.put("/api/users/<int:user_id>")
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

    if not fields:
        return jsonify({"error": "No hi ha camps per actualitzar"}), 400

    params.append(user_id)

    try:
        row = fetch_one(
            f"""
            UPDATE users
            SET {", ".join(fields)}
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

@app.delete("/api/users/<int:user_id>")
def delete_user(user_id):
    row = fetch_one(
        "DELETE FROM users WHERE id = %s RETURNING id;",
        (user_id,)
    )
    if not row:
        return jsonify({"error": "Usuari no trobat"}), 404
    return jsonify({"deleted": row[0]})

if __name__ == "__main__":
    app.run(debug=True)
