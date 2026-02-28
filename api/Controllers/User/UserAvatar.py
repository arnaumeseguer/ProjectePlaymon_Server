from flask import jsonify, Blueprint, request
import os
import requests
from uuid import uuid4
from urllib.parse import urlparse
from db import fetch_one

user_avatar_bp = Blueprint("user_avatar", __name__)

BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "")
ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png", "webp", "gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def delete_blob_by_url(blob_url):
    if not blob_url or not BLOB_READ_WRITE_TOKEN:
        return False

    try:
        parsed = urlparse(blob_url)
        blob_path = parsed.path.lstrip("/")
        if not blob_path:
            return False

        delete_url = f"https://blob.vercel-storage.com/{blob_path}"
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}"
        }

        response = requests.delete(delete_url, headers=headers, timeout=20)
        return response.status_code in [200, 202, 204, 404]
    except Exception:
        return False


@user_avatar_bp.post("/api/users/<int:user_id>/avatar")
def upload_avatar(user_id):
    """
    Upload avatar image to Vercel Blob and save URL to user record.
    
    Expects multipart form with 'file' field.
    Returns: { "avatar_url": "https://..." }
    """
    
    # Check if user exists
    user_row = fetch_one("SELECT id, avatar FROM users WHERE id = %s", (user_id,))
    if not user_row:
        return jsonify({"error": "Usuari no trobat"}), 404

    old_avatar_url = user_row[1]
    
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
    
    # Upload to Vercel Blob via REST API
    try:
        if not BLOB_READ_WRITE_TOKEN:
            return jsonify({"error": "Vercel Blob no configurat al servidor"}), 500
        
        # Generate unique filename per upload to avoid cache/overwrite issues
        original_filename = file.filename or ""
        file_ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "jpg"
        blob_filename = f"avatars/user_{user_id}_{uuid4().hex}.{file_ext}"
        
        # Upload using Vercel Blob REST API
        upload_url = f"https://blob.vercel-storage.com/{blob_filename}"
        headers = {
            "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
            "x-add-random-suffix": "0",
            "x-upsert": "true"
        }
        
        response = requests.put(
            upload_url,
            headers=headers,
            data=file_bytes,
            params={"filename": blob_filename},
            timeout=30
        )
        
        if response.status_code not in [200, 201]:
            return jsonify({"error": f"Error pujant a Vercel Blob: HTTP {response.status_code}"}), 500
        
        # Parse response to get public URL
        try:
            response_data = response.json()
            blob_url = response_data.get("url", "")
        except:
            blob_url = ""
        
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

        if old_avatar_url and old_avatar_url != blob_url:
            delete_blob_by_url(old_avatar_url)
        
        return jsonify({
            "avatar_url": blob_url,
            "message": "Avatar actualitzat correctament"
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Error pujant fitxer: {str(e)}"}), 500


@user_avatar_bp.delete("/api/users/<int:user_id>/avatar")
def delete_avatar(user_id):
    """
    Remove user avatar URL from DB and try deleting blob from Vercel Blob.
    Returns: { "message": "...", "blob_deleted": true/false }
    """
    try:
        user_row = fetch_one("SELECT id, avatar FROM users WHERE id = %s", (user_id,))
        if not user_row:
            return jsonify({"error": "Usuari no trobat"}), 404

        current_avatar_url = user_row[1]
        blob_deleted = False

        if current_avatar_url:
            blob_deleted = delete_blob_by_url(current_avatar_url)

        fetch_one(
            "UPDATE users SET avatar = NULL WHERE id = %s RETURNING id",
            (user_id,)
        )

        return jsonify({
            "message": "Avatar eliminat correctament",
            "blob_deleted": blob_deleted
        }), 200
    except Exception as e:
        return jsonify({"error": f"Error eliminant avatar: {str(e)}"}), 500
