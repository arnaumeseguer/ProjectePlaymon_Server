from flask import jsonify, Blueprint
from db import fetch_all
from api.Controllers.User.user_helpers import USER_SELECT, row_to_user

user_get_bp = Blueprint("user_get", __name__)

@user_get_bp.get("/api/users")
def get_users():
    rows = fetch_all(f"SELECT {USER_SELECT} FROM users ORDER BY id;")
    return jsonify([row_to_user(r) for r in rows])
