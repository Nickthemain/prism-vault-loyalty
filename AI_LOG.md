# PRISM VAULT // AI Development & Engineering Log

This document records the key iterative prompts, design specifications, and real-world debugging issues encountered and resolved during the end-to-end development of **PRISM VAULT**.

---

## 1. Key Engineering Prompts Used During Development

### Prompt 1: Domain Architecture & Database Schema
```text
Design a production-grade SQLite and SQLAlchemy 2.0 schema for a luxury physical goods 
factory loyalty and authenticity verification platform called "PRISM VAULT". 
The factory produces high-end goods (titanium chronographs, planar magnetic headsets, 
mechanical keyboards) distributed in sealed retail boxes.
Requirements:
- Track Customers (tier, spendable points, lifetime points, member ID).
- Track ProductBatches (SKU, batch number, points per box, facility location, inspector ID).
- Track BoxCodes (unique 12-char serial, status: UNCLAIMED/CLAIMED/REVOKED, SHA-256 hash, QR base64 data).
- Track Rewards & Redemptions (physical fulfillment with tracking numbers).
- Track AuditLogs (event type, severity: INFO/WARNING/CRITICAL, IP address, forensic payload).
- Enforce clean relationships, indexes, and pre-seeded realistic factory data.
```

### Prompt 2: "Liquid Quartz" Visual Identity & 3D Tilt Physics
```text
Do not build a generic dark mode or flat Bootstrap/Tailwind site. Create a bespoke 
"Liquid Quartz" crystal-glass aesthetic inspired by flagship Apple, Stripe, and luxury packaging.
Implement:
- Deep obsidian void background with dynamic chromatic radial ambient mesh gradients.
- Specular glassmorphism (backdrop-filter: blur(28px) saturate(190%)) and micro-borders.
- Interactive 3D perspective membership card:
  - Responds dynamically to mousemove with rotateX and rotateY parallax.
  - Holographic rainbow foil overlay using mix-blend-mode: color-dodge.
  - Dynamic specular glare gradient tracking cursor coordinates.
  - Metallic gold EMV chip, contactless emblem, and animated odometer counter.
- Web Audio API procedural synthesizer for glass crystal chimes without external audio assets.
```

### Prompt 3: Anti-Fraud Engine & Single-Use Atomic Locking
```text
Build a multi-layered anti-counterfeit and anti-fraud engine for /api/verify-code:
1. Prevent double-spend: Once a code is claimed, atomically lock it to CLAIMED with timestamp 
   and IP. If scanned again, reject claim, mint 0 points, log VERIFY_DOUBLE_SPEND warning, 
   and return masked original claimant info with a retail tampering report action.
2. Brute-force protection: Implement an in-memory sliding-window rate limiter restricting IPs 
   to 15 requests per minute (HTTP 429). Track consecutive non-existent serial submissions and 
   escalate severity to CRITICAL after 4 failures.
3. Cryptographic integrity: Compute HMAC-SHA256 signatures for every physical serial.
```

### Prompt 4: Factory Command Center & Printable Packaging QR Labels
```text
Build the Factory Owner Command Center (/admin) with operational cleanroom controls:
- Real-time stat cards (total manufactured boxes, verified genuine rate, points minted vs circulating, active fraud alerts).
- Interactive Chart.js analytics: verification velocity cubic spline line chart and customer tier doughnut chart.
- Batch Minting Studio: Generate high-entropy box codes and dynamic high-DPI QR codes using Pillow/qrcode.
- Printable Packaging Label Sheet: A4/sticker stock grid preview with cut lines, serial codes, 
  and tamper-evident hashes with 1-click window.print() support.
- Logistics Fulfillment Queue: Status updates and courier tracking number assignment.
```

### Prompt 5: Automated Pytest Suite & Test Isolation
```text
Write a comprehensive automated Pytest suite in tests/test_loyalty.py using FastAPI TestClient:
- Test 1: Verify genuine unclaimed code and assert correct tier multiplier points calculation.
- Test 2: Verify double-spend rejection and assert VERIFY_DOUBLE_SPEND audit log creation.
- Test 3: Verify non-existent code returns INVALID_CODE and logs security audit.
- Test 4: Verify reward redemption deducts points, decreases stock, and creates order.
- Test 5: Verify insufficient points or tier restrictions block redemption.
- Test 6: Verify batch minting generates unique cryptographic box codes with QR base64 data.
- Test 7: Verify admin dashboard metrics aggregation.
Ensure database isolation using a separate test SQLite engine.
```

