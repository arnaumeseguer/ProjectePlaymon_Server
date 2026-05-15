from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, ForeignKey, func
from .Base import Base


class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(Text)
    user_agent = Column(Text)
    success = Column(Boolean, default=True, nullable=False)
    country = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "country": self.country,
        }
