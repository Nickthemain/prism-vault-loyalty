# PRISM VAULT // System Assumptions & Design Decisions

This document outlines every engineering design decision, threat model assumption, and domain gap filled during the architectural design and implementation of the **PRISM VAULT** physical goods factory loyalty and authenticity system.

---

## 1. Physical Proof of Purchase & Box Code Architecture

### The Problem
Physical products sold in sealed retail boxes face an inherent physical-to-digital gap: anyone can photograph an exterior barcode or QR code in a retail store without purchasing the item.

### The Solution & Assumptions
1. **Inner Seal / Scratch-Off Placement**:
   - Each unique box serial code is placed **strictly inside the sealed retail box**—either beneath an opaque scratch-off silver latex foil on an authenticity card, or on a breakable holographic tamper-evident seal inside the inner foam packaging.
   - External packaging displays only product SKU and batch identifiers, never the claimable serial code.
2. **12-Character Segmented High-Entropy Serials**:
   - Box codes follow the format `PV-XXXX-YYYY-ZZ` (12 alphanumeric characters excluding ambiguous glyphs `O`, `0`, `I`, `1`).
   - Entropy space: 16 hex/alphanumeric characters yield over $1.6 \times 10^7$ combinations per batch prefix, rendering random guessing mathematically unfeasible.
3. **Dual Modality (Optical QR + Manual Alphanumeric)**:
   - Codes are encoded as high-contrast dynamic QR codes linking to `https://{domain}/?code=PV-XXXX-YYYY-ZZ`, allowing immediate mobile scanning via camera.
   - A manual uppercase entry field is provided for collectors who prefer entering alphanumeric characters directly.
4. **Cryptographic Verification Signatures**:
   - Each box code is cryptographically hashed at the time of factory minting using HMAC-SHA256:
     $$\text{Verification Hash} = \text{SHA-256}(\text{Code} \parallel \text{Batch Number} \parallel \text{Factory Secret Salt})$$
   - This signature is stored immutably in the factory cleanroom database. Even if a counterfeiter manufactures an identical physical box, they cannot produce a valid verification hash recognized by the ledger.

---

## 2. Anti-Fraud & Attack Mitigation Strategies

### A. Duplicate Claims & Double-Spend Defense (Re-Packaging Fraud)
- **Threat Vector**: A malicious buyer purchases a genuine item, opens the box, claims the loyalty points, carefully re-seals or re-shrinkwraps the box, and returns it to a retailer or resells it online as "brand new."
- **Mitigation**:
  - The verification engine treats code claiming as an **atomic single-use transaction**.
  - Database constraint: Status defaults to `UNCLAIMED`. Upon first successful verification, status transitions atomically to `CLAIMED` with `claimed_by_id`, `claimed_at`, and `claim_ip` logged.
  - If a code with status `CLAIMED` is submitted again:
    1. The claim is immediately **rejected**. Zero points are minted.
    2. An audit log event `VERIFY_DOUBLE_SPEND` is logged with severity `WARNING`, recording the attacker's IP, user-agent, and attempted timestamp.
    3. The UI surfaces an Amber Alert detailing the original registration date and masked claimant identity (`jul***@vance-atelier.com`), warning the customer that the product may be a returned or tampered unit.
    4. A direct 1-click button allows the buyer to file a **Retail Tampering Report** with factory quality control.

### B. Brute-Force & Automated Sequential Guessing
- **Threat Vector**: Automated bots scanning or querying serial variants (`PV-CHRO-0001`, `PV-CHRO-0002`, etc.) to steal points without purchasing physical goods.
- **Mitigation**:
  - **In-Memory Sliding-Window Rate Limiter**: Every IP address is restricted to a maximum of **15 verification requests per 60-second window**. Exceeding this limit triggers an immediate `HTTP 429 Too Many Requests` and logs a `RATE_LIMIT_TRIGGERED` audit event with `CRITICAL` severity.
  - **Consecutive Failure Exponential Watch**: If an IP records 4 consecutive invalid/non-existent code submissions, the system flags the IP as an active brute-force attacker, raising the security threat score on the factory owner's live monitor.

### C. Stolen Cartons & Recalled Inventory
- **Threat Vector**: A freight shipment or warehouse carton is stolen before retail distribution.
- **Mitigation**:
  - Box codes support explicit state management: `UNCLAIMED`, `CLAIMED`, `REVOKED`, and `SUSPECT`.
  - The factory administrator can revoke an entire batch or specific carton serials in one command.
  - If a buyer attempts to verify a revoked code, the system returns `REVOKED`, informing them that the inventory was recalled or reported stolen, and alerts factory security.

---

## 3. Loyalty Tier Thresholds & Multiplier Compounding

The client’s primary objective is to increase customer lifetime loyalty for high-margin physical goods. The tier architecture is designed around compounding points multipliers that incentivize buyers to purchase higher-tier goods and maintain their collection.

| Tier Name | Lifetime Points Required | Multiplier Applied | Collector Privileges & Unlocks |
| :--- | :--- | :--- | :--- |
| **Quartz** | 0 – 999 pts | **1.0x** (Base) | Digital Certificate of Authenticity, 1-Year Standard Factory Warranty. |
| **Sapphire** | 1,000 – 2,999 pts | **1.1x** (+10%) | Priority packaging dispatch, custom laser engraving eligibility. |
| **Amethyst** | 3,000 – 6,999 pts | **1.25x** (+25%) | 3-Year Extended Factory Warranty, Hand-Burnished Leather Goods access. |
| **Obsidian** | 7,000 – 14,999 pts | **1.5x** (+50%) | 5-Year Cleanroom Restoration & Re-Polish cover, complimentary cables. |
| **Prism Sovereign** | 15,000+ pts | **2.0x** (+100%) | Numbered Master Vault Presentation Cases (1 of 50), Direct Foundry Artisan Liaison. |

### Mathematical Multiplier Logic
When a collector verifies a product box, points are calculated using their current tier multiplier:
$$\text{Points Awarded} = \lfloor \text{Batch Base Points} \times \text{Tier Multiplier} \rfloor$$
*Example*: An Amethyst collector verifying an Aura Pro Headset (2,500 base points) receives:
$$2500 \times 1.25 = 3,125 \text{ Prism Points}$$

---

## 4. Factory Admin PIN & Command Center Security

### Administrative Access Control
1. **Factory Owner Command Center (`/admin`)**:
   - Access to batch code generation, label printing, customer fulfillment logs, and security incident streams is protected by a dedicated **Admin Security PIN** (default: `8821`, configurable via `.env`).
   - The backend validates the PIN via `POST /api/admin/verify-pin` before minting or modifying production runs.
2. **Session Persistence**:
   - Once validated, the administrative session token is held in `sessionStorage` to prevent unauthorized physical access at factory packaging terminals if left unattended.
3. **Label Printing Separation**:
   - Packaging QR label generation is handled strictly server-side using cryptographic salts, preventing client-side forgery of printable sticker sheets.
