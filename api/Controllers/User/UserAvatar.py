from flask import jsonify, Blueprint, request
import os
from vercel_blob import put
from db import fetch_one

user_avatar_bp = Blueprint("user_avatar", __name__)

BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "")
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "webp", "gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@user_avatar_bp.post("/api/users/<int:user_id>/avatar")
def upload_avatar(user_id):
    """
    Upload avatar image to Vercel Blob and save URL to user record.
    
    Expects multipart form with 'file' field.
    Returns: { "avatar_url": "https://..." }
    """
    
    # Check if user exists
    user_row = fetch_one("SELECT id FROM users WHERE id = %s", (user_id,))
    if not user_row:
        return jsonify({"error": "Usuari no trobat"}), 404
    
    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "Falta el camp 'file'"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Cap fitxer seleccionat"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Format de fitxer no permés (JPEG/PNG/WEBP/GIF)"}), 400
    
    # Check file size
    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": f"Fitxer massa gran (màxim {MAX_FILE_SIZE / 1024 / 1024}MB)"}), 400
    
    # Upload to Vercel Blob
    try:
        if not BLOB_READ_WRITE_TOKEN:
            return jsonify({"error": "Vercel Blob no configurat al servidor"}), 500
        
        # Generate unique filename with user ID
        file_ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else "jpg"
        blob_filename = f"avatars/user_{user_id}.{file_ext}"
        
        # Upload to Vercel Blob
        blob_response = put(
            pathname=blob_filename,
            body=file_bytes,
            options={
                "access": "public",
                "token": BLOB_READ_WRITE_TOKEN
            }
        )
        
        blob_url = blob_response.get("url", "")
        
        if not blob_url:
            return jsonify({"error": "No s'ha rebut URL de Vercel Blob"}), 500
        
        # Save blob URL to database
        try:
            fetch_one(
                "UPDATE users SET avatar = %s WHERE id = %s RETURNING id",
                (blob_url, user_id)
            )
        except Exception as e:
            return jsonify({"error": f"Error guardant a la BD: {str(e)}"}), 500
        
        return jsonify({
            "avatar_url": blob_url,
            "message": "Avatar actualitzat correctament"
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Error pujant fitxer: {str(e)}"}), 500
