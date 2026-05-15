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

    # Camps de seguretat (migració 003)
    telefon = Column(Text)
    idioma = Column(Text)
    password_changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(Text)
    login_alerts_enabled = Column(Boolean, default=True, nullable=False)
    recovery_email = Column(Text)
    recovery_phone = Column(Text)

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
            "telefon": self.telefon,
            "idioma": self.idioma,
            "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
            "two_factor_enabled": self.two_factor_enabled,
            "login_alerts_enabled": self.login_alerts_enabled,
            "recovery_email": self.recovery_email,
            "recovery_phone": self.recovery_phone,
        }
