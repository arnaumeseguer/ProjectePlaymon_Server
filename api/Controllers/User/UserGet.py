from flask import jsonify, Blueprint, request
import jwt
import os
from db import fetch_all, fetch_one
from api.Controllers.User.user_helpers import USER_SELECT, row_to_user

user_get_bp = Blueprint("user_get", __name__)

# JWT Secret - must match the one in UserLogin.py
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

@user_get_bp.get("/api/users")
def get_users():
    rows = fetch_all(f"SELECT {USER_SELECT} FROM users ORDER BY id;")
    return jsonify([row_to_user(r) for r in rows])

@user_get_bp.get("/api/users/<int:user_id>")
def get_user(user_id):
    row = fetch_one(
        f"SELECT {USER_SELECT} FROM users WHERE id = %s;",
        (user_id,)
    )
    if not row:
        return jsonify({"error": "Usuari no trobat"}), 404
    return jsonify(row_to_user(row))

@user_get_bp.get("/api/users/me")
def get_current_user():
    """
    Get current user data using JWT token from Authorization header.
    Header format: Authorization: Bearer <token>
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token no proporcionat"}), 401
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Verify and decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("id")
        
        if not user_id:
            return jsonify({"error": "Token inválid"}), 401
        
        # Fetch user from database
        user_row = fetch_one(
            f"SELECT {USER_SELECT} FROM users WHERE id = %s;",
            (user_id,)
        )
        
        if not user_row:
            return jsonify({"error": "Usuari no trobat"}), 404
        
        return jsonify(row_to_user(user_row)), 200
    
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expirat"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token inválid"}), 401
    except Exception as e:
        return jsonify({"error": "Error obtenint usuari actual", "detail": str(e)}), 500
