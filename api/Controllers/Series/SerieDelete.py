from flask import jsonify, Blueprint
from api.Models.Base import SessionLocal
from api.Services.SerieService import SerieService

serie_delete_bp = Blueprint("serie_delete", __name__)

@serie_delete_bp.delete("/api/series/<int:serie_id>")
def delete_serie(serie_id):
    db = SessionLocal()
    try:
        success = SerieService.delete(db, serie_id)
        if success:
            return jsonify({"deleted": serie_id}), 200
        return jsonify({"error": "Sèrie no trobada"}), 404
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Error eliminant la sèrie", "detail": str(e)}), 500
    finally:
        db.close()
