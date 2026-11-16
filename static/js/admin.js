/**
 * PRISM VAULT // Factory Loyalty & Authenticity Rewards
 * Factory Owner Command Center, Batch Minting, Label Printing & Anti-Fraud Monitor
 */

const adminState = {
  stats: null,
  batches: [],
  redemptions: [],
  auditLogs: [],
  selectedBatchForPrint: null,
  charts: {
    velocity: null,
    tier: null,
    batch: null
  }
};

// --- Fetch Dashboard Stats & Update UI ---
async function fetchAdminDashboard() {
  try {
    const res = await fetch('/api/admin/dashboard');
    if (res.ok) {
      adminState.stats = await res.json();
      updateMetricCards(adminState.stats);
      renderCharts(adminState.stats);
      renderRecentAuditTable(adminState.stats.recent_verifications);
    }
  } catch (err) {
    console.error('Error fetching admin dashboard:', err);
  }
}

function updateMetricCards(data) {
  const elTotalBoxes = document.getElementById('statTotalBoxes');
  const elVerifiedBoxes = document.getElementById('statVerifiedBoxes');
  const elVerifyRate = document.getElementById('statVerifyRate');
  const elPointsMinted = document.getElementById('statPointsMinted');
  const elPointsCirculating = document.getElementById('statPointsCirculating');
  const elFraudAlerts = document.getElementById('statFraudAlerts');

  if (elTotalBoxes) elTotalBoxes.textContent = data.total_boxes_manufactured.toLocaleString();
  if (elVerifiedBoxes) elVerifiedBoxes.textContent = data.total_verified_boxes.toLocaleString();
  if (elVerifyRate) elVerifyRate.textContent = `${data.verification_rate_percent}% Authenticated`;
  if (elPointsMinted) elPointsMinted.textContent = data.total_points_minted.toLocaleString();
  if (elPointsCirculating) elPointsCirculating.textContent = `${data.points_in_circulation.toLocaleString()} Circulating`;
  if (elFraudAlerts) elFraudAlerts.textContent = data.active_fraud_alerts;
}

// --- Chart.js Rendering ---
function renderCharts(data) {
  if (typeof Chart === 'undefined') return;

  // Chart Global Settings for Crystal Dark Mode
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.font.family = "'Plus Jakarta Sans', sans-serif";

  // 1. Verification Velocity Trend Chart
  const ctxVelocity = document.getElementById('velocityChart');
  if (ctxVelocity) {
    if (adminState.charts.velocity) adminState.charts.velocity.destroy();

    const gradient = ctxVelocity.getContext('2d').createLinearGradient(0, 0, 0, 240);
    gradient.addColorStop(0, 'rgba(56, 189, 248, 0.4)');
    gradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

    adminState.charts.velocity = new Chart(ctxVelocity, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun (Today)'],
        datasets: [{
          label: 'Box Verifications',
          data: [4, 7, 3, 8, 12, 18, 15],
          borderColor: '#38bdf8',
          borderWidth: 2.5,
          backgroundColor: gradient,
          fill: true,
          tension: 0.38,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#38bdf8',
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0d121c',
            borderColor: 'rgba(255, 255, 255, 0.15)',
            borderWidth: 1,
            titleColor: '#ffffff',
            bodyColor: '#38bdf8',
            padding: 10
          }
        },
        scales: {
          x: { grid: { color: 'rgba(255, 255, 255, 0.04)' } },
          y: { grid: { color: 'rgba(255, 255, 255, 0.04)' }, beginAtZero: true }
        }
      }
    });
  }

  // 2. Customer Tier Distribution Doughnut Chart
  const ctxTier = document.getElementById('tierChart');
  if (ctxTier) {
    if (adminState.charts.tier) adminState.charts.tier.destroy();

    const tierData = data.tier_distribution || {};
    const labels = Object.keys(tierData);
    const values = Object.values(tierData);

    adminState.charts.tier = new Chart(ctxTier, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: values.length ? values : [1, 1, 1, 1, 1],
          backgroundColor: [
            '#38bdf8', // Quartz
            '#3b82f6', // Sapphire
            '#a855f7', // Amethyst
            '#f59e0b', // Obsidian
            '#ec4899'  // Prism Sovereign
          ],
          borderColor: '#0d121c',
          borderWidth: 3,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: { boxWidth: 12, padding: 12, font: { size: 11 } }
          }
        },
        cutout: '72%'
      }
    });
  }
}

// --- Batches Management ---
async function fetchBatches() {
  try {
    const res = await fetch('/api/admin/batches');
    if (res.ok) {
      adminState.batches = await res.json();
      renderBatchesTable();
    }
  } catch (err) {
    console.error('Error fetching batches:', err);
  }
}

