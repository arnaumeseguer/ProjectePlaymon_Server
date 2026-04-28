from sqlalchemy import Column, BigInteger, Integer, Text, Float, DateTime, UniqueConstraint, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from .Base import Base

class Watchlist(Base):
    __tablename__ = "veure_mes_tard"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tmdb_id = Column(Integer, nullable=False)
    media_type = Column(Text, nullable=False, default="movie")
    title = Column(Text)
    poster_path = Column(Text)
    backdrop_path = Column(Text)
    overview = Column(Text)
    release_date = Column(Text)
    first_air_date = Column(Text)
    vote_average = Column(Float)
    genres = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "tmdb_id", "media_type", name="uq_watchlist_user_tmdb_type"),
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
            "overview": self.overview,
            "release_date": self.release_date,
            "first_air_date": self.first_air_date,
            "vote_average": self.vote_average,
            "genres": self.genres or [],
        }
