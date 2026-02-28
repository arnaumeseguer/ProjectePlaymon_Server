from flask import jsonify, Blueprint, request
from werkzeug.security import check_password_hash
import jwt
import os
from datetime import datetime, timedelta
from db import fetch_one
from api.Controllers.User.user_helpers import USER_SELECT, row_to_user

user_login_bp = Blueprint("user_login", __name__)

# JWT Secret - use environment variable or fallback (IMPORTANT: set JWT_SECRET in .env for production)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

@user_login_bp.post("/api/login")
def login():
    """
    Login endpoint that verifies credentials and returns JWT token.
    Expected JSON: {
        "username": "user@example.com or username",
        "password": "user_password"
    }
    Returns:
    {
        "token": "jwt_token_here",
        "user": {...user_data...},
        "expires_in": 86400
    }
    """
    data = request.get_json(silent=True) or {}
    
    username_or_email = (data.get("username") or data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    
    if not username_or_email:
        return jsonify({"error": "Falta 'username' o 'email'"}), 400
    if not password:
        return jsonify({"error": "Falta 'password'"}), 400
    
    try:
        # Search user by username or email
        user_row = fetch_one(
            f"""
            SELECT {USER_SELECT}, password_hash
            FROM users
            WHERE username = %s OR email = %s
            """,
            (username_or_email, username_or_email)
        )
        
        if not user_row:
            return jsonify({"error": "Usuari no trobat"}), 401
        
        # Verify password
        stored_password_hash = user_row[8]  # password_hash is the 9th element (index 8)
        if not check_password_hash(stored_password_hash, password):
            return jsonify({"error": "Contrasenya incorrecta"}), 401
        
        # Check if user is active
        user_data = row_to_user(user_row[:8])
        is_active = user_row[5]
        if not is_active:
            return jsonify({"error": "L'usuari no està actiu"}), 403
        
        # Generate JWT token
        payload = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "role": user_data["role"],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return jsonify({
            "token": token,
            "user": user_data,
            "expires_in": JWT_EXPIRATION_HOURS * 3600  # seconds
        }), 200
    
    except Exception as e:
        return jsonify({"error": "Error en login", "detail": str(e)}), 500
