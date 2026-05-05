from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, UniqueConstraint, func, ForeignKey
from .Base import Base

class PlaymonHistorial(Base):
    __tablename__ = "playmon_historial"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id       = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id      = Column(Integer, nullable=False)
    title         = Column(Text)
    thumbnail_url = Column(Text)
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_playmon_historial_user_video"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "video_id":      self.video_id,
            "title":         self.title,
            "thumbnail_url": self.thumbnail_url,
            "updated_at":    self.updated_at.isoformat() if self.updated_at else None,
        }
