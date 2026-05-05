from sqlalchemy import Column, BigInteger, Integer, DateTime, func
from .Base import Base

class VisitesOriginalsGenerals(Base):
    __tablename__ = "visites_originals_generals"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    video_id    = Column(Integer, nullable=False, unique=True)
    view_count  = Column(BigInteger, nullable=False, default=0)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
