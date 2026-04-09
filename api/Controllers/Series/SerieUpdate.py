from flask import jsonify, Blueprint, request
from api.Models.Base import SessionLocal
from api.Services.SerieService import SerieService
from datetime import datetime

serie_update_bp = Blueprint("serie_update", __name__)

@serie_update_bp.put("/api/series/<int:serie_id>")
def update_serie(serie_id):
    data = request.get_json(silent=True) or {}
    
    if not data:
        return jsonify({"error": "No s'han enviat dades per actualitzar"}), 400

    valid_keys = [
        "tmdb_id", "title", "description", "poster_url", 
        "backdrop_url", "video_url", "is_public", "categoria", 
        "reparto", "direccio", "fecha_estreno", "num_temporades", 
        "num_episodis", "estat", "temporades"
    ]
    serie_data = {k: data[k] for k in valid_keys if k in data}

    if "fecha_estreno" in serie_data and isinstance(serie_data["fecha_estreno"], str):
        try:
            serie_data["fecha_estreno"] = datetime.fromisoformat(serie_data["fecha_estreno"])
        except ValueError:
            pass

    if not serie_data:
        return jsonify({"message": "Cap camp vàlid per actualitzar"}), 200

    db = SessionLocal()
    try:
        updated_serie = SerieService.update(db, serie_id, serie_data)
        if not updated_serie:
            return jsonify({"error": "Sèrie no trobada"}), 404
        return jsonify(updated_serie.to_dict())
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error actualitzant la sèrie", "detail": str(e)}), 500
    finally:
        db.close()
