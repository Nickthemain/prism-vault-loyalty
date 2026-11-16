/**
 * PRISM VAULT // Factory Loyalty & Authenticity Rewards
 * Customer Portal, 3D Card Physics, Verification Ceremony & Reward Dispensary
 */

// Global State
const state = {
  currentCustomer: null,
  allCustomers: [],
  rewards: [],
  verifiedBoxes: [],
  redemptions: [],
  audioEnabled: true
};

// --- Web Audio Synthesizer (Zero External Asset Dependency) ---
const LuxuryAudio = {
  ctx: null,
  init() {
    if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
  },
  playChime() {
    if (!state.audioEnabled) return;
    try {
      this.init();
      if (!this.ctx) return;
      if (this.ctx.state === 'suspended') this.ctx.resume();

      const now = this.ctx.currentTime;
      // High glass crystal harmonics
      [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, now + idx * 0.08);

        gain.gain.setValueAtTime(0.001, now + idx * 0.08);
        gain.gain.exponentialRampToValueAtTime(0.15, now + idx * 0.08 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.08 + 0.9);

        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now + idx * 0.08);
        osc.stop(now + idx * 0.08 + 1.0);
      });
    } catch (e) {
      console.warn('Audio play error:', e);
    }
  },
  playWarning() {
    if (!state.audioEnabled) return;
    try {
      this.init();
      if (!this.ctx) return;
      if (this.ctx.state === 'suspended') this.ctx.resume();

      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(160, now);
      osc.frequency.exponentialRampToValueAtTime(110, now + 0.35);

      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.45);
    } catch (e) {
      console.warn('Audio error:', e);
    }
  }
};

// --- 3D Holographic Membership Card Physics ---
function init3DCardPhysics() {
  const card = document.getElementById('membershipCard3D');
  const stage = document.querySelector('.card-perspective-stage');
  const glare = document.getElementById('cardGlare');
  const foil = document.getElementById('cardFoil');

  if (!card || !stage) return;

  let isHovered = false;

  stage.addEventListener('mouseenter', () => {
    isHovered = true;
    card.style.transition = 'transform 0.1s ease-out';
  });

  stage.addEventListener('mousemove', (e) => {
    if (!isHovered) return;

    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;

    // Calculate rotation limits (-14 to +14 deg)
    const rotateX = ((centerY - y) / centerY) * 14;
    const rotateY = ((x - centerX) / centerX) * 14;

    card.style.transform = `perspective(1200px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.025, 1.025, 1.025)`;

    // Calculate glare position
    const glareX = (x / rect.width) * 100;
    const glareY = (y / rect.height) * 100;
    if (glare) {
      glare.style.background = `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255, 255, 255, 0.45) 0%, transparent 65%)`;
    }

    // Foil shift
    if (foil) {
      foil.style.backgroundPosition = `${glareX * 1.5}% ${glareY * 1.5}%`;
    }
  });

  stage.addEventListener('mouseleave', () => {
    isHovered = false;
    card.style.transition = 'transform 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
    card.style.transform = 'perspective(1200px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
  });
}

// --- Customer Profile Management ---
async function fetchCustomers() {
  try {
    const res = await fetch('/api/customers');
    if (res.ok) {
      state.allCustomers = await res.json();
      populateCustomerSwitcher();
    }
  } catch (err) {
    console.error('Failed to load customers:', err);
  }
}

function populateCustomerSwitcher() {
  const dropdown = document.getElementById('customerSwitcherDropdown');
  if (!dropdown) return;

  dropdown.innerHTML = state.allCustomers.map(c => `
    <div class="switcher-item ${state.currentCustomer && state.currentCustomer.id === c.id ? 'active' : ''}" 
         onclick="switchCustomer(${c.id})">
      <div class="switcher-avatar">${c.name.charAt(0)}</div>
      <div class="switcher-info">
        <div class="switcher-name">${c.name}</div>
        <div class="switcher-meta">${c.tier} • ${c.points_balance.toLocaleString()} pts</div>
      </div>
    </div>
  `).join('') + `
    <div class="switcher-divider"></div>
    <div class="switcher-item" onclick="openNewCustomerModal()">
      <div class="switcher-avatar add-new">+</div>
      <div class="switcher-info">
        <div class="switcher-name">Register New Collector</div>
        <div class="switcher-meta">Instant Vault Membership</div>
      </div>
    </div>
  `;
}

