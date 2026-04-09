from sqlalchemy import Column, Integer, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSON
from .Base import Base

class Serie(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True)
    tmdb_id = Column(Integer)
    title = Column(Text)
    description = Column(Text)
    poster_url = Column(Text)
    backdrop_url = Column(Text)
    video_url = Column(Text)
    is_public = Column(Boolean)
    categoria = Column(JSON)
    reparto = Column(JSON)
    direccio = Column(JSON)
    fecha_estreno = Column(DateTime)
    num_temporades = Column(Integer)
    num_episodis = Column(Integer)
    estat = Column(Text)
    temporades = Column(JSON)

    def to_dict(self):
        return {
            "id": self.id,
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "description": self.description,
            "poster_url": self.poster_url,
            "backdrop_url": self.backdrop_url,
            "video_url": self.video_url,
            "is_public": self.is_public,
            "categoria": self.categoria,
            "reparto": self.reparto,
            "direccio": self.direccio,
            "fecha_estreno": self.fecha_estreno.isoformat() if hasattr(self.fecha_estreno, 'isoformat') else self.fecha_estreno,
            "num_temporades": self.num_temporades,
            "num_episodis": self.num_episodis,
            "estat": self.estat,
            "temporades": self.temporades
        }