function renderBatchesTable() {
  const tbody = document.getElementById('batchesTableBody');
  if (!tbody) return;

  if (adminState.batches.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: #64748b;">
          No manufacturing batches found. Click "Mint New Batch" to generate factory codes.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = adminState.batches.map(b => {
    const claimRate = b.total_units > 0 ? Math.round((b.claimed_units / b.total_units) * 100) : 0;
    const dateStr = new Date(b.created_at).toLocaleDateString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric'
    });

    return `
      <tr>
        <td>
          <span class="code-badge">${escapeHtml(b.batch_number)}</span>
        </td>
        <td>
          <div style="font-weight: 600; color: #ffffff;">${escapeHtml(b.product_name)}</div>
          <div style="font-size: 0.72rem; color: #64748b; font-family: var(--font-mono);">${escapeHtml(b.product_sku)}</div>
        </td>
        <td>
          <div style="font-weight: 600; color: #e2e8f0;">${b.claimed_units} / ${b.total_units} units</div>
          <div style="font-size: 0.72rem; color: #38bdf8;">${claimRate}% claimed</div>
        </td>
        <td>
          <span style="font-family: var(--font-mono); color: #fbbf24; font-weight: 600;">
            ${b.points_per_box.toLocaleString()} pts
          </span>
        </td>
        <td>
          <div style="font-size: 0.8rem; color: #cbd5e1;">${escapeHtml(b.facility_location)}</div>
          <div style="font-size: 0.72rem; color: #64748b;">${escapeHtml(b.inspector_id)}</div>
        </td>
        <td>${dateStr}</td>
        <td>
          <button class="btn-crystal btn-crystal-primary" style="padding: 0.4rem 0.85rem; font-size: 0.78rem;"
                  onclick="openPrintLabelsModal(${b.id})">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/>
            </svg>
            Print Box QR Labels
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// --- Batch Minting Form Submission ---
async function handleBatchMintSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('mintBatchSubmitBtn');
  if (btn) btn.disabled = true;

  const payload = {
    product_name: document.getElementById('mintProdName').value.trim(),
    product_sku: document.getElementById('mintProdSku').value.trim(),
    quantity: parseInt(document.getElementById('mintQuantity').value, 10),
    points_per_box: parseInt(document.getElementById('mintPointsPerBox').value, 10),
    facility_location: document.getElementById('mintFacility').value.trim(),
    inspector_id: document.getElementById('mintInspector').value.trim(),
    notes: document.getElementById('mintNotes').value.trim()
  };

  try {
    const res = await fetch('/api/admin/batches', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      closeModal('mintBatchModal');
      await fetchBatches();
      await fetchAdminDashboard();
      openPrintLabelsModal(data.id);
    } else {
      alert(data.detail || 'Failed to mint batch');
    }
  } catch (err) {
    console.error('Batch mint error:', err);
    alert('Error minting batch codes');
  } finally {
    if (btn) btn.disabled = false;
  }
}

// --- Printable Box QR Label Sheet Modal ---
async function openPrintLabelsModal(batchId) {
  const modal = document.getElementById('printLabelsModal');
  const container = document.getElementById('printLabelsContainer');
  const title = document.getElementById('printModalBatchTitle');
  if (!modal || !container) return;

  container.innerHTML = `
    <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #94a3b8;">
      Generating high-DPI packaging QR labels with cryptographic signatures...
    </div>
  `;
  modal.classList.add('active');

  try {
    const res = await fetch(`/api/admin/batches/${batchId}/codes`);
    if (res.ok) {
      const data = await res.json();
      adminState.selectedBatchForPrint = data;
      if (title) {
        title.textContent = `${data.batch.batch_number} // ${data.batch.product_name}`;
      }

      container.innerHTML = data.codes.map(c => `
        <div class="printable-label-badge">
          <div class="label-factory-tag">PRISM VAULT // CERTIFIED GENUINE</div>
          <img src="${c.qr_data}" alt="Box QR" class="label-qr-img">
          <div class="label-code-str">${escapeHtml(c.code)}</div>
          <div class="label-product-meta">
            ${escapeHtml(data.batch.product_sku)} • ${data.batch.points_per_box} PTS
          </div>
          <div style="font-size: 0.58rem; color: #94a3b8; font-family: var(--font-mono); margin-top: 4px;">
            SEAL: ${c.verification_hash.substring(0, 16)}...
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Error fetching batch codes:', err);
    container.innerHTML = `<div style="color: #fb7185;">Error loading labels for printing.</div>`;
  }
}

// --- Anti-Fraud & Security Monitor Table ---
function renderRecentAuditTable(events) {
  const tbody = document.getElementById('auditLogsTableBody');
  if (!tbody) return;

  if (!events || events.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; padding: 2rem; color: #64748b;">
          Zero anomaly alerts recorded. Cleanroom operational security nominal.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = events.map(e => {
    let sevBadge = '';
    if (e.severity === 'CRITICAL') {
      sevBadge = `<span style="background: rgba(244,63,94,0.2); color: #fb7185; border: 1px solid rgba(244,63,94,0.4); padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 700; font-size: 0.7rem;">CRITICAL</span>`;
    } else if (e.severity === 'WARNING') {
      sevBadge = `<span style="background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 700; font-size: 0.7rem;">WARNING</span>`;
    } else {
      sevBadge = `<span style="background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); padding: 0.2rem 0.5rem; border-radius: 6px; font-weight: 700; font-size: 0.7rem;">INFO</span>`;
    }

    const detailsStr = typeof e.details === 'object' ? JSON.stringify(e.details) : e.details || '—';

    return `
      <tr>
        <td>${sevBadge}</td>
        <td>
          <span style="font-family: var(--font-mono); font-size: 0.78rem; font-weight: 600; color: #f1f5f9;">
            ${escapeHtml(e.event_type)}
          </span>
        </td>
        <td>
          <span class="code-badge">${escapeHtml(e.box_code || '—')}</span>
        </td>
        <td>
          <span style="font-family: var(--font-mono); font-size: 0.76rem; color: #94a3b8;">
            ${escapeHtml(e.ip_address || '—')}
          </span>
        </td>
        <td>
          <div style="font-size: 0.74rem; color: #94a3b8; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${escapeHtml(detailsStr)}
          </div>
        </td>
        <td style="font-size: 0.75rem; color: #64748b;">${escapeHtml(e.created_at)}</td>
      </tr>
    `;
  }).join('');
}

// --- Reward Fulfillment Management ---
async function fetchRedemptions() {
  try {
    const res = await fetch('/api/admin/redemptions');
    if (res.ok) {
      adminState.redemptions = await res.json();
      renderRedemptionsTable();
    }
  } catch (err) {
    console.error('Error fetching redemptions:', err);
  }
}

function renderRedemptionsTable() {
  const tbody = document.getElementById('redemptionsTableBody');
  if (!tbody) return;

  if (adminState.redemptions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 2rem; color: #64748b;">
          No pending reward redemptions.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = adminState.redemptions.map(r => {
    return `
      <tr>
        <td>
          <span class="code-badge">${escapeHtml(r.redemption_code)}</span>
        </td>
        <td>
          <div style="font-weight: 600; color: #ffffff;">${escapeHtml(r.reward_title)}</div>
          <div style="font-size: 0.72rem; color: #38bdf8;">${r.points_spent.toLocaleString()} pts spent</div>
        </td>
        <td>
          <div style="font-weight: 600; color: #e2e8f0;">${escapeHtml(r.recipient_name)}</div>
          <div style="font-size: 0.72rem; color: #64748b;">${escapeHtml(r.customer_email)}</div>
        </td>
        <td>
          <div style="font-size: 0.78rem; color: #cbd5e1; max-width: 250px;">
            ${escapeHtml(r.shipping_address)}
          </div>
        </td>
        <td>
          <select onchange="updateFulfillmentStatus(${r.id}, this.value)" 
                  style="background: #0d121c; border: 1px solid rgba(255,255,255,0.15); color: #ffffff; padding: 0.35rem 0.6rem; border-radius: 8px; font-size: 0.78rem;">
            <option value="PENDING_SHIPMENT" ${r.status === 'PENDING_SHIPMENT' ? 'selected' : ''}>Pending Shipment</option>
            <option value="IN_PRODUCTION" ${r.status === 'IN_PRODUCTION' ? 'selected' : ''}>In Production</option>
            <option value="DISPATCHED" ${r.status === 'DISPATCHED' ? 'selected' : ''}>Dispatched</option>
            <option value="COMPLETED" ${r.status === 'COMPLETED' ? 'selected' : ''}>Completed</option>
          </select>
        </td>
        <td>
          <input type="text" placeholder="Tracking #" value="${escapeHtml(r.tracking_number || '')}"
                 onblur="updateFulfillmentTracking(${r.id}, this.value)"
                 style="background: #0d121c; border: 1px solid rgba(255,255,255,0.15); color: #ffffff; padding: 0.35rem 0.6rem; border-radius: 8px; font-size: 0.78rem; width: 140px;">
        </td>
      </tr>
    `;
  }).join('');
}

async function updateFulfillmentStatus(id, newStatus) {
  try {
    await fetch(`/api/admin/redemptions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
  } catch (err) {
    console.error('Failed to update status:', err);
  }
}

