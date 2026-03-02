from flask import Blueprint, jsonify
from db import count_rows

table_count_bp = Blueprint("table_count", __name__)


@table_count_bp.get("/api/stats/<string:table_name>/count")
def get_table_count(table_name):
    try:
        total = count_rows(table_name)
        if total is None :
            return jsonify({"error": "Taula no trobada"}), 404

        return jsonify({
            "table": table_name,
            "count": total,
        }), 200
    except Exception as e:
        return jsonify({"error": "Error obtenint recompte", "detail": str(e)}), 500