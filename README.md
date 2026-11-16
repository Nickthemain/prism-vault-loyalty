# PRISM VAULT // Factory Loyalty & Authenticity Rewards

> **Flagship Physical Goods Authenticity Certification & Factory Loyalty Rewards Web Application**  
> Bespoke **Crystal-Glass & Tactile Luxury ("Liquid Quartz")** Visual Identity.

---

## 💎 Project Overview
**PRISM VAULT** is an end-to-end full-stack loyalty and anti-counterfeiting platform designed for a physical goods manufacturing foundry. The client manufactures precision goods (titanium chronographs, planar magnetic acoustic headsets, CNC machined keyboards, and artisanal accessories) that are distributed globally in sealed retail packaging.

Physical retail boxes face critical vulnerabilities:
1. **Counterfeit & Replica Fraud**: Unauthorized clones erode brand reputation and revenue.
2. **Re-packaging & Return Tampering**: Malicious actors open sealed retail boxes, steal contents or claim points, and re-shrinkwrap boxes.
3. **Customer Retention**: High-ticket buyers require a compelling reason to register genuine goods and become repeat collectors.

PRISM VAULT solves this with a **256-bit cryptographic cleanroom ledger**, **single-use scratch-off/QR verification**, **automated double-spend detection**, an **interactive 3D holographic tilt card**, and a **factory command center with printable QR label sheets**.

---

## 🔮 Liquid Quartz Crystal Tech Stack

- **Backend**:
  - **Python 3.10+** with **FastAPI** (modern async REST endpoints, auto-generated OpenAPI documentation).
  - **SQLAlchemy 2.0** ORM over **SQLite** (atomic transactions, connection-thread pooling, indexed queries).
  - **Pydantic v2** (`BaseModel`, `ConfigDict`, robust data validation).
  - **qrcode[pil]** & **Pillow** (high-DPI dynamic base64 packaging label generation).
  - **pytest** & **httpx** (automated test client and integration test suite).
- **Frontend**:
  - **Vanilla HTML5 & Advanced CSS3**: Bespoke *Liquid Quartz* styling (`backdrop-filter: blur(28px) saturate(190%)`, multi-layer specular top borders, chromatic ambient orbs, and GPU-accelerated transitions).
  - **Interactive 3D Card Physics**: Pure JavaScript mouse/touch perspective parallax (`perspective: 1200px rotateX/rotateY`) with dynamic specular glare and holographic foil overlays.
  - **Zero-Dependency Web Audio API**: Procedural glass crystal chimes and alert frequencies synthesized in-browser.
  - **Chart.js (CDN)**: Real-time cubic spline velocity tracking and collector tier doughnut analytics.
  - **Canvas Confetti**: Visual celebration on verified genuine unboxings.

---

## 🚀 Setup & Run Steps (From Inside `prism-vault-loyalty/`)

### 1. Open Terminal and Enter Project Directory
```bash
cd prism-vault-loyalty
```

### 2. Activate Python Virtual Environment
If using the repository's pre-configured virtual environment:
```bash
# If using the parent workspace venv:
source ../.venv/bin/activate

# Or create a dedicated venv inside the project:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```
Default configuration values:
- `PROJECT_NAME="PRISM VAULT // Factory Loyalty & Authenticity Rewards"`
- `PORT=8000`
- `HOST=127.0.0.1`
- `DATABASE_URL="sqlite:///./prism_vault.db"`
- `SECRET_KEY="prism_vault_super_secret_cryptographic_key_999"`
- `ADMIN_PIN="8821"`
- `RATE_LIMIT_PER_MINUTE=15`

### 4. Run the Development Server
```bash
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access Live Endpoints
- **Customer Loyalty & Authenticity Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Factory Owner Command Center**: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)
- **Interactive Swagger API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🏷️ Ready-to-Test Demo Box Codes

The database is pre-seeded with realistic batch codes ready for instant verification:

| Serial Code | Status | Product Association | Points | Expected Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **`PV-DEMO-1001`** | **UNCLAIMED** | Titanium Chrono Flask (Obsidian Edition) | 1,200 | ✅ 100% Genuine Certified, credits points + multiplier, generates Certificate of Authenticity. |
| **`PV-DEMO-1002`** | **UNCLAIMED** | Aura Pro Planar Acoustic Headset | 2,500 | ✅ 100% Genuine Certified, elevates collector tier, unlocks artisan rewards. |
| **`PV-DEMO-CLAIMED`** | **CLAIMED** | Titanium Chrono Flask | 1,200 | ⚠️ Double-Spend Warning. Surfaces original claim date, masked claimant email, and retail tampering alert. |
| **`PV-CHRO-77B2-04`** | **UNCLAIMED** | Titanium Chrono Flask | 1,200 | ✅ Ready-to-claim cleanroom serial. |
| **`PV-AURA-2022-X3`** | **UNCLAIMED** | Aura Pro Acoustic Headset | 2,500 | ✅ Ready-to-claim acoustic chamber serial. |
| **`PV-FAKE-COUNTERFEIT-999`** | **UNREGISTERED** | Non-cataloged Replica | 0 | 🛑 Security Alert: Unregistered Serial Code. Mismatch against cleanroom ledger. |

> **Tip:** In the web UI, click any pill in the **"Ready-to-Test Factory Samples"** shelf to automatically load and test these codes in 1 click.

---

## 🔐 Factory Admin PIN
- **Default Factory Owner Security PIN**: **`8821`**
- Configurable via `.env` (`ADMIN_PIN=8821`).
- Used to authenticate factory management operations, batch code minting, and logistics dispatch status updates in the Command Center.

---

## 🧪 Running Automated Tests

Run the comprehensive pytest test suite to verify fraud mitigation, double-spend prevention, tier multipliers, batch minting, and reward fulfillment:

```bash
cd prism-vault-loyalty
PYTHONPATH=. pytest tests/test_loyalty.py -v
```

### Test Suite Execution Output:
```text
============================= test session starts ==============================
collected 7 items

tests/test_loyalty.py::test_verify_genuine_box_code_and_accrue_points PASSED [ 14%]
tests/test_loyalty.py::test_prevent_double_spend_fraud PASSED            [ 28%]
tests/test_loyalty.py::test_detect_counterfeit_invalid_code PASSED       [ 42%]
tests/test_loyalty.py::test_reward_redemption_success_and_points_deduction PASSED [ 57%]
tests/test_loyalty.py::test_reward_redemption_insufficient_points PASSED [ 71%]
tests/test_loyalty.py::test_admin_batch_minting_and_unique_codes PASSED  [ 85%]
tests/test_loyalty.py::test_admin_dashboard_metrics PASSED               [100%]

========================= 7 passed, 1 warning in 0.40s =========================
```
