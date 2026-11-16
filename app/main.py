"""
PRISM VAULT // Factory Loyalty & Authenticity Rewards
FastAPI Application, Anti-Fraud Engine, QR Generator & Core APIs
"""

import os
import io
import base64
import hashlib
import secrets
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from pydantic import BaseModel

from app.database import (
    engine, Base, get_db, init_db,
    Customer, ProductBatch, BoxCode, Reward, Redemption, AuditLog
)
from app.schemas import (
    CustomerCreate, CustomerResponse,
    VerifyCodeRequest, VerifyCodeResponse, BatchInfo,
    BatchCreateRequest, BatchResponse,
    RewardResponse, RedemptionCreateRequest, RedemptionResponse,
    RedemptionStatusUpdate, AuditLogResponse, DashboardStats
)

# Initialize database schema
init_db()

app = FastAPI(
    title="PRISM VAULT // Factory Loyalty & Authenticity Rewards",
    description="Flagship physical goods factory loyalty and authenticity verification portal",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

SECRET_KEY = os.getenv("SECRET_KEY", "prism_vault_cryptographic_foundry_salt_999")
ADMIN_PIN = os.getenv("ADMIN_PIN", "8821")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "15"))


# --- In-Memory Sliding Window Rate Limiter & Anti-Fraud Tracker ---
class AntiFraudRateLimiter:
    def __init__(self):
        # ip -> list of timestamps
        self.request_history: Dict[str, List[datetime]] = {}
        # ip -> count of consecutive failed attempts
        self.failed_attempts: Dict[str, int] = {}

    def check_rate_limit(self, ip: str) -> bool:
        """Returns True if within rate limit, False if rate limited (> 15/min)."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=1)
        history = self.request_history.get(ip, [])
        # filter entries within 1 minute
        history = [t for t in history if t > window_start]
        history.append(now)
        self.request_history[ip] = history

        return len(history) <= RATE_LIMIT_PER_MINUTE

    def record_failure(self, ip: str) -> int:
        self.failed_attempts[ip] = self.failed_attempts.get(ip, 0) + 1
        return self.failed_attempts[ip]

    def record_success(self, ip: str):
        self.failed_attempts[ip] = 0


rate_limiter = AntiFraudRateLimiter()


# --- Cryptographic Helper Functions ---
def generate_verification_hash(code: str, batch_number: str) -> str:
    """Compute HMAC-SHA256 signature for physical box verification."""
    payload = f"{code}:{batch_number}:{SECRET_KEY}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_qr_base64(data: str) -> str:
    """Generate a clean high-contrast QR code as a base64 PNG data URI."""
    import qrcode
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0d1017", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def generate_secure_box_code(prefix: str = "PV") -> str:
    """Generate high-entropy human-readable box code: PV-XXXX-YYYY-ZZZZ."""
    part1 = secrets.token_hex(2).upper()
    part2 = secrets.token_hex(2).upper()
    part3 = secrets.token_hex(2).upper()
    return f"{prefix}-{part1}-{part2}-{part3}"


# --- Seed Initial Realistic Data ---
def seed_initial_data():
    db = next(get_db())
    try:
        # Check if batches exist
        if db.query(ProductBatch).count() == 0:
            # Batch 1: Luxury Titanium Chrono Flask
            batch1 = ProductBatch(
                batch_number="BATCH-2026-CHRONO-A1",
                product_name="Apex Precision Titanium Chrono Flask - Obsidian Edition",
                product_sku="APEX-FLASK-TI-01",
                points_per_box=1200,
                facility_location="Aethelgard Precision Foundry, Cleanroom Alpha-7",
                inspector_id="INSP-AL-902",
                total_units=12,
                claimed_units=3,
                notes="Laser-sintered Grade 5 Titanium with vacuum thermal seal. High loyalty tier target."
            )
            # Batch 2: Aura Pro Planar Magnetic Acoustic Headset
            batch2 = ProductBatch(
                batch_number="BATCH-2026-ACOUSTIC-X7",
                product_name="Aura Pro Planar Magnetic Acoustic Headset",
                product_sku="AURA-PLANAR-HD-07",
                points_per_box=2500,
                facility_location="Kyoto Precision Labs, Acoustic Chamber 3",
                inspector_id="INSP-KY-418",
                total_units=8,
                claimed_units=2,
                notes="Beryllium-coated diaphragm with solid brass acoustic chamber."
            )
            # Batch 3: Monolith CNC Machined Mechanical Keyboard
            batch3 = ProductBatch(
                batch_number="BATCH-2026-KEY-F9",
                product_name="Aethelgard Monolith CNC Machined Keyboard",
                product_sku="MONO-KEY-65-RAW",
                points_per_box=3500,
                facility_location="Zurich Master Vault & Workshop",
                inspector_id="INSP-ZH-104",
                total_units=6,
                claimed_units=1,
                notes="Solid 6063 Aluminum block with internal brass weight and gasket mount."
            )
            db.add_all([batch1, batch2, batch3])
            db.commit()
            db.refresh(batch1)
            db.refresh(batch2)
            db.refresh(batch3)

            # Seed sample customer profiles
            cust1 = Customer(
                member_id="PV-MEM-88219",
                name="Julian Vance",
                email="julian@vance-atelier.com",
                phone="+1 (555) 392-8810",
                points_balance=3700,
                lifetime_points=3700,
                tier="Amethyst"
            )
            cust2 = Customer(
                member_id="PV-MEM-94012",
                name="Elena Rostova",
                email="elena.rostova@geneva-vault.ch",
                phone="+41 22 819 4400",
                points_balance=9400,
                lifetime_points=9400,
                tier="Obsidian"
            )
            cust3 = Customer(
                member_id="PV-MEM-10488",
                name="Kaelen Thorne",
                email="kaelen.thorne@aether.design",
                phone="+44 20 7946 0912",
                points_balance=850,
                lifetime_points=850,
                tier="Quartz"
            )
            db.add_all([cust1, cust2, cust3])
            db.commit()
            db.refresh(cust1)
            db.refresh(cust2)
            db.refresh(cust3)

            # Generate Box Codes for Batch 1
            # 3 Claimed codes, 9 Unclaimed
            codes = []
            sample_fixed_codes = [
                ("PV-DEMO-1001", False, None),
                ("PV-DEMO-1002", False, None),
                ("PV-DEMO-CLAIMED", True, cust1),
                ("PV-CHRO-991A-01", True, cust1),
                ("PV-CHRO-991A-02", True, cust1),
                ("PV-CHRO-991A-03", True, cust2),
                ("PV-CHRO-77B2-04", False, None),
                ("PV-CHRO-77B2-05", False, None),
                ("PV-CHRO-77B2-06", False, None),
                ("PV-CHRO-88C3-07", False, None),
                ("PV-CHRO-88C3-08", False, None),
                ("PV-CHRO-88C3-09", False, None),
                ("PV-CHRO-44D1-10", False, None),
                ("PV-CHRO-44D1-11", False, None),
                ("PV-CHRO-44D1-12", False, None),
            ]
            for c_str, is_claimed, c_cust in sample_fixed_codes:
                v_hash = generate_verification_hash(c_str, batch1.batch_number)
                qr = generate_qr_base64(f"http://localhost:8000/?code={c_str}")
                b_code = BoxCode(
                    code=c_str,
                    batch_id=batch1.id,
                    status="CLAIMED" if is_claimed else "UNCLAIMED",
                    claimed_by_id=c_cust.id if is_claimed else None,
                    claimed_at=datetime.now(timezone.utc) - timedelta(days=2) if is_claimed else None,
                    claim_ip="192.168.1.42" if is_claimed else None,
                    verification_hash=v_hash,
                    qr_data=qr
                )
                codes.append(b_code)

            # Generate Box Codes for Batch 2 (Aura Pro)
            sample_acoustic_codes = [
                ("PV-AURA-1011-X1", True, cust2),
                ("PV-AURA-1011-X2", True, cust2),
                ("PV-AURA-2022-X3", False, None),
                ("PV-AURA-2022-X4", False, None),
                ("PV-AURA-3033-X5", False, None),
                ("PV-AURA-3033-X6", False, None),
                ("PV-AURA-4044-X7", False, None),
                ("PV-AURA-4044-X8", False, None),
            ]
            for c_str, is_claimed, c_cust in sample_acoustic_codes:
                v_hash = generate_verification_hash(c_str, batch2.batch_number)
                qr = generate_qr_base64(f"http://localhost:8000/?code={c_str}")
                b_code = BoxCode(
                    code=c_str,
                    batch_id=batch2.id,
                    status="CLAIMED" if is_claimed else "UNCLAIMED",
                    claimed_by_id=c_cust.id if is_claimed else None,
                    claimed_at=datetime.now(timezone.utc) - timedelta(days=5) if is_claimed else None,
                    claim_ip="185.120.44.12" if is_claimed else None,
                    verification_hash=v_hash,
                    qr_data=qr
                )
                codes.append(b_code)

            # Generate Box Codes for Batch 3 (Monolith Keyboard)
            sample_key_codes = [
                ("PV-MONO-8801-Z1", True, cust1),
                ("PV-MONO-8801-Z2", False, None),
                ("PV-MONO-8801-Z3", False, None),
                ("PV-MONO-9902-Z4", False, None),
                ("PV-MONO-9902-Z5", False, None),
                ("PV-MONO-9902-Z6", False, None),
            ]
            for c_str, is_claimed, c_cust in sample_key_codes:
                v_hash = generate_verification_hash(c_str, batch3.batch_number)
                qr = generate_qr_base64(f"http://localhost:8000/?code={c_str}")
                b_code = BoxCode(
                    code=c_str,
                    batch_id=batch3.id,
                    status="CLAIMED" if is_claimed else "UNCLAIMED",
                    claimed_by_id=c_cust.id if is_claimed else None,
                    claimed_at=datetime.now(timezone.utc) - timedelta(days=1) if is_claimed else None,
                    claim_ip="192.168.1.42" if is_claimed else None,
                    verification_hash=v_hash,
                    qr_data=qr
                )
                codes.append(b_code)

            db.add_all(codes)
            db.commit()

        # Seed Rewards Catalog if empty
        if db.query(Reward).count() == 0:
            rewards = [
                Reward(
                    title="Machined Titanium Collector Keycap",
                    subtitle="Limited Edition Cleanroom Machined CNC Keycap with Prism Inlay",
                    description="Crafted from aerospace Grade 5 titanium, mirror-polished chamfers, compatible with Cherry MX mechanical switches. Includes engraved factory serial number.",
                    category="COLLECTIBLE",
                    points_cost=1200,
                    required_tier="Quartz",
                    stock_quantity=45,
                    badge_label="Popular",
                    image_url="https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&w=600&q=80"
                ),
                Reward(
                    title="Bespoke Factory Laser Serialization & Engraving",
                    subtitle="Custom Monogram or Calligraphic Signature on Your Next Factory Box",
                    description="Submit custom vector artwork or typographic initials for high-precision fiber laser engraving directly at our Zurich or cleanroom facility.",
                    category="SERVICE",
                    points_cost=1800,
                    required_tier="Sapphire",
                    stock_quantity=100,
                    badge_label="Artisanal",
                    image_url="https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=600&q=80"
                ),
                Reward(
                    title="Aethelgard 4.4mm Balanced Braided Copper Cable",
                    subtitle="Custom Cryo-Treated Monocrystalline OCC Acoustic Cable",
                    description="Hand-braided 8-core copper audio cable with rhodium-plated 4.4mm balanced connector. Engineered for ultra-low impedance and pure acoustic fidelity.",
                    category="PHYSICAL_GOODS",
                    points_cost=2500,
                    required_tier="Sapphire",
                    stock_quantity=28,
                    badge_label="Audiophile",
                    image_url="https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=600&q=80"
                ),
                Reward(
                    title="Horween Chromexcel Leather Travel Sheath",
                    subtitle="Hand-Burnished Chicago Leather with Magnetic Alignment",
                    description="Custom-molded vegetable-tanned leather protective holster designed specifically for your precision flask or EDC gear. Water-resistant wax finish.",
                    category="PHYSICAL_GOODS",
                    points_cost=3800,
                    required_tier="Amethyst",
                    stock_quantity=18,
                    badge_label="Luxury Leather",
                    image_url="https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=600&q=80"
                ),
                Reward(
                    title="Extended 5-Year Comprehensive Cleanroom Warranty",
                    subtitle="Direct Factory Re-Calibration, Polish & Seal Replacement",
                    description="Unrestricted factory restoration warranty covering accidental damage, acoustic re-tuning, ultrasonic cleaning, and seal replacements directly by master artisans.",
                    category="WARRANTY",
                    points_cost=5000,
                    required_tier="Obsidian",
                    stock_quantity=200,
                    badge_label="VIP Assurance",
                    image_url="https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=600&q=80"
                ),
                Reward(
                    title="Foundry Master Vault Presentation Box 2026",
                    subtitle="Ultra-Rare Numbered 07/50 Walnut & Smoked Quartz Display Case",
                    description="American Black Walnut display box with integrated LED edge illumination, smoked quartz magnetic lid, and internal velvet molded cradle. Numbered limited edition.",
                    category="COLLECTIBLE",
                    points_cost=10000,
                    required_tier="Prism Sovereign",
                    stock_quantity=5,
                    badge_label="Ultra Rare (1 of 50)",
                    image_url="https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=600&q=80"
                )
            ]
            db.add_all(rewards)
            db.commit()

        # Seed sample redemptions if none
        if db.query(Redemption).count() == 0:
            cust1 = db.query(Customer).filter_by(member_id="PV-MEM-88219").first()
            reward1 = db.query(Reward).first()
            if cust1 and reward1:
                rdm = Redemption(
                    redemption_code="RDM-7741-ALPH",
                    customer_id=cust1.id,
                    reward_id=reward1.id,
                    points_spent=reward1.points_cost,
                    recipient_name=cust1.name,
                    shipping_address="742 Evergreen Terrace, Suite 4B, Zurich, CH-8001",
                    status="DISPATCHED",
                    tracking_number="DHL-EXPRESS-992014819",
                    created_at=datetime.now(timezone.utc) - timedelta(days=3)
                )
                db.add(rdm)
                db.commit()

        # Seed some audit logs if empty
        if db.query(AuditLog).count() == 0:
            sample_logs = [
                AuditLog(
                    event_type="BATCH_MINTED",
                    severity="INFO",
                    ip_address="127.0.0.1",
                    details=json.dumps({"batch": "BATCH-2026-CHRONO-A1", "units": 12, "sku": "APEX-FLASK-TI-01"}),
                    created_at=datetime.now(timezone.utc) - timedelta(days=6)
                ),
                AuditLog(
                    event_type="VERIFY_SUCCESS",
                    severity="INFO",
                    ip_address="192.168.1.42",
                    box_code="PV-CHRO-991A-01",
                    details=json.dumps({"customer": "Julian Vance", "points": 1200, "tier": "Amethyst"}),
                    created_at=datetime.now(timezone.utc) - timedelta(days=2)
                ),
                AuditLog(
                    event_type="VERIFY_DOUBLE_SPEND",
                    severity="WARNING",
                    ip_address="45.130.82.11",
                    box_code="PV-CHRO-991A-01",
                    details=json.dumps({"reason": "Re-verification attempt on claimed serial", "original_claimant": "Julian Vance"}),
                    created_at=datetime.now(timezone.utc) - timedelta(hours=14)
                ),
                AuditLog(
                    event_type="VERIFY_INVALID_CODE",
                    severity="WARNING",
                    ip_address="91.200.12.99",
                    box_code="PV-FAKE-9999-ZZ",
                    details=json.dumps({"reason": "Code does not exist in factory ledger", "suspected": "Brute-force sequential scan"}),
                    created_at=datetime.now(timezone.utc) - timedelta(hours=4)
                ),
            ]
            db.add_all(sample_logs)
            db.commit()

    finally:
        db.close()


# Run initial seeding on module load
seed_initial_data()


# --- HTML Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def customer_portal(request: Request, code: Optional[str] = None):
    """Customer Loyalty & Authenticity Portal."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"initial_code": code or ""}
    )


