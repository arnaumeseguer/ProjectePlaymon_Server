from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, UniqueConstraint, func, ForeignKey
from .Base import Base

class HistorialVisualitzacio(Base):
    __tablename__ = "historial_visualitzacions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(Text, nullable=False, default="movie")
    title = Column(Text)
    poster_path = Column(Text)
    backdrop_path = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_historial_user_tmdb_type"),
    )

    def to_dict(self):
        return {
            "id": self.tmdb_id,
            "tmdb_id": self.tmdb_id,
            "media_type": self.media_type,
            "title": self.title,
            "name": self.title,
            "poster_path": self.poster_path,
            "backdrop_path": self.backdrop_path,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
