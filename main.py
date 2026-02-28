from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

from api.Controllers.User.UserGet import user_get_bp
from api.Controllers.User.UserCreate import user_create_bp
from api.Controllers.User.UserUpdate import user_update_bp
from api.Controllers.User.UserDelete import user_delete_bp
from api.Controllers.User.UserLogin import user_login_bp
from api.Controllers.User.UserAvatar import user_avatar_bp


app = Flask(__name__)
CORS(app)

app.register_blueprint(user_get_bp)
app.register_blueprint(user_create_bp)
app.register_blueprint(user_update_bp)
app.register_blueprint(user_delete_bp)
app.register_blueprint(user_login_bp)
app.register_blueprint(user_avatar_bp)


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


if __name__ == "__main__":
    app.run(debug=True)
