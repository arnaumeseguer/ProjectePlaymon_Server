from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from api.Models.Serie import Serie
from typing import List, Optional

class SerieService:
    @staticmethod
    def get_all(db: Session, categoria: str = None) -> List[Serie]:
        query = db.query(Serie)
        
        if categoria:
            # We filter for the presence of the category ID/name in the JSON column.
            query = query.filter(cast(Serie.categoria, String).contains(categoria))
            
        return query.order_by(Serie.id.desc()).all()

    @staticmethod
    def get_by_id(db: Session, serie_id: int) -> Optional[Serie]:
        return db.query(Serie).filter(Serie.id == serie_id).first()

    @staticmethod
    def create(db: Session, data: dict) -> Serie:
        serie = Serie(**data)
        db.add(serie)
        db.commit()
        db.refresh(serie)
        return serie

    @staticmethod
    def update(db: Session, serie_id: int, data: dict) -> Optional[Serie]:
        serie = db.query(Serie).filter(Serie.id == serie_id).first()
        if not serie:
            return None
        
        for key, value in data.items():
            if hasattr(serie, key):
                setattr(serie, key, value)
        
        db.commit()
        db.refresh(serie)
        return serie

    @staticmethod
    def delete(db: Session, serie_id: int) -> bool:
        serie = db.query(Serie).filter(Serie.id == serie_id).first()
        if not serie:
            return False
        
        db.delete(serie)
        db.commit()
        return True