### Prompt 6: Resilient Customer Resolution & Edge-Case Hardening
```text
Review the redemption and verification endpoints for real-world user friction:
- Allow reward redemptions to resolve customers by either customer_id, customer_email, 
  or active session fallback so short test forms or custom automated calls never 422.
- Pre-fill a valid luxury delivery address in the customer portal modal.
- Provide ready-to-test sample code pills (PV-DEMO-1001, PV-DEMO-1002, PV-DEMO-CLAIMED) 
  for instant 1-click demonstration.
```

---

## 2. Real Issues Caught & Fixed During Development

### Issue 1: Starlette 0.46+ / 1.10+ `TemplateResponse` Parameter Order Shift
- **Symptom**: During initial endpoint testing, accessing `GET /` and `GET /admin` threw:
  ```text
  TypeError: cannot use 'tuple' as a dict key (unhashable type: 'dict')
  at jinja2/utils.py in __getitem__ (rv = self._mapping[key])
  ```
- **Root Cause**: In older Starlette versions, `Jinja2Templates.TemplateResponse` accepted `(name, context)`. In modern Starlette (v0.46.0+ / v1.10.0+), the method signature was changed to `(request, name, context=None)`. Calling `TemplateResponse("index.html", {"request": request})` caused Jinja2 to treat `"index.html"` as the request object and the dictionary context as the template name, generating an unhashable cache key error.
- **Resolution**: Updated all route handlers in `app/main.py` to use explicit keyword arguments:
  ```python
  return templates.TemplateResponse(
      request=request,
      name="index.html",
      context={"initial_code": code or ""}
  )
  ```

---

### Issue 2: Nested Directory `PYTHONPATH` Resolution in Pytest & Uvicorn
- **Symptom**: Executing `pytest tests/test_loyalty.py` from within `prism-vault-loyalty/` failed with:
  ```text
  ModuleNotFoundError: No module named 'app'
  ```
- **Root Cause**: The application modules live inside `prism-vault-loyalty/app/`. When running commands without an installed editable package (`pip install -e .`), Python’s `sys.path` did not include the current working directory, preventing imports of `app.main` and `app.database`.
- **Resolution**: 
  1. Standardized all execution scripts and documentation to explicitly prefix commands with `PYTHONPATH=.`:
     ```bash
     cd prism-vault-loyalty
     PYTHONPATH=. pytest tests/test_loyalty.py -v
     PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
     ```
  2. Verified that all imports resolve cleanly both when run from workspace root and from inside `prism-vault-loyalty/`.

---

### Issue 3: Pydantic v2 `min_length` Validation on Redemption Addresses (HTTP 422)
- **Symptom**: Interactive browser testing showed:
  ```text
  POST /api/redeem HTTP/1.1" 422 Unprocessable Content
  ```
- **Root Cause**: The schema `RedemptionCreateRequest` specified `shipping_address: str = Field(..., min_length=10)`. When users submitted quick test addresses (e.g. `"Zurich"`, 6 characters), Pydantic rejected the payload with an unprocessable entity error before reaching business logic.
- **Resolution**:
  1. Softened `RedemptionCreateRequest` constraints in `app/schemas.py`:
     ```python
     class RedemptionCreateRequest(BaseModel):
         customer_id: Optional[int] = None
         customer_email: Optional[str] = None
         reward_id: int
         recipient_name: Optional[str] = Field("Valued Collector", max_length=120)
         shipping_address: Optional[str] = Field("Foundry Vault Dispatch, Zurich Cleanroom 7", max_length=500)
     ```
  2. Added fallback logic in `app/main.py` to automatically resolve customer accounts via ID, email, or active default profile.
  3. Pre-populated the UI modal textarea with a default address (`742 Evergreen Terrace, Suite 4B, Zurich, CH-8001`) to ensure seamless test execution.

---

### Issue 4: Missing `email-validator` Dependency with Pydantic v2
- **Symptom**: App startup initially failed with:
  ```text
  ImportError: email-validator is not installed, run `pip install 'pydantic[email]'`
  ```
- **Root Cause**: Pydantic v2 moved email validation into an optional external library (`email-validator`), requiring an explicit dependency when using `EmailStr`.
- **Resolution**: Installed `email-validator>=2.1.0` in the environment and appended it directly to `requirements.txt`.
