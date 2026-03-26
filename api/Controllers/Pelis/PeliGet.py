from flask import jsonify, Blueprint
from api.Models.Base import SessionLocal
from api.Services.PeliService import PeliService
from sqlalchemy import cast, String

peli_get_bp = Blueprint("peli_get", __name__)

@peli_get_bp.get("/api/pelis")
def get_pelis():
    from flask import request
    categoria = request.args.get("categoria")
    db = SessionLocal()
    try:
        pelis = PeliService.get_all(db, categoria)
        return jsonify([p.to_dict() for p in pelis])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@peli_get_bp.get("/api/pelis/<int:peli_id>")
def get_peli(peli_id):
    db = SessionLocal()
    try:
        peli = PeliService.get_by_id(db, peli_id)
        if not peli:
            return jsonify({"error": "Pel·lícula no trobada"}), 404
        return jsonify(peli.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@peli_get_bp.get("/api/pelis/<int:peli_id>/relacionats")
def get_pelis_relacionats(peli_id):
    """Retorna fins a 12 pel·lícules del mateix gènere, excloent la peli actual."""
    db = SessionLocal()
    try:
        from api.Models.Peli import Peli
        # Obtenim la peli principal per saber els seus gèneres
        peli = db.query(Peli).filter(Peli.id == peli_id).first()
        if not peli:
            return jsonify([])

        # Extraiem els IDs de gènere de la peli actual
        cats = peli.categoria or []
        if isinstance(cats, str):
            import json
            try: cats = json.loads(cats)
            except: cats = []

        if not cats:
            # Si no hi ha gèneres, retornem les 12 més recents (sense la mateixa)
            pelis = db.query(Peli).filter(
                Peli.id != peli_id,
                Peli.is_public == True
            ).order_by(Peli.id.desc()).limit(12).all()
            return jsonify([p.to_dict() for p in pelis])

        # Agafem el primer gènere i cerquem coincidències
        first_genre = cats[0]
        search_term = str(first_genre.get("id", "")) if isinstance(first_genre, dict) else str(first_genre)

        pelis = db.query(Peli).filter(
            Peli.id != peli_id,
            Peli.is_public == True,
            cast(Peli.categoria, String).contains(search_term)
        ).order_by(Peli.id.desc()).limit(12).all()

        return jsonify([p.to_dict() for p in pelis])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@peli_get_bp.get("/api/pelis/search")
def search_local_pelis():
    from flask import request
    from sqlalchemy import or_
    query = request.args.get("query", "")
    db = SessionLocal()
    try:
        from api.Models.Peli import Peli
        import unicodedata
        from sqlalchemy import func
        if not query:
            return jsonify([])
            
        # Normalització i neteja d'accents bàsica per al costat del client
        nfkd = unicodedata.normalize('NFKD', query)
        query_unaccent = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
        
        # Filtre robust a SQL per intercanviar els accents a les taules virtualment abans de cridar l'ilike
        accents = 'áéíóúàèìòùäëïöüâêîôûñÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÂÊÎÔÛÑ'
        base    = 'aeiouaeiouaeiouaeiounAEIOUAEIOUAEIOUAEIOUN'
        
        pelis = db.query(Peli).filter(
            Peli.is_public == True,
            func.translate(Peli.title, accents, base).ilike(f"{query_unaccent}%")
        ).order_by(Peli.title.asc()).limit(20).all()
        return jsonify([p.to_dict() for p in pelis])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
