from flask import jsonify, Blueprint, request
import os
import re
from uuid import uuid4
from db import fetch_one, fetch_all

# Read and validate Cloudinary URL before importing cloudinary module.
# cloudinary package parses CLOUDINARY_URL on import and can crash app startup if invalid.
cloudinary_url = (os.getenv("CLOUDINARY_URL") or "").strip()
cloudinary_config_error = None

if cloudinary_url and not cloudinary_url.startswith("cloudinary://"):
    cloudinary_config_error = "Invalid CLOUDINARY_URL scheme. Expecting to start with 'cloudinary://'"
    os.environ.pop("CLOUDINARY_URL", None)
    cloudinary_url = ""

import cloudinary
import cloudinary.uploader

video_upload_bp = Blueprint("video_upload", __name__)

# Configure Cloudinary from URL
if cloudinary_url:
    try:
        cloudinary.config(cloudinary_url=cloudinary_url)
    except Exception as e:
        cloudinary_config_error = str(e)
        cloudinary_url = ""

ALLOWED_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "avi", "mkv", "flv", "wmv"}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB for videos (Cloudinary free is 25GB total)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def delete_cloudinary_video(public_id):
    """Delete a video from Cloudinary by public_id"""
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="video")
        return result.get("result") == "ok"
    except Exception:
        return False