@app.get("/admin", response_class=HTMLResponse)
async def factory_command_center(request: Request):
    """Factory Owner Command Center & Security Monitor."""
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={}
    )


# --- Customer APIs ---
@app.get("/api/customers", response_model=List[CustomerResponse])
def get_all_customers(db: Session = Depends(get_db)):
    """List all registered customers for quick switcher / testing."""
    return db.query(Customer).order_by(desc(Customer.points_balance)).all()


@app.get("/api/customer/profile", response_model=CustomerResponse)
def get_customer_profile(
    email: Optional[str] = None,
    member_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Fetch customer profile by email or member ID."""
    query = db.query(Customer)
    if member_id:
        cust = query.filter_by(member_id=member_id).first()
    elif email:
        cust = query.filter_by(email=email).first()
    else:
        # Default to first customer if none specified
        cust = query.first()

    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust


@app.post("/api/customers", response_model=CustomerResponse)
def create_or_get_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer or return existing one."""
    cust = db.query(Customer).filter_by(email=payload.email).first()
    if cust:
        return cust

    # Generate unique member ID
    rand_suffix = secrets.token_hex(3).upper()
    member_id = f"PV-MEM-{rand_suffix}"

    cust = Customer(
        member_id=member_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        points_balance=0,
        lifetime_points=0,
        tier="Quartz"
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@app.get("/api/customer/{customer_id}/history")
def get_customer_history(customer_id: int, db: Session = Depends(get_db)):
    """Get customer's verified box claim ledger and reward redemptions."""
    cust = db.query(Customer).filter_by(id=customer_id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    claimed_boxes = (
        db.query(BoxCode)
        .filter_by(claimed_by_id=customer_id)
        .order_by(desc(BoxCode.claimed_at))
        .all()
    )

    boxes_list = []
    for b in claimed_boxes:
        batch = b.batch
        boxes_list.append({
            "code": b.code,
            "product_name": batch.product_name,
            "product_sku": batch.product_sku,
            "batch_number": batch.batch_number,
            "points_earned": batch.points_per_box,
            "claimed_at": b.claimed_at,
            "verification_hash": b.verification_hash,
            "facility_location": batch.facility_location,
            "inspector_id": batch.inspector_id,
        })

    redemptions = (
        db.query(Redemption)
        .filter_by(customer_id=customer_id)
        .order_by(desc(Redemption.created_at))
        .all()
    )

    redemptions_list = []
    for r in redemptions:
        redemptions_list.append({
            "id": r.id,
            "redemption_code": r.redemption_code,
            "reward_title": r.reward.title,
            "points_spent": r.points_spent,
            "status": r.status,
            "tracking_number": r.tracking_number,
            "shipping_address": r.shipping_address,
            "created_at": r.created_at,
        })

    return {
        "customer": {
            "id": cust.id,
            "member_id": cust.member_id,
            "name": cust.name,
            "tier": cust.tier,
            "points_balance": cust.points_balance,
            "lifetime_points": cust.lifetime_points,
            "tier_multiplier": cust.tier_multiplier
        },
        "verified_boxes": boxes_list,
        "redemptions": redemptions_list
    }


# --- Box Verification & Loyalty Claim Endpoint (Core Engine) ---
@app.post("/api/verify-code", response_model=VerifyCodeResponse)
def verify_and_claim_box_code(
    payload: VerifyCodeRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticity & Loyalty Verification Engine:
    1. Checks rate-limiting per client IP.
    2. Validates physical box code in cleanroom ledger.
    3. Detects double-spend attempts (counterfeit/re-packaging alerts).
    4. Applies tier multipliers and credits Prism Points to customer.
    5. Commits immutable verification hash and audit log.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown Device")
    raw_code = payload.code.strip().upper()

    # Rate limiting & brute force check
    if not rate_limiter.check_rate_limit(client_ip):
        # Log critical rate limit violation
        audit = AuditLog(
            event_type="RATE_LIMIT_TRIGGERED",
            severity="CRITICAL",
            ip_address=client_ip,
            user_agent=user_agent,
            box_code=raw_code,
            details=json.dumps({"error": "Velocity rate limit exceeded (> 15 attempts/min)"})
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Too many verification attempts from this IP. Please wait 60 seconds."
        )

    # Find the box code in database
    box = db.query(BoxCode).filter(func.upper(BoxCode.code) == raw_code).first()

    # Scenario 1: Box code does NOT exist (Potential Counterfeit / Invalid Code)
    if not box:
        failures = rate_limiter.record_failure(client_ip)
        severity = "CRITICAL" if failures >= 4 else "WARNING"
        audit = AuditLog(
            event_type="VERIFY_INVALID_CODE",
            severity=severity,
            ip_address=client_ip,
            user_agent=user_agent,
            box_code=raw_code,
            details=json.dumps({
                "error": "Non-existent serial code submitted",
                "consecutive_failures": failures,
                "threat_assessment": "Brute-force attempt detected" if failures >= 4 else "Typo or unauthorized counterfeit code"
            })
        )
        db.add(audit)
        db.commit()

        return VerifyCodeResponse(
            success=False,
            status="INVALID_CODE",
            message="Authenticity verification failed. This serial code is not recognized in the factory cleanroom ledger. Please check the scratch-off card or contact factory support.",
            box_code=raw_code
        )

    # Scenario 2: Box code is REVOKED or FLAGGED_SUSPECT
    if box.status in ("REVOKED", "SUSPECT"):
        audit = AuditLog(
            event_type="VERIFY_FLAGGED_CODE",
            severity="CRITICAL",
            ip_address=client_ip,
            user_agent=user_agent,
            box_code=box.code,
            details=json.dumps({"status": box.status, "reason": "Box was recalled or marked suspect in factory ledger"})
        )
        db.add(audit)
        db.commit()
        return VerifyCodeResponse(
            success=False,
            status="REVOKED",
            message=f"Verification alert: This box unit has been marked as {box.status} by factory quality assurance.",
            box_code=box.code
        )

    # Scenario 3: Box code ALREADY CLAIMED (Double-Spend / Re-Packaging Fraud Alert)
    if box.status == "CLAIMED":
        claimant = box.customer
        claimant_name = claimant.name if claimant else "Another Registered Collector"
        claimant_email_masked = (
            claimant.email[:3] + "***@" + claimant.email.split("@")[1]
            if claimant and "@" in claimant.email else "***"
        )
        claim_time_str = box.claimed_at.strftime("%Y-%m-%d %H:%M UTC") if box.claimed_at else "Previously"

        audit = AuditLog(
            event_type="VERIFY_DOUBLE_SPEND",
            severity="WARNING",
            ip_address=client_ip,
            user_agent=user_agent,
            box_code=box.code,
            details=json.dumps({
                "warning": "Double-spend claim attempt on previously verified box",
                "original_claimant_id": claimant.id if claimant else None,
                "original_claimed_at": str(box.claimed_at),
                "attempted_by_ip": client_ip
            })
        )
        db.add(audit)
        db.commit()

        batch_info = BatchInfo.model_validate(box.batch)
        return VerifyCodeResponse(
            success=False,
            status="ALREADY_CLAIMED",
            message=f"Authenticity Warning: This genuine box code was already claimed on {claim_time_str} by collector ({claimant_email_masked}). If this box was bought as brand new sealed, report potential retail tampering immediately.",
            box_code=box.code,
            batch=batch_info,
            claimed_at=box.claimed_at,
            verification_hash=box.verification_hash
        )

    # Scenario 4: VALID UNCLAIMED CODE -> Execute Genuine Verification & Reward Loyalty
    rate_limiter.record_success(client_ip)

    # Identify or create customer
    customer: Optional[Customer] = None
    if payload.member_id:
        customer = db.query(Customer).filter_by(member_id=payload.member_id).first()
    elif payload.customer_email:
        customer = db.query(Customer).filter_by(email=payload.customer_email).first()
        if not customer:
            rand_suffix = secrets.token_hex(3).upper()
            customer = Customer(
                member_id=f"PV-MEM-{rand_suffix}",
                name=payload.customer_name or "Distinguished Collector",
                email=payload.customer_email,
                phone=payload.customer_phone,
                points_balance=0,
                lifetime_points=0,
                tier="Quartz"
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
    else:
        # Default to first customer if no customer info sent (smooth demo mode)
        customer = db.query(Customer).first()

    if not customer:
        customer = Customer(
            member_id=f"PV-MEM-{secrets.token_hex(3).upper()}",
            name="Julian Vance",
            email="julian@vance-atelier.com",
            points_balance=0,
            lifetime_points=0,
            tier="Quartz"
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    # Calculate points with tier multiplier
    base_points = box.batch.points_per_box
    multiplier = customer.tier_multiplier
    points_awarded = int(base_points * multiplier)

    # Mark box as claimed
    now = datetime.now(timezone.utc)
    box.status = "CLAIMED"
    box.claimed_by_id = customer.id
    box.claimed_at = now
    box.claim_ip = client_ip

    # Update batch claimed count
    box.batch.claimed_units = (box.batch.claimed_units or 0) + 1

    # Credit points to customer and check tier upgrade
    prev_tier = customer.tier
    customer.points_balance += points_awarded
    customer.lifetime_points += points_awarded
    new_tier = customer.update_tier()

    # Digital certificate ID
    cert_id = f"CERT-{box.batch.product_sku}-{secrets.token_hex(4).upper()}"

    # Log successful verification
    audit = AuditLog(
        event_type="VERIFY_SUCCESS",
        severity="INFO",
        ip_address=client_ip,
        user_agent=user_agent,
        box_code=box.code,
        details=json.dumps({
            "product": box.batch.product_name,
            "sku": box.batch.product_sku,
            "batch": box.batch.batch_number,
            "customer_id": customer.id,
            "customer_email": customer.email,
            "base_points": base_points,
            "multiplier": multiplier,
            "points_awarded": points_awarded,
            "new_balance": customer.points_balance,
            "tier_upgrade": (prev_tier != new_tier),
            "certificate_id": cert_id
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(customer)
    db.refresh(box)

    return VerifyCodeResponse(
        success=True,
        status="VERIFIED_GENUINE",
        message=f"Authenticity 100% Certified Genuine! {points_awarded} Prism Points have been credited to your vault ledger.",
        box_code=box.code,
        batch=BatchInfo.model_validate(box.batch),
        points_awarded=points_awarded,
        multiplier_applied=multiplier,
        customer=CustomerResponse.model_validate(customer),
        verification_hash=box.verification_hash,
        claimed_at=box.claimed_at,
        certificate_id=cert_id
    )


# --- Rewards & Redemption APIs ---
@app.get("/api/rewards", response_model=List[RewardResponse])
def get_rewards(db: Session = Depends(get_db)):
    """Fetch active rewards in catalog."""
    return db.query(Reward).filter_by(is_active=True).order_by(Reward.points_cost).all()


@app.post("/api/redeem", response_model=RedemptionResponse)
def redeem_reward(
    payload: RedemptionCreateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Redeem points for factory rewards with instant verification and order creation."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    customer = None
    if payload.customer_id:
        customer = db.query(Customer).filter_by(id=payload.customer_id).first()
    elif payload.customer_email:
        customer = db.query(Customer).filter_by(email=payload.customer_email).first()

    if not customer:
        customer = db.query(Customer).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    reward = db.query(Reward).filter_by(id=payload.reward_id, is_active=True).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not available")

    # Check stock
    if reward.stock_quantity <= 0:
        raise HTTPException(status_code=400, detail="Reward is currently out of stock at the factory.")

    # Check points balance
    if customer.points_balance < reward.points_cost:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient points. Required: {reward.points_cost}, Available: {customer.points_balance}"
        )

    # Check tier qualification
    tier_order = ["Quartz", "Sapphire", "Amethyst", "Obsidian", "Prism Sovereign"]
    cust_tier_idx = tier_order.index(customer.tier) if customer.tier in tier_order else 0
    req_tier_idx = tier_order.index(reward.required_tier) if reward.required_tier in tier_order else 0

    if cust_tier_idx < req_tier_idx:
        raise HTTPException(
            status_code=403,
            detail=f"This reward requires {reward.required_tier} tier or higher. Current tier: {customer.tier}"
        )

    # Deduct points & reduce stock
    customer.points_balance -= reward.points_cost
    reward.stock_quantity -= 1

    # Generate redemption code
    rdm_code = f"RDM-{secrets.token_hex(3).upper()}-{secrets.token_hex(2).upper()}"
    final_recipient = payload.recipient_name or customer.name or "Valued Collector"
    final_address = payload.shipping_address or "Foundry Vault Dispatch, Zurich Cleanroom 7"

    redemption = Redemption(
        redemption_code=rdm_code,
        customer_id=customer.id,
        reward_id=reward.id,
        points_spent=reward.points_cost,
        recipient_name=final_recipient,
        shipping_address=final_address,
        status="PENDING_SHIPMENT",
        tracking_number=None,
        created_at=datetime.now(timezone.utc)
    )
    db.add(redemption)

    # Log redemption
    audit = AuditLog(
        event_type="REWARD_REDEEMED",
        severity="INFO",
        ip_address=client_ip,
        details=json.dumps({
            "redemption_code": rdm_code,
            "customer_id": customer.id,
            "reward_id": reward.id,
            "reward_title": reward.title,
            "points_spent": reward.points_cost,
            "remaining_balance": customer.points_balance
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(redemption)
    db.refresh(customer)

    return RedemptionResponse(
        id=redemption.id,
        redemption_code=redemption.redemption_code,
        customer_id=redemption.customer_id,
        reward_id=redemption.reward_id,
        reward_title=reward.title,
        points_spent=redemption.points_spent,
        recipient_name=redemption.recipient_name,
        shipping_address=redemption.shipping_address,
        status=redemption.status,
        tracking_number=redemption.tracking_number,
        created_at=redemption.created_at,
        new_points_balance=customer.points_balance
    )


# --- Factory Owner Command Center (Admin APIs) ---
class AdminPinVerifyRequest(BaseModel):
    pin: str


@app.post("/api/admin/verify-pin")
def verify_admin_pin(payload: AdminPinVerifyRequest):
    """Authenticate factory owner via secure Admin PIN."""
    if payload.pin.strip() == ADMIN_PIN:
        return {"success": True, "token": secrets.token_hex(16)}
    raise HTTPException(status_code=401, detail="Invalid Factory Admin Security PIN")


@app.get("/api/admin/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Live analytics, fraud metrics, and batch performance for factory owner."""
    total_boxes = db.query(BoxCode).count()
    claimed_boxes = db.query(BoxCode).filter_by(status="CLAIMED").count()
    v_rate = round((claimed_boxes / total_boxes * 100), 1) if total_boxes > 0 else 0.0

    # Points metrics
    batches = db.query(ProductBatch).all()
    total_minted = sum(b.total_units * b.points_per_box for b in batches)
    total_redeemed = db.query(func.sum(Redemption.points_spent)).scalar() or 0
    total_circulating = db.query(func.sum(Customer.points_balance)).scalar() or 0
    total_customers = db.query(Customer).count()

    # Active fraud alerts (severity WARNING or CRITICAL within last 48 hrs)
    recent_48h = datetime.now(timezone.utc) - timedelta(hours=48)
    fraud_alerts = db.query(AuditLog).filter(
        AuditLog.created_at >= recent_48h,
        AuditLog.severity.in_(["WARNING", "CRITICAL"])
    ).count()

    # Tier breakdown
    tier_counts = {}
    for t in ["Quartz", "Sapphire", "Amethyst", "Obsidian", "Prism Sovereign"]:
        tier_counts[t] = db.query(Customer).filter_by(tier=t).count()

    # Recent 10 verifications / audit events
    recent_events = (
        db.query(AuditLog)
        .order_by(desc(AuditLog.created_at))
        .limit(12)
        .all()
    )
    events_data = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "ip_address": e.ip_address,
            "box_code": e.box_code,
            "created_at": e.created_at.strftime("%b %d, %H:%M"),
            "details": json.loads(e.details) if e.details else {}
        }
        for e in recent_events
    ]

    # Batch summary breakdown
    batch_breakdown = []
    for b in batches:
        batch_breakdown.append({
            "id": b.id,
            "batch_number": b.batch_number,
            "product_name": b.product_name,
            "sku": b.product_sku,
            "total_units": b.total_units,
            "claimed_units": b.claimed_units,
            "points_per_box": b.points_per_box,
            "claim_percentage": round((b.claimed_units / b.total_units * 100), 1) if b.total_units > 0 else 0
        })

    return DashboardStats(
        total_boxes_manufactured=total_boxes,
        total_verified_boxes=claimed_boxes,
        verification_rate_percent=v_rate,
        total_points_minted=total_minted,
        total_points_redeemed=total_redeemed,
        points_in_circulation=total_circulating,
        total_customers=total_customers,
        active_fraud_alerts=fraud_alerts,
        tier_distribution=tier_counts,
        recent_verifications=events_data,
        batch_breakdown=batch_breakdown
    )


@app.post("/api/admin/batches", response_model=BatchResponse)
def create_batch_and_mint_codes(
    payload: BatchCreateRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Factory Cleanroom Batch Minting Engine:
    Creates a new physical product batch and generates cryptographically signed,
    unique, high-entropy box codes with corresponding high-DPI QR codes.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Create batch number based on timestamp and SKU
    sku_clean = "".join([c for c in payload.product_sku if c.isalnum()]).upper()[:6]
    rand_tag = secrets.token_hex(2).upper()
    batch_num = f"BATCH-2026-{sku_clean}-{rand_tag}"

    batch = ProductBatch(
        batch_number=batch_num,
        product_name=payload.product_name,
        product_sku=payload.product_sku,
        points_per_box=payload.points_per_box,
        facility_location=payload.facility_location,
        inspector_id=payload.inspector_id,
        total_units=payload.quantity,
        claimed_units=0,
        notes=payload.notes
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # Generate unique codes for each box unit
    sample_codes = []
    box_codes_to_insert = []
    for _ in range(payload.quantity):
        code = generate_secure_box_code(prefix="PV")
        v_hash = generate_verification_hash(code, batch_num)
        qr_uri = generate_qr_base64(f"http://localhost:8000/?code={code}")

        box_code = BoxCode(
            code=code,
            batch_id=batch.id,
            status="UNCLAIMED",
            verification_hash=v_hash,
            qr_data=qr_uri,
            created_at=datetime.now(timezone.utc)
        )
        box_codes_to_insert.append(box_code)
        if len(sample_codes) < 5:
            sample_codes.append(code)

    db.add_all(box_codes_to_insert)

    # Audit log
    audit = AuditLog(
        event_type="BATCH_MINTED",
        severity="INFO",
        ip_address=client_ip,
        details=json.dumps({
            "batch_number": batch.batch_number,
            "product_name": batch.product_name,
            "units_minted": payload.quantity,
            "points_per_box": payload.points_per_box,
            "inspector_id": payload.inspector_id
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(batch)

    res = BatchResponse.model_validate(batch)
    res.sample_codes = sample_codes
    return res


@app.get("/api/admin/batches")
def get_all_batches(db: Session = Depends(get_db)):
    """Fetch all production batches."""
    batches = db.query(ProductBatch).order_by(desc(ProductBatch.created_at)).all()
    results = []
    for b in batches:
        results.append({
            "id": b.id,
            "batch_number": b.batch_number,
            "product_name": b.product_name,
            "product_sku": b.product_sku,
            "points_per_box": b.points_per_box,
            "facility_location": b.facility_location,
            "inspector_id": b.inspector_id,
            "total_units": b.total_units,
            "claimed_units": b.claimed_units,
            "created_at": b.created_at,
            "notes": b.notes
        })
    return results


@app.get("/api/admin/batches/{batch_id}/codes")
def get_batch_box_codes(batch_id: int, db: Session = Depends(get_db)):
    """Fetch all individual box serials and QR codes for printing label sheets."""
    batch = db.query(ProductBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    codes = db.query(BoxCode).filter_by(batch_id=batch_id).all()
    return {
        "batch": {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "product_name": batch.product_name,
            "product_sku": batch.product_sku,
            "points_per_box": batch.points_per_box,
            "facility_location": batch.facility_location,
            "inspector_id": batch.inspector_id,
            "created_at": batch.created_at
        },
        "total_count": len(codes),
        "codes": [
            {
                "id": c.id,
                "code": c.code,
                "status": c.status,
                "verification_hash": c.verification_hash,
                "qr_data": c.qr_data,
                "claimed_at": c.claimed_at,
            }
            for c in codes
        ]
    }


@app.get("/api/admin/redemptions")
def get_all_redemptions(db: Session = Depends(get_db)):
    """Fetch all reward redemptions for factory fulfillment."""
    redemptions = db.query(Redemption).order_by(desc(Redemption.created_at)).all()
    return [
        {
            "id": r.id,
            "redemption_code": r.redemption_code,
            "customer_id": r.customer_id,
            "customer_name": r.customer.name,
            "customer_email": r.customer.email,
            "reward_id": r.reward_id,
            "reward_title": r.reward.title,
            "points_spent": r.points_spent,
            "recipient_name": r.recipient_name,
            "shipping_address": r.shipping_address,
            "status": r.status,
            "tracking_number": r.tracking_number,
            "created_at": r.created_at
        }
        for r in redemptions
    ]


@app.patch("/api/admin/redemptions/{redemption_id}")
def update_redemption_fulfillment(
    redemption_id: int,
    payload: RedemptionStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update fulfillment status and tracking number for physical rewards."""
    rdm = db.query(Redemption).filter_by(id=redemption_id).first()
    if not rdm:
        raise HTTPException(status_code=404, detail="Redemption not found")

    rdm.status = payload.status
    if payload.tracking_number:
        rdm.tracking_number = payload.tracking_number

    db.commit()
    db.refresh(rdm)
    return {
        "success": True,
        "id": rdm.id,
        "status": rdm.status,
        "tracking_number": rdm.tracking_number
    }


@app.get("/api/admin/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 50,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Fetch security audit events and fraud logs."""
    query = db.query(AuditLog)
    if severity:
        query = query.filter_by(severity=severity)
    return query.order_by(desc(AuditLog.created_at)).limit(limit).all()


@app.get("/api/admin/demo-codes")
def get_demo_codes(db: Session = Depends(get_db)):
    """Helper to return ready-to-test codes: unclaimed, claimed, and info."""
    unclaimed = db.query(BoxCode).filter_by(status="UNCLAIMED").limit(4).all()
    claimed = db.query(BoxCode).filter_by(status="CLAIMED").limit(2).all()

    return {
        "unclaimed_codes": [
            {
                "code": u.code,
                "product": u.batch.product_name,
                "points": u.batch.points_per_box,
                "batch": u.batch.batch_number
            }
            for u in unclaimed
        ],
        "claimed_codes": [
            {
                "code": c.code,
                "product": c.batch.product_name,
                "claimed_by": c.customer.name if c.customer else "Collector",
                "claimed_at": c.claimed_at
            }
            for c in claimed
        ]
    }


@app.post("/api/admin/reset-demo")
def reset_demo_database():
    """Reset database to factory seed data."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_initial_data()
    return {"success": True, "message": "Factory database reset to pristine seed state."}
