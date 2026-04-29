from sqlalchemy import Column, BigInteger, Integer, Text, DateTime, UniqueConstraint, func, ForeignKey
from .Base import Base

class LlistaOriginals(Base):
    __tablename__ = "llista_playmon_originals"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id     = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id    = Column(Integer, nullable=False)
    title       = Column(Text)
    thumbnail_url = Column(Text)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_llista_originals_user_video"),
    )

    def to_dict(self):
        return {
            "id":            self.id,
            "video_id":      self.video_id,
            "title":         self.title,
            "thumbnail_url": self.thumbnail_url,
            "created_at":    self.created_at.isoformat() if self.created_at else None,
        }
