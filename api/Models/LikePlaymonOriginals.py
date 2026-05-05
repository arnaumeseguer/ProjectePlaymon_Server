from sqlalchemy import Column, BigInteger, Integer, DateTime, UniqueConstraint, func, ForeignKey
from .Base import Base

class LikePlaymonOriginals(Base):
    __tablename__ = "like_playmon_originals"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id   = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_like_playmon_user_video"),
    )