@video_upload_bp.post("/api/videos/upload")
def upload_video():
    """
    Upload video to Cloudinary and save metadata to database.
    
    Expects multipart form with:
    - 'file': Video file (MP4/WebM/OGG/MOV/AVI, max 500MB)
    - 'title': Video title (optional)
    - 'description': Video description (optional)
    - 'is_public': Boolean for visibility (optional, default false)
    
    Returns: { "video_id": <id>, "video_url": "https://...", "message": "..." }
    """
    
    # Get user_id from JWT token or form
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        user_id = request.form.get("user_id")
    
    if not user_id:
        return jsonify({"error": "user_id required (header X-User-ID or form field)"}), 400
    
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user_id"}), 400
    
    # Check if user exists
    user_row = fetch_one("SELECT id, username FROM users WHERE id = %s", (user_id,))
    if not user_row:
        return jsonify({"error": "Usuari no trobat"}), 404
    
    username = user_row[1] or f"user{user_id}"
    
    # Validate file
    if "file" not in request.files:
        return jsonify({"error": "Falta el camp 'file'"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Cap fitxer seleccionat"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Format de vídeo no permés (MP4/WebM/OGG/MOV/AVI/MKV)"}), 400
    
    # Check file size
    file_bytes = file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({"error": f"Vídeo massa gran (màxim {MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"}), 400
    
    if file_size < 1024:  # At least 1KB
        return jsonify({"error": "Vídeo massa petit"}), 400
    
    # Get metadata from request
    title = (request.form.get("title") or "Sin título").strip()
    description = (request.form.get("description") or "").strip()
    is_public = request.form.get("is_public", "false").lower() in ("true", "1", "yes")
    
    # Upload to Cloudinary
    try:
        # Check if credentials are set
        if cloudinary_config_error:
            return jsonify({
                "error": "Cloudinary no configurat al servidor",
                "detail": cloudinary_config_error,
            }), 500

        if not cloudinary_url:
            return jsonify({"error": "Cloudinary no configurat al servidor"}), 500
        
        # Sanitize username for Cloudinary public_id
        safe_username = re.sub(r'[^a-zA-Z0-9_-]', '', username) or f"user{user_id}"
        
        # Generate unique folder and filename
        unique_id = uuid4().hex[:8]
        public_id = f"playmon/{safe_username}/{unique_id}"
        
        # Reset file pointer to beginning after reading
        file.seek(0)
        
        # Upload to Cloudinary (use upload_large for large files)
        upload_result = cloudinary.uploader.upload(
            file,
            resource_type="video",
            public_id=public_id,
            folder="playmon",
            use_filename=False,
            unique_filename=False,
            overwrite=False,
            timeout=120
        )
        
        video_url = upload_result.get("secure_url", "")
        cloudinary_public_id = upload_result.get("public_id", "")
        
        if not video_url:
            return jsonify({"error": "Error pujant a Cloudinary"}), 500
        
        # Save video record to database
        try:
            video_row = fetch_one(
                """
                INSERT INTO videos (user_id, title, description, video_url, file_size, is_public)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, title, description, video_url, file_size, is_public)
            )
            
            if not video_row:
                return jsonify({"error": "Error guardant vídeo a la BD"}), 500
            
            video_id = video_row[0]
            
        except Exception as e:
            return jsonify({"error": f"Error guardant a la BD: {str(e)}"}), 500
        
        return jsonify({
            "video_id": video_id,
            "video_url": video_url,
            "title": title,
            "file_size": file_size,
            "message": "Vídeo pujat correctament a Cloudinary"
        }), 201
    
    except Exception as e:
        return jsonify({"error": f"Error pujant vídeo: {str(e)}"}), 500


@video_upload_bp.get("/api/videos")
def get_videos():
    """
    Get all public videos or user's own videos.
    Query params:
    - user_id: Get videos from specific user
    - limit: Max results (default 20)
    - offset: Pagination offset (default 0)
    """
    try:
        user_id = request.args.get("user_id")
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))
        
        if user_id:
            # Get videos from specific user (public only)
            try:
                user_id = int(user_id)
            except ValueError:
                return jsonify({"error": "Invalid user_id"}), 400
            
            rows = fetch_all(
                """
                SELECT id, user_id, title, description, video_url, thumbnail_url, 
                       file_size, duration, is_public, created_at
                FROM videos
                WHERE user_id = %s AND is_public = true
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset)
            )
        else:
            # Get all public videos
            rows = fetch_all(
                """
                SELECT id, user_id, title, description, video_url, thumbnail_url, 
                       file_size, duration, is_public, created_at
                FROM videos
                WHERE is_public = true
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
        
        if not rows:
            return jsonify({"videos": []}), 200
        
        videos = []
        for r in rows:
            videos.append({
                "id": r[0],
                "user_id": r[1],
                "title": r[2],
                "description": r[3],
                "video_url": r[4],
                "thumbnail_url": r[5],
                "file_size": r[6],
                "duration": r[7],
                "is_public": r[8],
                "created_at": r[9].isoformat() if r[9] else None
            })
        
        return jsonify({"videos": videos}), 200
    
    except Exception as e:
        return jsonify({"error": f"Error recuperant vídeos: {str(e)}"}), 500


@video_upload_bp.get("/api/videos/<int:video_id>")
def get_video(video_id):
    """Get a specific video by ID"""
    try:
        row = fetch_one(
            """
            SELECT id, user_id, title, description, video_url, thumbnail_url, 
                   file_size, duration, is_public, created_at
            FROM videos
            WHERE id = %s
            """,
            (video_id,)
        )
        
        if not row:
            return jsonify({"error": "Vídeo no trobat"}), 404
        
        # Check permissions (TODO: verify user can access)
        
        video = {
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "description": row[3],
            "video_url": row[4],
            "thumbnail_url": row[5],
            "file_size": row[6],
            "duration": row[7],
            "is_public": row[8],
            "created_at": row[9].isoformat() if row[9] else None
        }
        
        return jsonify(video), 200
    
    except Exception as e:
        return jsonify({"error": f"Error recuperant vídeo: {str(e)}"}), 500


@video_upload_bp.delete("/api/videos/<int:video_id>")
def delete_video(video_id):
    """Delete a video (only owner can delete)"""
    try:
        # Get video to check permissions
        row = fetch_one(
            "SELECT user_id FROM videos WHERE id = %s",
            (video_id,)
        )
        
        if not row:
            return jsonify({"error": "Vídeo no trobat"}), 404
        
        # TODO: Verify user owns this video (check JWT)
        
        # Delete from database first
        fetch_one(
            "DELETE FROM videos WHERE id = %s",
            (video_id,)
        )
        
        # Note: Cloudinary files will eventually be cleaned up
        # For now we just remove the database record
        
        return jsonify({
            "message": "Vídeo eliminat correctament"
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Error eliminant vídeo: {str(e)}"}), 500