async function loadActiveCustomer(customerIdOrEmail) {
  try {
    let url = '/api/customer/profile';
    if (typeof customerIdOrEmail === 'string' && customerIdOrEmail.includes('@')) {
      url += `?email=${encodeURIComponent(customerIdOrEmail)}`;
    } else if (customerIdOrEmail) {
      url = `/api/customer/${customerIdOrEmail}/history`;
    }

    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      // data could be Customer or history payload
      state.currentCustomer = data.customer || data;
      updateCustomerUI();
      loadCustomerHistory(state.currentCustomer.id);
      loadRewards();
    }
  } catch (err) {
    console.error('Error loading customer:', err);
  }
}

function switchCustomer(id) {
  const cust = state.allCustomers.find(c => c.id === id);
  if (cust) {
    state.currentCustomer = cust;
    updateCustomerUI();
    loadCustomerHistory(cust.id);
    loadRewards();
    closeSwitcherDropdown();
  }
}

function updateCustomerUI() {
  if (!state.currentCustomer) return;
  const c = state.currentCustomer;

  // Top nav pill
  const nameEl = document.getElementById('navProfileName');
  const tierEl = document.getElementById('navProfileTier');
  const avatarEl = document.getElementById('navProfileAvatar');
  if (nameEl) nameEl.textContent = c.name;
  if (tierEl) tierEl.textContent = `${c.tier} Tier`;
  if (avatarEl) avatarEl.textContent = c.name.charAt(0).toUpperCase();

  // 3D Card
  const cardName = document.getElementById('cardCollectorName');
  const cardMemId = document.getElementById('cardMemberId');
  const cardTier = document.getElementById('cardTierBadge');
  const cardPts = document.getElementById('cardPointsValue');
  const cardEl = document.getElementById('membershipCard3D');

  if (cardName) cardName.textContent = c.name;
  if (cardMemId) cardMemId.textContent = c.member_id;
  if (cardPts) animatePointsCounter(cardPts, c.points_balance);

  if (cardTier) {
    cardTier.textContent = c.tier;
    cardTier.className = 'card-tier-badge';
    const tierSlug = c.tier.toLowerCase().replace(' ', '-');
    cardTier.classList.add(`tier-${tierSlug}`);
  }

  // Update card ambient lighting
  if (cardEl) {
    cardEl.setAttribute('data-tier', c.tier);
  }

  // Update Tier timeline highlighting
  document.querySelectorAll('.tier-pillar-card').forEach(card => {
    const tName = card.getAttribute('data-tier-name');
    if (tName && tName.toLowerCase() === c.tier.toLowerCase()) {
      card.classList.add('active-user-tier');
    } else {
      card.classList.remove('active-user-tier');
    }
  });

  // Re-populate switcher
  populateCustomerSwitcher();
}

function animatePointsCounter(element, targetValue) {
  const startValue = parseInt(element.getAttribute('data-current') || '0', 10);
  element.setAttribute('data-current', targetValue);

  const duration = 800;
  const startTime = performance.now();

  function update(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out expo
    const ease = 1 - Math.pow(2, -10 * progress);
    const current = Math.floor(startValue + (targetValue - startValue) * ease);
    element.innerHTML = `${current.toLocaleString()} <span class="card-points-unit">PTS</span>`;

    if (progress < 1) {
      requestAnimationFrame(update);
    } else {
      element.innerHTML = `${targetValue.toLocaleString()} <span class="card-points-unit">PTS</span>`;
    }
  }

  requestAnimationFrame(update);
}

