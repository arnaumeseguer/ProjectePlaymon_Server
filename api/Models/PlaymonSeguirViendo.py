from sqlalchemy import Column, BigInteger, Integer, Float, Text, DateTime, UniqueConstraint, func, ForeignKey
from .Base import Base

class PlaymonSeguirViendo(Base):
    __tablename__ = "playmon_seguir_viendo"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id       = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id      = Column(Integer, nullable=False)
    title         = Column(Text)
    thumbnail_url = Column(Text)
    progress      = Column(Float, default=0)
    duration      = Column(Float, default=0)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_playmon_seguir_viendo_user_video"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "video_id":      self.video_id,
            "title":         self.title,
            "thumbnail_url": self.thumbnail_url,
            "progress":      self.progress or 0,
            "duration":      self.duration or 0,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }
