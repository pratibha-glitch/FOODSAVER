// SmartPlate AI - Main Application Orchestrator
const App = {
  activeTab: 'volunteer-feed',

  async init() {
    await Auth.init();
    await this.refreshMetricsBanner();
    this.switchTab('volunteer-feed');
    this.setupNotificationChecker();
  },

  switchTab(tabId) {
    this.activeTab = tabId;

    // Update tab bar buttons
    document.querySelectorAll('.tab-item').forEach(el => {
      if (el.getAttribute('data-tab') === tabId) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    // Update view panels
    document.querySelectorAll('.view-panel').forEach(panel => {
      if (panel.id === `view-${tabId}`) {
        panel.style.display = 'block';
      } else {
        panel.style.display = 'none';
      }
    });

    this.refreshCurrentView();
  },

  async refreshCurrentView() {
    if (this.activeTab === 'volunteer-feed') {
      await Volunteer.init();
    } else if (this.activeTab === 'staff-dashboard') {
      await Staff.init();
    } else if (this.activeTab === 'my-pickups') {
      await Volunteer.loadMyPickups();
    } else if (this.activeTab === 'admin-dashboard') {
      await Admin.init();
    }
  },

  async refreshMetricsBanner() {
    const res = await API.get('/api/admin/metrics');
    if (!res.success || !res.metrics) return;

    const m = res.metrics;
    const bannerPickups = document.getElementById('bannerPickups');
    const bannerActive = document.getElementById('bannerActive');
    const bannerVolunteers = document.getElementById('bannerVolunteers');
    const bannerCo2 = document.getElementById('bannerCo2');

    if (bannerPickups) bannerPickups.innerText = `${m.completed_pickups} Pickups`;
    if (bannerActive) bannerActive.innerText = `${m.active_available_listings} Available`;
    if (bannerVolunteers) bannerVolunteers.innerText = `${m.verified_volunteers_count} Active`;
    if (bannerCo2) bannerCo2.innerText = `${m.environmental_impact.co2_prevented_kg} kg CO₂ Diverted`;
  },

  // Modal Management
  openModal() {
    const modal = document.getElementById('appModal');
    if (modal) modal.style.display = 'flex';
  },

  closeModal() {
    const modal = document.getElementById('appModal');
    if (modal) modal.style.display = 'none';
  },

  async showListingDetails(listingId) {
    const res = await API.get(`/api/listings/${listingId}`);
    if (!res.success || !res.listing) {
      this.showToast(res.error || "Could not load listing details.", "danger");
      return;
    }

    const l = res.listing;
    const urg = l.urgency || { level: 'STANDARD', explanation: 'Operational collection window active.', minutes_left: 120 };
    const deadlineDate = new Date(l.operational_deadline);
    const deadlineStr = deadlineDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' (' + deadlineDate.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ')';
    const photoSrc = l.photo_filename ? `/static/uploads/${l.photo_filename}` : '/static/uploads/preset_dal_rice.jpg';
    const role = Auth.currentUser ? Auth.currentUser.role : 'public';
    const userId = Auth.currentUser ? Auth.currentUser.id : null;

    const modalContent = document.getElementById('modalContent');
    modalContent.innerHTML = `
      <div class="modal-header">
        <div>
          <h3 style="font-size: 1.15rem; color: var(--primary-dark);">${escapeHtml(l.food_name)}</h3>
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Category: ${l.category.replace('_', ' ')}</span>
        </div>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>

      <div style="border-radius: 8px; overflow: hidden; margin-bottom: 14px; position: relative; max-height: 200px; background: #000;">
        <img src="${photoSrc}" alt="${escapeHtml(l.food_name)}" style="width: 100%; height: 200px; object-fit: cover; display: block;" onerror="this.src='/static/uploads/preset_dal_rice.jpg'">
        <div style="position: absolute; top: 10px; left: 10px;">
          <span class="status-pill status-${l.status}">● ${l.status.toUpperCase()}</span>
        </div>
        <div style="position: absolute; bottom: 10px; right: 10px;">
          <span class="urgency-badge urgency-${urg.level.toLowerCase()}">
            ⏱️ ${urg.level} (${urg.minutes_left}m left)
          </span>
        </div>
      </div>

      <div class="grid-2" style="gap: 10px; font-size: 0.8rem; margin-bottom: 14px; background: var(--bg-muted); padding: 12px; border-radius: 8px;">
        <div>
          <span style="color: var(--text-muted); font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Quantity:</span><br>
          <strong>${l.quantity_value} ${l.quantity_unit}</strong> <span class="user-role-tag ${l.quantity_source === 'measured' ? 'staff' : 'volunteer'}">${l.quantity_source.replace('_', ' ')}</span>
        </div>
        <div>
          <span style="color: var(--text-muted); font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Pickup Location:</span><br>
          <strong>${escapeHtml(l.location_name)}</strong><br>
          <span style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(l.building || '')} (${escapeHtml(l.floor || 'Ground')}) • ${escapeHtml(l.zone || '')}</span>
        </div>
        <div>
          <span style="color: var(--text-muted); font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Storage & Handling:</span><br>
          <strong>${l.storage_condition.replace('_', ' ').toUpperCase()}</strong>
        </div>
        <div>
          <span style="color: var(--text-muted); font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">Pickup Deadline:</span><br>
          <strong style="color: #b45309;">Until ${deadlineStr}</strong>
        </div>
      </div>

      ${l.known_allergens ? `
        <div style="font-size: 0.76rem; color: #991b1b; background: #fee2e2; padding: 6px 10px; border-radius: 6px; margin-bottom: 10px;">
          ⚠️ <b>Known Allergens:</b> ${escapeHtml(l.known_allergens)}
        </div>
      ` : ''}

      ${l.staff_notes ? `
        <div style="font-size: 0.78rem; color: var(--text-main); background: #f8fafc; border: 1px solid var(--border); padding: 8px 10px; border-radius: 6px; margin-bottom: 12px;">
          📝 <b>Staff Notes:</b> ${escapeHtml(l.staff_notes)}
        </div>
      ` : ''}

      <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 6px; padding: 8px 10px; font-size: 0.72rem; color: #166534; margin-bottom: 12px;">
        🛡️ <b>Food Safety Verification:</b> Physical sensory checklist and storage protocol confirmed by canteen staff (${escapeHtml(l.staff_name)}).
      </div>

      <div style="margin-bottom: 16px;">
        <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Status Transition History:</div>
        <div style="max-height: 90px; overflow-y: auto; font-size: 0.72rem; color: var(--text-muted); border: 1px solid var(--border); border-radius: 6px; padding: 6px;">
          ${(res.audit_logs || []).map(a => `
            <div>• <b>${new Date(a.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</b>: ${a.old_status} → ${a.new_status} (${escapeHtml(a.user_name)}): <i>${escapeHtml(a.change_note || '')}</i></div>
          `).join('')}
        </div>
      </div>

      <div style="display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
        
        ${l.status === 'available' && role === 'volunteer' ? `
          <button class="btn btn-primary" onclick="App.closeModal(); Volunteer.claimListing(${l.id});">
            🤝 Claim Food
          </button>
        ` : ''}

        ${l.status === 'claimed' && l.claimed_by_volunteer_id === userId ? `
          <button class="btn btn-primary" onclick="App.closeModal(); Volunteer.startPickup(${l.id});">
            🚶 Start Pickup
          </button>
        ` : ''}

        ${l.status === 'pickup_in_progress' && (l.claimed_by_volunteer_id === userId || role === 'staff' || role === 'admin') ? `
          <button class="btn btn-success" onclick="App.closeModal(); Volunteer.openCollectModal(${l.id}, '${escapeHtml(l.food_name)}', ${l.quantity_value}, '${l.quantity_unit}');">
            ✓ Confirm Collection
          </button>
        ` : ''}

        ${(l.status === 'available' || l.status === 'claimed') && (role === 'staff' || role === 'admin' || l.claimed_by_volunteer_id === userId) ? `
          <button class="btn btn-danger btn-sm" onclick="App.openCancelModal(${l.id});">
            ✕ Cancel
          </button>
        ` : ''}
      </div>
    `;
    this.openModal();
  },

  openCancelModal(listingId) {
    const modalContent = document.getElementById('modalContent');
    modalContent.innerHTML = `
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; color: #dc2626;">✕ Cancel Food Listing</h3>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>

      <div style="margin-bottom: 14px; font-size: 0.82rem; color: var(--text-muted);">
        Please specify a mandatory reason for cancellation (e.g., quality inspection failure, spill, canteen schedule change).
      </div>

      <div style="margin-bottom: 16px;">
        <label class="form-label">Cancellation Reason <span class="req">*</span></label>
        <textarea id="cancelReasonInput" class="form-control" rows="3" placeholder="Provide honest details for audit trail..."></textarea>
      </div>

      <div style="display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Keep Listing</button>
        <button class="btn btn-danger" onclick="App.submitCancellation(${listingId})">Confirm Cancellation</button>
      </div>
    `;
    this.openModal();
  },

  async submitCancellation(listingId) {
    const reason = document.getElementById('cancelReasonInput').value.trim();
    if (!reason) {
      this.showToast("Cancellation reason is mandatory.", "danger");
      return;
    }

    const res = await API.post(`/api/listings/${listingId}/cancel`, { reason });
    if (res.success) {
      this.showToast("Listing cancelled and recorded in audit log.", "info");
      this.closeModal();
      this.refreshCurrentView();
    } else {
      this.showToast(res.error, "danger");
    }
  },

  // In-App Notifications Dropdown
  async openNotifications() {
    const res = await API.get('/api/notifications');
    const notifs = res.notifications || [];

    const modalContent = document.getElementById('modalContent');
    modalContent.innerHTML = `
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; color: var(--primary-dark);">🔔 In-App Volunteer Broadcasts & Alerts</h3>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>

      <div style="display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto;">
        ${notifs.length === 0 ? `
          <div style="text-align: center; color: var(--text-muted); padding: 24px;">No new alerts.</div>
        ` : notifs.map(n => `
          <div style="background: ${n.is_read ? 'var(--bg-muted)' : '#ecfdf5'}; border: 1px solid ${n.is_read ? 'var(--border)' : '#86efac'}; border-radius: 8px; padding: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <strong style="font-size: 0.85rem; color: var(--text-main);">${escapeHtml(n.title)}</strong>
              <span style="font-size: 0.7rem; color: var(--text-muted);">${new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <p style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(n.message)}</p>
          </div>
        `).join('')}
      </div>

      <div style="margin-top: 16px; text-align: right;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
      </div>
    `;
    this.openModal();

    // Mark notifications as read
    const badge = document.getElementById('notifCountBadge');
    if (badge) badge.style.display = 'none';
  },

  setupNotificationChecker() {
    setInterval(async () => {
      if (Auth.currentUser) {
        const res = await API.get('/api/notifications?unread=1');
        const badge = document.getElementById('notifCountBadge');
        if (badge && res.notifications) {
          const count = res.notifications.length;
          if (count > 0) {
            badge.innerText = count;
            badge.style.display = 'inline-block';
          } else {
            badge.style.display = 'none';
          }
        }
      }
    }, 15000);
  },

  // Toast Notification System
  showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  }
};

// Global Sanitizer
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// Bootstrap on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
