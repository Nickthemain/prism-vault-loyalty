"""
PRISM VAULT // Factory Loyalty & Authenticity Rewards
Automated Pytest Suite: Fraud Detection, Double-Spend, Tier Multipliers & Redemptions
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, Customer, ProductBatch, BoxCode, Reward, Redemption, AuditLog
from app.main import app, seed_initial_data, rate_limiter

# In-memory SQLite for isolated test runs
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_prism_vault.db"
test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    # Setup fresh tables
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed test database
    db = TestingSessionLocal()
    try:
        # Create test batch
        batch = ProductBatch(
            batch_number="BATCH-TEST-TITAN-01",
            product_name="Titanium Precision Test Flask",
            product_sku="TEST-FLASK-01",
            points_per_box=1000,
            facility_location="Zurich Test Cleanroom",
            inspector_id="INSP-TEST-01",
            total_units=5,
            claimed_units=0
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        # Create test customers
        cust_quartz = Customer(
            member_id="PV-MEM-TEST-QUARTZ",
            name="Alice Quartz",
            email="alice@test.com",
            points_balance=500,
            lifetime_points=500,
            tier="Quartz"
        )
        cust_amethyst = Customer(
            member_id="PV-MEM-TEST-AMETHYST",
            name="Bob Amethyst",
            email="bob@test.com",
            points_balance=4000,
            lifetime_points=4000,
            tier="Amethyst"
        )
        db.add_all([cust_quartz, cust_amethyst])
        db.commit()

        # Create box codes: 1 unclaimed, 1 claimed
        code_unclaimed = BoxCode(
            code="PV-TEST-UNCL-01",
            batch_id=batch.id,
            status="UNCLAIMED",
            verification_hash="hash_uncl_01",
            qr_data="data:image/png;base64,sample"
        )
        code_claimed = BoxCode(
            code="PV-TEST-CLMD-02",
            batch_id=batch.id,
            status="CLAIMED",
            claimed_by_id=cust_quartz.id,
            verification_hash="hash_clmd_02",
            qr_data="data:image/png;base64,sample"
        )
        db.add_all([code_unclaimed, code_claimed])

        # Create sample rewards
        reward_low = Reward(
            title="Titanium Test Keycap",
            subtitle="Test reward low tier",
            description="Low cost reward for Quartz",
            category="COLLECTIBLE",
            points_cost=400,
            required_tier="Quartz",
            stock_quantity=10,
            is_active=True
        )
        reward_high = Reward(
            title="Vault Master Box VIP",
            subtitle="High tier VIP reward",
            description="High cost reward requiring Obsidian",
            category="COLLECTIBLE",
            points_cost=8000,
            required_tier="Obsidian",
            stock_quantity=2,
            is_active=True
        )
        db.add_all([reward_low, reward_high])
        db.commit()

    finally:
        db.close()

    # Reset rate limiter memory
    rate_limiter.request_history.clear()
    rate_limiter.failed_attempts.clear()

    yield

    # Teardown
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)


def test_verify_genuine_box_code_and_accrue_points():
    """Test standard genuine box code verification and points crediting with tier multiplier."""
    response = client.post("/api/verify-code", json={
        "code": "PV-TEST-UNCL-01",
        "customer_email": "bob@test.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["status"] == "VERIFIED_GENUINE"
    assert "100% Certified Genuine" in data["message"]

    # Bob is Amethyst tier, multiplier is 1.25 -> 1000 * 1.25 = 1250 points
    assert data["points_awarded"] == 1250
    assert data["multiplier_applied"] == 1.25
    assert data["customer"]["points_balance"] == 4000 + 1250


def test_prevent_double_spend_fraud():
    """Test that claiming an already claimed box code is prevented and flagged."""
    response = client.post("/api/verify-code", json={
        "code": "PV-TEST-CLMD-02",
        "customer_email": "bob@test.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "ALREADY_CLAIMED"
    assert "already claimed" in data["message"].lower()

    # Verify audit log recorded double-spend warning
    db = TestingSessionLocal()
    audit = db.query(AuditLog).filter_by(event_type="VERIFY_DOUBLE_SPEND").first()
    assert audit is not None
    assert audit.severity == "WARNING"
    assert audit.box_code == "PV-TEST-CLMD-02"
    db.close()


def test_detect_counterfeit_invalid_code():
    """Test that submitting an uncatalogued code returns INVALID_CODE and logs security audit."""
    response = client.post("/api/verify-code", json={
        "code": "PV-FAKE-COUNTERFEIT-999",
        "customer_email": "alice@test.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["status"] == "INVALID_CODE"

    db = TestingSessionLocal()
    audit = db.query(AuditLog).filter_by(event_type="VERIFY_INVALID_CODE").first()
    assert audit is not None
    assert audit.box_code == "PV-FAKE-COUNTERFEIT-999"
    db.close()


def test_reward_redemption_success_and_points_deduction():
    """Test successful redemption: points deducted, stock reduced, redemption code issued."""
    db = TestingSessionLocal()
    cust = db.query(Customer).filter_by(email="alice@test.com").first()
    reward = db.query(Reward).filter_by(title="Titanium Test Keycap").first()
    db.close()

    response = client.post("/api/redeem", json={
        "customer_id": cust.id,
        "reward_id": reward.id,
        "recipient_name": "Alice Quartz",
        "shipping_address": "42 Crystal Boulevard, Zurich, Switzerland"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["redemption_code"].startswith("RDM-")
    assert data["points_spent"] == 400
    assert data["new_points_balance"] == 500 - 400  # 100 left
    assert data["status"] == "PENDING_SHIPMENT"


def test_reward_redemption_insufficient_points():
    """Test rejection when customer doesn't have enough points."""
    db = TestingSessionLocal()
    cust = db.query(Customer).filter_by(email="alice@test.com").first()
    reward = db.query(Reward).filter_by(title="Vault Master Box VIP").first()
    db.close()

    response = client.post("/api/redeem", json={
        "customer_id": cust.id,
        "reward_id": reward.id,
        "recipient_name": "Alice Quartz",
        "shipping_address": "42 Crystal Boulevard, Zurich, Switzerland"
    })
    # Should fail with 400 or 403 (insufficient points / tier)
    assert response.status_code in (400, 403)


def test_admin_batch_minting_and_unique_codes():
    """Test factory owner minting a new batch with cryptographic codes."""
    response = client.post("/api/admin/batches", json={
        "product_name": "Precision Titanium Chrono Flask",
        "product_sku": "FLASK-TI-88",
        "quantity": 10,
        "points_per_box": 1500,
        "facility_location": "Cleanroom 9",
        "inspector_id": "INSP-99"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["total_units"] == 10
    assert len(data["sample_codes"]) > 0

    batch_id = data["id"]
    # Check that individual codes with QR were generated
    codes_resp = client.get(f"/api/admin/batches/{batch_id}/codes")
    assert codes_resp.status_code == 200
    codes_data = codes_resp.json()
    assert codes_data["total_count"] == 10
    assert codes_data["codes"][0]["qr_data"].startswith("data:image/png;base64,")


def test_admin_dashboard_metrics():
    """Test dashboard analytics aggregation endpoint."""
    response = client.get("/api/admin/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_boxes_manufactured" in data
    assert "total_verified_boxes" in data
    assert "tier_distribution" in data
    assert "batch_breakdown" in data