async function updateFulfillmentTracking(id, trackingNum) {
  try {
    const item = adminState.redemptions.find(r => r.id === id);
    const currStatus = item ? item.status : 'DISPATCHED';

    await fetch(`/api/admin/redemptions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: currStatus,
        tracking_number: trackingNum.trim()
      })
    });
  } catch (err) {
    console.error('Failed to update tracking:', err);
  }
}

// --- Database Reset Demo Helper ---
async function resetDemoData() {
  if (!confirm('Reset factory database to fresh pristine seed state? This will re-mint initial test batches and demo collectors.')) {
    return;
  }

  try {
    const res = await fetch('/api/admin/reset-demo', { method: 'POST' });
    if (res.ok) {
      alert('Factory cleanroom ledger reset to pristine seed state.');
      await fetchAdminDashboard();
      await fetchBatches();
      await fetchRedemptions();
    }
  } catch (err) {
    console.error('Reset error:', err);
  }
}

// --- Modals ---
function openMintBatchModal() {
  const modal = document.getElementById('mintBatchModal');
  if (modal) modal.classList.add('active');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('active');
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// --- DOM Load Event ---
document.addEventListener('DOMContentLoaded', async () => {
  await fetchAdminDashboard();
  await fetchBatches();
  await fetchRedemptions();

  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('active');
    });
  });
});
