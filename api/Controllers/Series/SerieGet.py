from flask import jsonify, Blueprint, request
from api.Models.Base import SessionLocal
from api.Services.SerieService import SerieService

serie_get_bp = Blueprint("serie_get", __name__)

@serie_get_bp.get("/api/series")
def get_series():
    categoria = request.args.get("categoria")
    db = SessionLocal()
    try:
        series = SerieService.get_all(db, categoria)
        return jsonify([s.to_dict() for s in series])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@serie_get_bp.get("/api/series/<int:serie_id>")
def get_serie(serie_id):
    db = SessionLocal()
    try:
        serie = SerieService.get_by_id(db, serie_id)
        if not serie:
            return jsonify({"error": "Sèrie no trobada"}), 404
        return jsonify(serie.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