// --- Customer History & Ledger ---
async function loadCustomerHistory(customerId) {
  try {
    const res = await fetch(`/api/customer/${customerId}/history`);
    if (res.ok) {
      const data = await res.json();
      state.verifiedBoxes = data.verified_boxes || [];
      state.redemptions = data.redemptions || [];
      renderHistoryTable();
    }
  } catch (err) {
    console.error('Error fetching history:', err);
  }
}

function renderHistoryTable() {
  const tbody = document.getElementById('historyTableBody');
  if (!tbody) return;

  if (state.verifiedBoxes.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; padding: 2.5rem; color: #64748b;">
          No physical box serials verified yet. Enter a code above to certify your factory goods.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = state.verifiedBoxes.map(b => {
    const dateStr = b.claimed_at ? new Date(b.claimed_at).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric'
    }) : '—';

    return `
      <tr>
        <td>
          <span class="code-badge">${escapeHtml(b.code)}</span>
        </td>
        <td>
          <div style="font-weight: 600; color: #f1f5f9;">${escapeHtml(b.product_name)}</div>
          <div style="font-size: 0.72rem; color: #64748b; font-family: var(--font-mono);">${escapeHtml(b.product_sku)}</div>
        </td>
        <td>
          <span style="font-family: var(--font-mono); font-size: 0.78rem; color: #94a3b8;">${escapeHtml(b.batch_number)}</span>
        </td>
        <td>
          <span style="font-weight: 700; color: #38bdf8;">+${b.points_earned.toLocaleString()} pts</span>
        </td>
        <td>${dateStr}</td>
        <td>
          <button class="btn-crystal btn-crystal-secondary" style="padding: 0.35rem 0.75rem; font-size: 0.75rem;"
                  onclick="viewCertificate('${escapeHtml(b.code)}')">
            <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            Certificate
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// --- Box Code Verification Flow ---
async function verifyBoxCode(codeToVerify = null) {
  const codeInput = document.getElementById('boxCodeInput');
  const code = (codeToVerify || (codeInput ? codeInput.value : '')).trim().toUpperCase();

  if (!code) {
    showChamberError('Please enter a box serial code from the package inner seal.');
    return;
  }

  const hud = document.getElementById('verificationResultHud');
  const btn = document.getElementById('verifySubmitBtn');

  // Disable button and show scanning animation
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="spin-animation" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
        <path d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      Scanning Optical Ledger...
    `;
  }

  try {
    const payload = {
      code: code,
      customer_email: state.currentCustomer ? state.currentCustomer.email : null,
      member_id: state.currentCustomer ? state.currentCustomer.member_id : null
    };

    const res = await fetch('/api/verify-code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    renderVerificationResultHUD(data);

    if (data.success) {
      LuxuryAudio.playChime();
      triggerConfetti();

      // Update current customer with fresh data
      if (data.customer) {
        state.currentCustomer = data.customer;
        updateCustomerUI();
      }

      if (state.currentCustomer) {
        loadCustomerHistory(state.currentCustomer.id);
      }
      loadRewards();
    } else {
      LuxuryAudio.playWarning();
    }
  } catch (err) {
    console.error('Verification error:', err);
    showChamberError('Network or verification service error. Please try again.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        Verify Authenticity & Claim
      `;
    }
  }
}

function renderVerificationResultHUD(res) {
  const hud = document.getElementById('verificationResultHud');
  if (!hud) return;

  hud.style.display = 'block';
  hud.className = 'verification-result-hud';

  if (res.status === 'VERIFIED_GENUINE') {
    hud.classList.add('result-genuine');
    hud.innerHTML = `
      <div class="hud-header">
        <div class="hud-icon hud-icon-genuine">
          <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <div class="hud-title-col">
          <span class="hud-status-badge" style="color: #34d399;">100% Certified Genuine Factory Origin</span>
          <h4 class="hud-main-heading">${escapeHtml(res.batch ? res.batch.product_name : 'Factory Sealed Goods')}</h4>
        </div>
      </div>
      <p class="hud-body-text">${escapeHtml(res.message)}</p>
      
      <div class="hud-meta-grid">
        <div class="meta-field">
          <span class="meta-label">Serial Number</span>
          <span class="meta-val">${escapeHtml(res.box_code)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Batch ID</span>
          <span class="meta-val">${escapeHtml(res.batch ? res.batch.batch_number : '—')}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Points Awarded</span>
          <span class="meta-val" style="color: #38bdf8;">+${res.points_awarded.toLocaleString()} (${res.multiplier_applied}x tier)</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Cleanroom Facility</span>
          <span class="meta-val">${escapeHtml(res.batch ? res.batch.facility_location : 'Foundry Alpha-7')}</span>
        </div>
      </div>

      <div class="hud-actions">
        <button class="btn-crystal btn-crystal-primary" onclick="viewCertificate('${escapeHtml(res.box_code)}')">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          View Certificate of Authenticity
        </button>
        <button class="btn-crystal btn-crystal-secondary" onclick="dismissResultHUD()">
          Dismiss
        </button>
      </div>
    `;
  } else if (res.status === 'ALREADY_CLAIMED') {
    hud.classList.add('result-fraud');
    hud.innerHTML = `
      <div class="hud-header">
        <div class="hud-icon hud-icon-fraud">
          <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
        </div>
        <div class="hud-title-col">
          <span class="hud-status-badge" style="color: #fbbf24;">Authenticity Warning // Double-Claim Detected</span>
          <h4 class="hud-main-heading">Code Already Registered in Factory Ledger</h4>
        </div>
      </div>
      <p class="hud-body-text">${escapeHtml(res.message)}</p>

      <div class="hud-meta-grid">
        <div class="meta-field">
          <span class="meta-label">Serial Number</span>
          <span class="meta-val">${escapeHtml(res.box_code)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Initial Claim Date</span>
          <span class="meta-val">${res.claimed_at ? new Date(res.claimed_at).toLocaleDateString() : 'Previously'}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Status</span>
          <span class="meta-val" style="color: #fbbf24;">REPLAY_PREVENTED</span>
        </div>
      </div>

      <div class="hud-actions">
        <button class="btn-crystal btn-crystal-secondary" onclick="reportTampering('${escapeHtml(res.box_code)}')">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Report Retail Tampering to Quality Assurance
        </button>
        <button class="btn-crystal btn-crystal-secondary" onclick="dismissResultHUD()">
          Dismiss
        </button>
      </div>
    `;
  } else {
    // INVALID_CODE or REVOKED
    hud.classList.add('result-counterfeit');
    hud.innerHTML = `
      <div class="hud-header">
        <div class="hud-icon hud-icon-counterfeit">
          <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
          </svg>
        </div>
        <div class="hud-title-col">
          <span class="hud-status-badge" style="color: #fb7185;">Security Alert // Cryptographic Mismatch</span>
          <h4 class="hud-main-heading">Unregistered Serial Code</h4>
        </div>
      </div>
      <p class="hud-body-text">${escapeHtml(res.message)}</p>

      <div class="hud-actions">
        <button class="btn-crystal btn-crystal-secondary" onclick="dismissResultHUD()">
          Try Another Serial
        </button>
      </div>
    `;
  }
}

function dismissResultHUD() {
  const hud = document.getElementById('verificationResultHud');
  if (hud) hud.style.display = 'none';
}

function showChamberError(msg) {
  const hud = document.getElementById('verificationResultHud');
  if (!hud) return;
  hud.style.display = 'block';
  hud.className = 'verification-result-hud result-counterfeit';
  hud.innerHTML = `
    <p class="hud-body-text" style="margin-bottom: 0.5rem; color: #fb7185;">${escapeHtml(msg)}</p>
  `;
}

// --- Rewards Catalog & Redemption ---
async function loadRewards() {
  try {
    const res = await fetch('/api/rewards');
    if (res.ok) {
      state.rewards = await res.json();
      renderRewardsCatalog();
    }
  } catch (err) {
    console.error('Error fetching rewards:', err);
  }
}

function renderRewardsCatalog() {
  const grid = document.getElementById('rewardsGrid');
  if (!grid) return;

  const userBalance = state.currentCustomer ? state.currentCustomer.points_balance : 0;
  const userTier = state.currentCustomer ? state.currentCustomer.tier : 'Quartz';

  const tierHierarchy = ['Quartz', 'Sapphire', 'Amethyst', 'Obsidian', 'Prism Sovereign'];
  const userTierRank = tierHierarchy.indexOf(userTier);

  grid.innerHTML = state.rewards.map(r => {
    const reqTierRank = tierHierarchy.indexOf(r.required_tier);
    const tierQualified = userTierRank >= reqTierRank;
    const pointsQualified = userBalance >= r.points_cost;
    const canRedeem = tierQualified && pointsQualified && r.stock_quantity > 0;

    let buttonHtml = '';
    if (canRedeem) {
      buttonHtml = `
        <button class="btn-crystal btn-crystal-gold" onclick="openRedeemModal(${r.id})">
          Redeem Reward
        </button>
      `;
    } else if (!tierQualified) {
      buttonHtml = `
        <button class="btn-crystal btn-crystal-secondary" disabled style="opacity: 0.6; cursor: not-allowed;">
          🔒 Requires ${r.required_tier} Tier
        </button>
      `;
    } else if (!pointsQualified) {
      const needed = r.points_cost - userBalance;
      buttonHtml = `
        <button class="btn-crystal btn-crystal-secondary" disabled style="opacity: 0.6; cursor: not-allowed;">
          Need ${needed.toLocaleString()} more pts
        </button>
      `;
    } else {
      buttonHtml = `
        <button class="btn-crystal btn-crystal-secondary" disabled style="opacity: 0.5;">
          Out of Stock
        </button>
      `;
    }

    return `
      <div class="crystal-card reward-card">
        <div class="reward-image-wrap">
          <img src="${r.image_url || 'https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&w=600&q=80'}" 
               alt="${escapeHtml(r.title)}" class="reward-img">
          ${r.badge_label ? `<span class="reward-badge-overlay">${escapeHtml(r.badge_label)}</span>` : ''}
          <span class="reward-tier-overlay">${r.required_tier}+</span>
        </div>
        <div class="reward-body">
          <div class="reward-title-group">
            <h4 class="reward-title">${escapeHtml(r.title)}</h4>
            <p class="reward-desc">${escapeHtml(r.description)}</p>
          </div>
          <div class="reward-footer">
            <div class="reward-cost-wrap">
              <span class="cost-label">Vault Points</span>
              <span class="cost-amount">${r.points_cost.toLocaleString()} <span>PTS</span></span>
            </div>
            ${buttonHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// --- Redemption Modal Handling ---
function openRedeemModal(rewardId) {
  const reward = state.rewards.find(r => r.id === rewardId);
  if (!reward || !state.currentCustomer) return;

  const modal = document.getElementById('redemptionModal');
  const body = document.getElementById('redemptionModalBody');
  if (!modal || !body) return;

  body.innerHTML = `
    <h3 style="font-family: var(--font-display); font-size: 1.5rem; color: #ffffff; margin-bottom: 0.5rem;">
      Confirm Reward Dispatch
    </h3>
    <p style="font-size: 0.88rem; color: #94a3b8; margin-bottom: 1.5rem;">
      You are redeeming <strong>${escapeHtml(reward.title)}</strong> for 
      <strong style="color: #38bdf8;">${reward.points_cost.toLocaleString()} Prism Points</strong>.
    </p>

    <form id="redemptionForm" onsubmit="submitRedemption(event, ${reward.id})">
      <div style="display: flex; flex-direction: column; gap: 1rem; margin-bottom: 1.5rem;">
        <div>
          <label style="display: block; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #94a3b8; margin-bottom: 0.35rem;">
            Recipient Collector Name
          </label>
          <input type="text" id="rdmRecipientName" required value="${escapeHtml(state.currentCustomer.name)}"
                 style="width: 100%; padding: 0.75rem 1rem; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; color: #ffffff; outline: none;">
        </div>

        <div>
          <label style="display: block; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #94a3b8; margin-bottom: 0.35rem;">
            Shipping Address (Street, City, Postal Code, Country)
          </label>
          <textarea id="rdmShippingAddress" required rows="3"
                    style="width: 100%; padding: 0.75rem 1rem; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; color: #ffffff; outline: none;">742 Evergreen Terrace, Suite 4B, Zurich, CH-8001</textarea>
        </div>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
        <button type="button" class="btn-crystal btn-crystal-secondary" onclick="closeModal('redemptionModal')">
          Cancel
        </button>
        <button type="submit" class="btn-crystal btn-crystal-gold" id="rdmConfirmBtn">
          Authorize & Deduct Points
        </button>
      </div>
    </form>
  `;

  modal.classList.add('active');
}

async function submitRedemption(e, rewardId) {
  e.preventDefault();
  const btn = document.getElementById('rdmConfirmBtn');
  const recipientName = (document.getElementById('rdmRecipientName').value || '').trim() || (state.currentCustomer ? state.currentCustomer.name : 'Valued Collector');
  const address = (document.getElementById('rdmShippingAddress').value || '').trim() || 'Foundry Cleanroom Vault, Zurich, Switzerland';

  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/redeem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        customer_id: state.currentCustomer ? state.currentCustomer.id : null,
        customer_email: state.currentCustomer ? state.currentCustomer.email : null,
        reward_id: rewardId,
        recipient_name: recipientName,
        shipping_address: address
      })
    });

    const data = await res.json();
    if (res.ok) {
      LuxuryAudio.playChime();
      triggerConfetti();

      // Update local points
      state.currentCustomer.points_balance = data.new_points_balance;
      updateCustomerUI();
      loadRewards();
      loadCustomerHistory(state.currentCustomer.id);

      // Show voucher confirmation
      const body = document.getElementById('redemptionModalBody');
      body.innerHTML = `
        <div style="text-align: center; padding: 1rem 0;">
          <div style="width: 56px; height: 56px; border-radius: 50%; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.25rem;">
            <svg width="28" height="28" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <h3 style="font-family: var(--font-display); font-size: 1.5rem; color: #ffffff; margin-bottom: 0.5rem;">
            Fulfillment Order Placed!
          </h3>
          <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 1.5rem;">
            Your redemption code is:
          </p>
          <div style="display: inline-block; font-family: var(--font-mono); font-size: 1.25rem; font-weight: 700; color: #fbbf24; background: rgba(0,0,0,0.5); padding: 0.6rem 1.4rem; border-radius: 8px; border: 1px dashed rgba(245,158,11,0.4); margin-bottom: 1.5rem;">
            ${escapeHtml(data.redemption_code)}
          </div>
          <p style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 1.5rem;">
            Factory dispatch team will prepare your artisan piece and notify tracking status.
          </p>
          <button class="btn-crystal btn-crystal-primary" onclick="closeModal('redemptionModal')">
            Done
          </button>
        </div>
      `;
    } else {
      alert(data.detail || 'Redemption failed');
      if (btn) btn.disabled = false;
    }
  } catch (err) {
    console.error('Redemption error:', err);
    alert('Failed to process redemption.');
    if (btn) btn.disabled = false;
  }
}

// --- Certificate of Authenticity Modal ---
async function viewCertificate(boxCode) {
  const modal = document.getElementById('certificateModal');
  const body = document.getElementById('certificateModalBody');
  if (!modal || !body) return;

  // Find box in history or find via API
  let box = state.verifiedBoxes.find(b => b.code.toUpperCase() === boxCode.toUpperCase());

  // If not in state, construct or fetch
  if (!box) {
    box = {
      code: boxCode,
      product_name: "Apex Precision Titanium Chrono Flask",
      product_sku: "APEX-FLASK-TI-01",
      batch_number: "BATCH-2026-CHRONO-A1",
      facility_location: "Aethelgard Precision Foundry, Cleanroom 7",
      inspector_id: "INSP-AL-902",
      verification_hash: "a4f89d023b81109cde892e8fa42091db876a3e1104e",
      claimed_at: new Date()
    };
  }

  body.innerHTML = `
    <div class="certificate-sheet">
      <div class="cert-header">
        <div class="cert-factory-logo">PRISM VAULT // CLEANROOM FOUNDRY</div>
        <h2 class="cert-title">Certificate of Authenticity</h2>
        <p style="font-size: 0.78rem; color: #94a3b8; letter-spacing: 0.05em; text-transform: uppercase;">
          Cryptographically Verified Physical Goods Asset
        </p>
      </div>

      <div class="cert-serial-highlight">
        SERIAL: ${escapeHtml(box.code)}
      </div>

      <div class="cert-details-grid">
        <div class="meta-field">
          <span class="meta-label">Product Designation</span>
          <span class="meta-val" style="color: #ffffff;">${escapeHtml(box.product_name)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Factory SKU</span>
          <span class="meta-val">${escapeHtml(box.product_sku)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Manufacturing Batch</span>
          <span class="meta-val">${escapeHtml(box.batch_number)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Foundry Cleanroom</span>
          <span class="meta-val">${escapeHtml(box.facility_location)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Certified Inspector</span>
          <span class="meta-val">${escapeHtml(box.inspector_id)}</span>
        </div>
        <div class="meta-field">
          <span class="meta-label">Verification Date</span>
          <span class="meta-val">${box.claimed_at ? new Date(box.claimed_at).toLocaleDateString() : 'Active'}</span>
        </div>
      </div>

      <div style="font-size: 0.7rem; color: #94a3b8; margin-bottom: 0.5rem; text-align: left;">
        SHA-256 Cleanroom Immutable Ledger Signature:
      </div>
      <div class="cert-hash-block">
        ${escapeHtml(box.verification_hash || 'SHA256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069')}
      </div>

      <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 2rem;">
        <button class="btn-crystal btn-crystal-primary" onclick="window.print()">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
          </svg>
          Print / Export Certificate
        </button>
        <button class="btn-crystal btn-crystal-secondary" onclick="closeModal('certificateModal')">
          Close
        </button>
      </div>
    </div>
  `;

  modal.classList.add('active');
}

// --- QR Camera Scanner Simulated Optical Chamber ---
function openCameraScannerModal() {
  const modal = document.getElementById('qrScannerModal');
  if (!modal) return;
  modal.classList.add('active');

  const scannerWindow = document.getElementById('qrScannerFeed');
  if (scannerWindow) {
    scannerWindow.innerHTML = `
      <div style="position: relative; width: 100%; height: 260px; background: #000000; border-radius: 12px; overflow: hidden; display: flex; align-items: center; justify-content: center;">
        <div style="position: absolute; inset: 0; background: radial-gradient(circle, rgba(56, 189, 248, 0.1) 0%, transparent 80%);"></div>
        <div style="width: 180px; height: 180px; border: 2px dashed rgba(56, 189, 248, 0.6); border-radius: 16px; position: relative;">
          <div style="position: absolute; top: 0; left: 0; right: 0; height: 2px; background: #38bdf8; box-shadow: 0 0 10px #38bdf8; animation: laserSweep 2s infinite alternate ease-in-out;"></div>
        </div>
        <p style="position: absolute; bottom: 15px; font-size: 0.78rem; color: #94a3b8; font-family: var(--font-mono);">
          Align box QR label within optics
        </p>
      </div>

      <div style="display: flex; gap: 0.75rem; margin-top: 1.25rem;">
        <button class="btn-crystal btn-crystal-primary" style="flex: 1;" onclick="simulateScanCode('PV-CHRO-77B2-04')">
          Simulate Scan (Unclaimed Flask)
        </button>
        <button class="btn-crystal btn-crystal-secondary" style="flex: 1;" onclick="simulateScanCode('PV-CHRO-991A-01')">
          Simulate Scan (Claimed Double-Spend)
        </button>
      </div>
    `;
  }
}

function simulateScanCode(code) {
  closeModal('qrScannerModal');
  const input = document.getElementById('boxCodeInput');
  if (input) input.value = code;
  verifyBoxCode(code);
}

// --- Report Retail Tampering Helper ---
function reportTampering(code) {
  alert(`Thank you for alerting factory quality control. A formal forensic incident report has been flagged for Serial #${code} to prevent retail counterfeit distribution.`);
}

// --- Confetti Animation Trigger ---
function triggerConfetti() {
  if (window.confetti) {
    window.confetti({
      particleCount: 90,
      spread: 70,
      origin: { y: 0.6 },
      colors: ['#38bdf8', '#a855f7', '#f59e0b', '#10b981', '#ffffff']
    });
  }
}

// --- Modal Helper Functions ---
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('active');
}

function openNewCustomerModal() {
  closeSwitcherDropdown();
  const modal = document.getElementById('newCustomerModal');
  if (modal) modal.classList.add('active');
}

async function handleNewCustomerSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('newCustName').value.trim();
  const email = document.getElementById('newCustEmail').value.trim();
  const phone = document.getElementById('newCustPhone').value.trim();

  if (!name || !email) return;

  try {
    const res = await fetch('/api/customers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, phone })
    });
    if (res.ok) {
      const newCust = await res.json();
      state.allCustomers.unshift(newCust);
      state.currentCustomer = newCust;
      closeModal('newCustomerModal');
      updateCustomerUI();
      loadCustomerHistory(newCust.id);
      loadRewards();
    }
  } catch (err) {
    console.error('Error creating customer:', err);
  }
}

