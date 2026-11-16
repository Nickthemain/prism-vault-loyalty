"""
PRISM VAULT // Factory Loyalty & Authenticity Rewards
Pydantic Request & Response Schemas (Pydantic v2 Compliant)
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# --- Customer Schemas ---
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=40)


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: str
    points_balance: int
    lifetime_points: int
    tier: str
    tier_multiplier: float
    created_at: datetime


# --- Box Code & Verification Schemas ---
class VerifyCodeRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=64, description="Box serial code from inner seal")
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    member_id: Optional[str] = None


class BatchInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_number: str
    product_name: str
    product_sku: str
    facility_location: str
    inspector_id: str
    points_per_box: int
    created_at: datetime


class VerifyCodeResponse(BaseModel):
    success: bool
    status: str  # VERIFIED_GENUINE, ALREADY_CLAIMED, INVALID_CODE, REVOKED
    message: str
    box_code: str
    batch: Optional[BatchInfo] = None
    points_awarded: int = 0
    multiplier_applied: float = 1.0
    customer: Optional[CustomerResponse] = None
    verification_hash: Optional[str] = None
    claimed_at: Optional[datetime] = None
    certificate_id: Optional[str] = None


# --- Product Batch Minting Schemas ---
class BatchCreateRequest(BaseModel):
    product_name: str = Field(..., min_length=3, max_length=160)
    product_sku: str = Field(..., min_length=3, max_length=64)
    quantity: int = Field(..., ge=1, le=500, description="Number of unique box codes to generate")
    points_per_box: int = Field(500, ge=50, le=10000)
    facility_location: str = Field("Aethelgard Precision Foundry, Cleanroom 7", max_length=120)
    inspector_id: str = Field("INSP-AL-902", max_length=64)
    notes: Optional[str] = None


class BoxCodeItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    status: str
    verification_hash: str
    qr_data: Optional[str] = None
    claimed_at: Optional[datetime] = None


class BatchResponse(BatchInfo):
    model_config = ConfigDict(from_attributes=True)

    total_units: int
    claimed_units: int
    notes: Optional[str] = None
    sample_codes: Optional[List[str]] = None


# --- Reward Schemas ---
class RewardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subtitle: Optional[str] = None
    description: str
    category: str
    points_cost: int
    required_tier: str
    stock_quantity: int
    image_url: Optional[str] = None
    badge_label: Optional[str] = None
    is_active: bool


# --- Redemption Schemas ---
class RedemptionCreateRequest(BaseModel):
    customer_id: Optional[int] = None
    customer_email: Optional[str] = None
    reward_id: int
    recipient_name: Optional[str] = Field("Valued Collector", max_length=120)
    shipping_address: Optional[str] = Field("Foundry Vault Dispatch, Zurich Cleanroom 7", max_length=500)


class RedemptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    redemption_code: str
    customer_id: int
    reward_id: int
    reward_title: str
    points_spent: int
    recipient_name: str
    shipping_address: str
    status: str
    tracking_number: Optional[str] = None
    created_at: datetime
    new_points_balance: Optional[int] = None


class RedemptionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(PENDING_SHIPMENT|IN_PRODUCTION|DISPATCHED|COMPLETED)$")
    tracking_number: Optional[str] = None


# --- Audit & Fraud Schemas ---
class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    severity: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    box_code: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime


# --- Factory Analytics Dashboard Schemas ---
class DashboardStats(BaseModel):
    total_boxes_manufactured: int
    total_verified_boxes: int
    verification_rate_percent: float
    total_points_minted: int
    total_points_redeemed: int
    points_in_circulation: int
    total_customers: int
    active_fraud_alerts: int
    tier_distribution: dict
    recent_verifications: List[dict]
    batch_breakdown: List[dict]
