"""
PRISM VAULT // Factory Loyalty & Authenticity Rewards
Database Models & SQLite Configuration via SQLAlchemy
"""

import os
import json
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prism_vault.db")

# SQLite needs check_same_thread=False for FastAPI concurrency
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    phone = Column(String(40), nullable=True)
    points_balance = Column(Integer, default=0, nullable=False)
    lifetime_points = Column(Integer, default=0, nullable=False)
    tier = Column(String(32), default="Quartz", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    claimed_boxes = relationship("BoxCode", back_populates="customer", cascade="all, delete-orphan")
    redemptions = relationship("Redemption", back_populates="customer", cascade="all, delete-orphan")

    def update_tier(self):
        """Update customer tier based on lifetime points."""
        pts = self.lifetime_points
        if pts >= 15000:
            self.tier = "Prism Sovereign"
        elif pts >= 7000:
            self.tier = "Obsidian"
        elif pts >= 3000:
            self.tier = "Amethyst"
        elif pts >= 1000:
            self.tier = "Sapphire"
        else:
            self.tier = "Quartz"
        return self.tier

    @property
    def tier_multiplier(self) -> float:
        multipliers = {
            "Quartz": 1.0,
            "Sapphire": 1.1,
            "Amethyst": 1.25,
            "Obsidian": 1.5,
            "Prism Sovereign": 2.0
        }
        return multipliers.get(self.tier, 1.0)


class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(64), unique=True, index=True, nullable=False)
    product_name = Column(String(160), nullable=False)
    product_sku = Column(String(64), nullable=False)
    points_per_box = Column(Integer, default=500, nullable=False)
    facility_location = Column(String(120), default="Aethelgard Precision Foundry, Cleanroom 7", nullable=False)
    inspector_id = Column(String(64), default="INSP-AL-902", nullable=False)
    total_units = Column(Integer, default=0, nullable=False)
    claimed_units = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    boxes = relationship("BoxCode", back_populates="batch", cascade="all, delete-orphan")


class BoxCode(Base):
    __tablename__ = "box_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, index=True, nullable=False)  # Serial on scratch-off / seal
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=False)
    status = Column(String(32), default="UNCLAIMED", nullable=False)  # UNCLAIMED, CLAIMED, REVOKED, SUSPECT
    claimed_by_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    claimed_at = Column(DateTime, nullable=True)
    claim_ip = Column(String(64), nullable=True)
    verification_hash = Column(String(128), nullable=False)
    qr_data = Column(Text, nullable=True)  # Base64 encoded PNG or SVG data URI
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    batch = relationship("ProductBatch", back_populates="boxes")
    customer = relationship("Customer", back_populates="claimed_boxes")

    __table_args__ = (
        Index("idx_boxcode_status", "status"),
    )


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(160), nullable=False)
    subtitle = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)
    category = Column(String(40), default="PHYSICAL_GOODS", nullable=False)  # PHYSICAL_GOODS, SERVICE, WARRANTY, COLLECTIBLE
    points_cost = Column(Integer, nullable=False)
    required_tier = Column(String(32), default="Quartz", nullable=False)
    stock_quantity = Column(Integer, default=50, nullable=False)
    image_url = Column(String(255), nullable=True)
    badge_label = Column(String(40), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    redemptions = relationship("Redemption", back_populates="reward")


class Redemption(Base):
    __tablename__ = "redemptions"

    id = Column(Integer, primary_key=True, index=True)
    redemption_code = Column(String(40), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    points_spent = Column(Integer, nullable=False)
    recipient_name = Column(String(120), nullable=False)
    shipping_address = Column(Text, nullable=False)
    status = Column(String(32), default="PENDING_SHIPMENT", nullable=False)  # PENDING_SHIPMENT, IN_PRODUCTION, DISPATCHED, COMPLETED
    tracking_number = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="redemptions")
    reward = relationship("Reward", back_populates="redemptions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), index=True, nullable=False)  # e.g., VERIFY_SUCCESS, VERIFY_DOUBLE_SPEND, BRUTE_FORCE_BLOCKED
    severity = Column(String(20), default="INFO", nullable=False)  # INFO, WARNING, CRITICAL
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    box_code = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)  # JSON formatted payload
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_audit_event_created", "event_type", "created_at"),
    )


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables and seed sample data if empty."""
    Base.metadata.create_all(bind=engine)