function toggleSwitcherDropdown() {
  const dropdown = document.getElementById('customerSwitcherDropdown');
  if (dropdown) dropdown.classList.toggle('active');
}

function closeSwitcherDropdown() {
  const dropdown = document.getElementById('customerSwitcherDropdown');
  if (dropdown) dropdown.classList.remove('active');
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// --- Initialization on DOM Loaded ---
document.addEventListener('DOMContentLoaded', async () => {
  init3DCardPhysics();
  await fetchCustomers();

  // Check URL query parameters for initial code: ?code=PV-XXXX-YYYY
  const urlParams = new URLSearchParams(window.location.search);
  const initialCode = urlParams.get('code');
  if (initialCode) {
    const input = document.getElementById('boxCodeInput');
    if (input) input.value = initialCode;
  }

  // Load first customer or Julian Vance
  const defaultCust = state.allCustomers.find(c => c.name.includes('Julian')) || state.allCustomers[0];
  if (defaultCust) {
    state.currentCustomer = defaultCust;
    updateCustomerUI();
    loadCustomerHistory(defaultCust.id);
    loadRewards();
  }

  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('active');
    });
  });

  // Close switcher dropdown on outside click
  document.addEventListener('click', (e) => {
    const switcher = document.getElementById('navProfilePill');
    const dropdown = document.getElementById('customerSwitcherDropdown');
    if (switcher && dropdown && !switcher.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.remove('active');
    }
  });

  // Enter key in box code field triggers verification
  const codeInput = document.getElementById('boxCodeInput');
  if (codeInput) {
    codeInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        verifyBoxCode();
      }
    });
  }
});
