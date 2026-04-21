from flask import jsonify, Blueprint, request
import os
import re
import requests as http_requests
from uuid import uuid4
from api.Models.Base import SessionLocal
from api.Models.User import User
from api.Services.UserService import UserService
from api.Services.VideoService import VideoService

video_upload_bp = Blueprint("video_upload", __name__)

BLOB_READ_WRITE_TOKEN = os.getenv("BLOB_READ_WRITE_TOKEN", "")
BLOB_BASE_URL = "https://blob.vercel-storage.com"

ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "avi", "mkv", "flv", "wmv"}
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024   # 500 MB
MAX_THUMB_SIZE  = 10  * 1024 * 1024  # 10 MB


def allowed_video(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def upload_to_blob(file_bytes, blob_path):
    """Puja bytes a Vercel Blob i retorna la URL pública, o None si falla."""
    if not BLOB_READ_WRITE_TOKEN:
        return None, "BLOB_READ_WRITE_TOKEN no configurat"

    upload_url = f"{BLOB_BASE_URL}/{blob_path}"
    headers = {
        "Authorization": f"Bearer {BLOB_READ_WRITE_TOKEN}",
        "x-add-random-suffix": "0",
        "x-upsert": "true",
    }
    try:
        resp = http_requests.put(upload_url, headers=headers, data=file_bytes,
                                 params={"filename": blob_path}, timeout=120)
        if resp.status_code not in (200, 201):
            return None, f"Vercel Blob HTTP {resp.status_code}"
        url = resp.json().get("url", "")
        return (url or None), (None if url else "URL buida a la resposta de Blob")
    except Exception as e:
        return None, str(e)


def _video_with_user(db, video):
    user = db.query(User).filter(User.id == video.user_id).first()
    d = video.to_dict()
    d["username"] = user.username if user and user.username else (user.name if user else "Usuari")
    d["user_avatar"] = user.avatar if user else None
    return d


@video_upload_bp.post("/api/videos/upload")
def upload_video():
    user_id = request.headers.get("X-User-ID") or request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user_id"}), 400

    db = SessionLocal()
    try:
        user = UserService.get_by_id(db, user_id)
        if not user:
            return jsonify({"error": "Usuari no trobat"}), 404

        if "file" not in request.files:
            return jsonify({"error": "Falta el camp 'file'"}), 400
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Cap fitxer seleccionat"}), 400
        if not allowed_video(file.filename):
            return jsonify({"error": "Format de vídeo no permès"}), 400

        file_bytes = file.read()
        if len(file_bytes) > MAX_VIDEO_SIZE:
            return jsonify({"error": "Vídeo massa gran (màxim 500 MB)"}), 400

        title       = (request.form.get("title") or "Sense títol").strip()
        description = (request.form.get("description") or "").strip()
        categoria   = (request.form.get("categoria") or "").strip() or None
        is_public   = request.form.get("is_public", "true").lower() in ("true", "1", "yes")

        safe_user = re.sub(r'[^a-zA-Z0-9_-]', '', user.username or f"user{user_id}")
        uid = uuid4().hex[:10]
        ext = file.filename.rsplit(".", 1)[1].lower()
        video_blob_path = f"videos/{safe_user}/{uid}.{ext}"

        video_url, err = upload_to_blob(file_bytes, video_blob_path)
        if not video_url:
            return jsonify({"error": f"Error pujant vídeo: {err}"}), 500

        # Miniatura: accepta URL ja pujada pel frontend o fitxer directe
        thumbnail_url = (request.form.get("thumbnail_url") or "").strip() or None
        if not thumbnail_url:
            thumb_file = request.files.get("thumbnail")
            if thumb_file and thumb_file.filename and allowed_image(thumb_file.filename):
                thumb_bytes = thumb_file.read()
                if len(thumb_bytes) <= MAX_THUMB_SIZE:
                    t_ext = thumb_file.filename.rsplit(".", 1)[1].lower()
                    thumb_path = f"thumbnails/{safe_user}/{uid}_thumb.{t_ext}"
                    thumbnail_url, _ = upload_to_blob(thumb_bytes, thumb_path)

        video = VideoService.create(db, {
            "user_id":       user_id,
            "title":         title,
            "description":   description,
            "video_url":     video_url,
            "thumbnail_url": thumbnail_url,
            "file_size":     len(file_bytes),
            "is_public":     is_public,
            "categoria":     categoria,
        })

        return jsonify(_video_with_user(db, video)), 201

    except Exception as e:
        return jsonify({"error": f"Error inesperat: {str(e)}"}), 500
    finally:
        db.close()


@video_upload_bp.get("/api/videos")
def get_videos():
    user_id = request.args.get("user_id")
    limit   = min(int(request.args.get("limit", 50)), 100)
    offset  = int(request.args.get("offset", 0))
    db = SessionLocal()
    try:
        videos = (VideoService.get_user_videos(db, int(user_id), limit, offset)
                  if user_id else VideoService.get_public_videos(db, limit, offset))
        return jsonify({"videos": [_video_with_user(db, v) for v in videos]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@video_upload_bp.get("/api/videos/<int:video_id>")
def get_video(video_id):
    db = SessionLocal()
    try:
        video = VideoService.get_by_id(db, video_id)
        if not video:
            return jsonify({"error": "Vídeo no trobat"}), 404
        return jsonify(_video_with_user(db, video)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@video_upload_bp.post("/api/videos/<int:video_id>/update")
def update_video(video_id):
    db = SessionLocal()
    try:
        video = VideoService.get_by_id(db, video_id)
        if not video:
            return jsonify({"error": "Vídeo no trobat"}), 404
            
        user = db.query(User).filter(User.id == video.user_id).first()

        # Handle FormData 
        title = request.form.get("title")
        if title:
            video.title = title.strip() or video.title
            
        description = request.form.get("description")
        if description is not None:  # Permet descripcions buides
            video.description = description.strip()
            
        categoria = request.form.get("categoria")
        if categoria is not None:
            video.categoria = categoria.strip() or None

        thumbnail_url = (request.form.get("thumbnail_url") or "").strip() or None
        if not thumbnail_url:
            thumb_file = request.files.get("thumbnail")
            if thumb_file and thumb_file.filename and allowed_image(thumb_file.filename):
                thumb_bytes = thumb_file.read()
                if len(thumb_bytes) <= MAX_THUMB_SIZE:
                    safe_user = re.sub(r'[^a-zA-Z0-9_-]', '', user.username if user and user.username else f"user{video.user_id}")
                    t_ext = thumb_file.filename.rsplit(".", 1)[1].lower()
                    uid = uuid4().hex[:10]
                    thumb_path = f"thumbnails/{safe_user}/{uid}_thumb.{t_ext}"
                    uploaded_url, _ = upload_to_blob(thumb_bytes, thumb_path)
                    if uploaded_url:
                        video.thumbnail_url = uploaded_url

        # També supporte JSON legacy en cas de que algu truqui directament
        if request.is_json:
            data = request.get_json() or {}
            if "title" in data:
                video.title = (data["title"] or "").strip() or video.title
            if "description" in data:
                video.description = (data["description"] or "").strip()
            if "categoria" in data:
                video.categoria = (data["categoria"] or "").strip() or None
            if "thumbnail_url" in data:
                video.thumbnail_url = data["thumbnail_url"]

        db.commit()
        db.refresh(video)
        return jsonify(_video_with_user(db, video)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@video_upload_bp.delete("/api/videos/<int:video_id>")
def delete_video(video_id):
    db = SessionLocal()
    try:
        success = VideoService.delete(db, video_id)
        if success:
            return jsonify({"message": "Vídeo eliminat correctament"}), 200
        return jsonify({"error": "Vídeo no trobat"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
