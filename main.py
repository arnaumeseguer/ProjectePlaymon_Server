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
from api.Controllers.Video.VideoUpload import video_upload_bp
from api.Controllers.Global.TableCount import table_count_bp

from api.Controllers.Pelis.PeliGet import peli_get_bp
from api.Controllers.Pelis.PeliCreate import peli_create_bp
from api.Controllers.Pelis.PeliUpdate import peli_update_bp
from api.Controllers.Pelis.PeliDelete import peli_delete_bp

from api.Controllers.Series.SerieGet import serie_get_bp
from api.Controllers.Series.SerieCreate import serie_create_bp
from api.Controllers.Series.SerieUpdate import serie_update_bp
from api.Controllers.Series.SerieDelete import serie_delete_bp



from sqlalchemy import text
from api.Models.Base import engine

app = Flask(__name__)
CORS(app)

@app.get("/api/_debug/migrate")
def migrate_db():
    # Attempt to align 'pelicules' table with the new user schema
    sql = """
    CREATE SCHEMA IF NOT EXISTS "neon_auth";
    
    ALTER TABLE pelicules RENAME COLUMN IF EXISTS backdrop_path TO backdrop_url;
    ALTER TABLE pelicules RENAME COLUMN IF EXISTS genres TO categoria;
    ALTER TABLE pelicules RENAME COLUMN IF EXISTS cast_list TO reparto;
    ALTER TABLE pelicules RENAME COLUMN IF EXISTS crew_list TO direccio;
    
    ALTER TABLE pelicules ADD COLUMN IF NOT EXISTS user_id INTEGER;
    ALTER TABLE pelicules ADD COLUMN IF NOT EXISTS file_size INTEGER;
    ALTER TABLE pelicules ADD COLUMN IF NOT EXISTS is_public BOOLEAN;
    
    -- Sync 'videos' table too
    ALTER TABLE videos ADD COLUMN IF NOT EXISTS categoria TEXT;
    ALTER TABLE videos ADD COLUMN IF NOT EXISTS reparto TEXT;
    ALTER TABLE videos ADD COLUMN IF NOT EXISTS direccio TEXT;
    ALTER TABLE videos ADD COLUMN IF NOT EXISTS calificacio INTEGER;
    ALTER TABLE videos ADD COLUMN IF NOT EXISTS fecha_estreno DATE;
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        return jsonify({"ok": True, "message": "Migration to new schema successful"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

app.register_blueprint(user_get_bp)
app.register_blueprint(user_create_bp)
app.register_blueprint(user_update_bp)
app.register_blueprint(user_delete_bp)
app.register_blueprint(user_login_bp)
app.register_blueprint(user_avatar_bp)
app.register_blueprint(video_upload_bp)
app.register_blueprint(table_count_bp)

app.register_blueprint(peli_get_bp)
app.register_blueprint(peli_create_bp)
app.register_blueprint(peli_update_bp)
app.register_blueprint(peli_delete_bp)

app.register_blueprint(serie_get_bp)
app.register_blueprint(serie_create_bp)
app.register_blueprint(serie_update_bp)
app.register_blueprint(serie_delete_bp)


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
