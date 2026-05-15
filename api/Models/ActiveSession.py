from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey, func
from .Base import Base


class ActiveSession(Base):
    __tablename__ = "active_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(Text)
    user_agent = Column(Text)
    revoked_at = Column(DateTime(timezone=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "jti": self.jti,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.revoked_at is None,
        }
