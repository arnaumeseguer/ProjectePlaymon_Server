from sqlalchemy import Column, BigInteger, Text, Boolean, DateTime, func
from .Base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    role = Column(Text, default='user', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    password_hash = Column(Text, default='password', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    avatar = Column(Text)
    pla_pagament = Column(Text)
    subscripcio_fi = Column(DateTime(timezone=True))

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') else self.created_at,
            "updated_at": self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') else self.updated_at,
            "avatar": self.avatar,
            "pla_pagament": self.pla_pagament,
            "subscripcio_fi": self.subscripcio_fi.isoformat() if self.subscripcio_fi else None,
        }
