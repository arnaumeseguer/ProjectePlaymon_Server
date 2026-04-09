from flask import jsonify, Blueprint, request
from api.Models.Base import SessionLocal
from api.Services.SerieService import SerieService
import sqlalchemy.exc

serie_create_bp = Blueprint("serie_create", __name__)

@serie_create_bp.post("/api/series")
def create_serie():
    data = request.get_json(silent=True) or {}
    
    serie_id = data.get("id")
    title = data.get("title")
    
    if serie_id is None:
        return jsonify({"error": "Falta 'id'"}), 400
    if not title:
        return jsonify({"error": "Falta 'title'"}), 400

    valid_keys = [
        "id", "tmdb_id", "title", "description", "poster_url", 
        "backdrop_url", "video_url", "is_public", "categoria", 
        "reparto", "direccio", "fecha_estreno", "num_temporades", 
        "num_episodis", "estat", "temporades"
    ]
    serie_data = {k: data[k] for k in valid_keys if k in data}

    db = SessionLocal()
    try:
        serie = SerieService.create(db, serie_data)
        return jsonify(serie.to_dict()), 201
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        return jsonify({"error": f"L'ID de la sèrie {serie_id} ja existeix"}), 409
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error creant la sèrie", "detail": str(e)}), 500
    finally:
        db.close()
