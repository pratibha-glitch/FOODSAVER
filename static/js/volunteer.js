// SmartPlate AI - Student Volunteer Discovery, Matching & Claim Controller
const Volunteer = {
  currentListings: [],
  countdownInterval: null,

  async init() {
    await this.loadFilterDropdowns();
    await this.loadAvailableListings();
    if (Auth.currentUser && (Auth.currentUser.role === 'volunteer' || Auth.currentUser.role === 'admin')) {
      await this.loadMyPickups();
    }
  },

  async loadFilterDropdowns() {
    const res = await API.get('/api/locations');
    const select = document.getElementById('volunteerFilterLocation');
    if (!select) return;

    if (res.success && res.locations) {
      select.innerHTML = '<option value="">All Campus Locations</option>' + 
        res.locations.map(l => `<option value="${l.id}">${l.name}</option>`).join('');
    }
  },

  async loadAvailableListings() {
    const container = document.getElementById('volunteerListingsContainer');
    if (!container) return;

    const locFilter = document.getElementById('volunteerFilterLocation') ? document.getElementById('volunteerFilterLocation').value : '';
    const catFilter = document.getElementById('volunteerFilterCategory') ? document.getElementById('volunteerFilterCategory').value : '';
    const urgFilter = document.getElementById('volunteerFilterUrgency') ? document.getElementById('volunteerFilterUrgency').value : '';

    let url = '/api/volunteer/listings?';
    if (locFilter) url += `location_id=${encodeURIComponent(locFilter)}&`;
    if (catFilter) url += `category=${encodeURIComponent(catFilter)}&`;
    if (urgFilter) url += `urgency=${encodeURIComponent(urgFilter)}&`;

    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">
        <div class="pulse-dot" style="margin: 0 auto 10px;"></div>
        Fetching available campus surplus meals & calculating urgency priority...
      </div>
    `;

    const res = await API.get(url);
    if (!res.success || !res.listings || res.listings.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 50px 20px; background: #fff; border: 1px dashed var(--border); border-radius: 12px;">
          <div style="font-size: 2.5rem; margin-bottom: 10px;">🍱</div>
          <h3 style="font-size: 1.1rem; color: var(--text-main); margin-bottom: 4px;">No Available Food Listings Right Now</h3>
          <p style="font-size: 0.82rem; color: var(--text-muted); max-width: 380px; margin: 0 auto;">
            All current surplus items have either been claimed or completed. As soon as canteen staff log surplus meals, they will appear here live.
          </p>
        </div>
      `;
      return;
    }

    this.currentListings = res.listings;
    container.innerHTML = res.listings.map(l => {
      const urg = l.urgency;
      const deadlineDate = new Date(l.operational_deadline);
      const timeStr = deadlineDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const photoSrc = l.photo_filename ? `/static/uploads/${l.photo_filename}` : '/static/uploads/preset_dal_rice.jpg';

      return `
        <div class="listing-card" id="card-listing-${l.id}">
          <div class="listing-img-box">
            <img src="${photoSrc}" alt="${escapeHtml(l.food_name)}" class="listing-img" onerror="this.src='/static/uploads/preset_dal_rice.jpg'">
            <div class="listing-img-tag">
              <span class="status-pill status-${l.status}">● ${l.status.toUpperCase()}</span>
            </div>
            <div class="listing-urgency-tag">
              <span class="live-countdown-badge" id="timer-${l.id}" data-deadline="${l.operational_deadline}">
                ⏱️ Calculating...
              </span>
            </div>
          </div>

          <div class="listing-body">
            <h3 class="listing-title">${escapeHtml(l.food_name)}</h3>
            
            <div class="listing-meta-row">
              <span>📦 <b>Quantity:</b></span>
              <strong>${l.quantity_value} ${l.quantity_unit} <span style="font-size: 0.72rem; color: var(--text-muted);">(${l.quantity_source.replace('_', ' ')})</span></strong>
            </div>

            <div class="listing-meta-row">
              <span>📍 <b>Pickup Location:</b></span>
              <strong style="color: var(--primary-dark);">${escapeHtml(l.location_name)}</strong>
            </div>

            <div class="listing-meta-row">
              <span>⏳ <b>Pickup Deadline:</b></span>
              <strong style="color: #b45309;">Until ${timeStr}</strong>
            </div>

            <div style="background: var(--bg-muted); padding: 8px 10px; border-radius: 6px; font-size: 0.74rem; color: var(--text-muted); margin: 8px 0;">
              ℹ️ <i>${urg.explanation}</i>
            </div>

            ${l.known_allergens ? `
              <div style="font-size: 0.74rem; color: #b91c1c; margin-bottom: 8px;">
                ⚠️ <b>Allergens:</b> ${escapeHtml(l.known_allergens)}
              </div>
            ` : ''}

            <div class="listing-footer">
              <button class="btn-claim-primary" onclick="Volunteer.claimListing(${l.id})">
                🤝 Claim Food (1-Click)
              </button>
              <div class="listing-actions-row">
                <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="App.showListingDetails(${l.id})" title="View full confirmed listing details">
                  🔍 View Details
                </button>
                <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="Volunteer.openSmartMatching(${l.id})" title="View smart volunteer eligibility ranking">
                  🎯 Volunteer Match
                </button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    this.startCountdownTicker();
  },

  startCountdownTicker() {
    if (this.countdownInterval) clearInterval(this.countdownInterval);
    const update = () => {
      const now = new Date().getTime();
      document.querySelectorAll('.live-countdown-badge[data-deadline]').forEach(badge => {
        const deadlineStr = badge.getAttribute('data-deadline');
        const deadline = new Date(deadlineStr).getTime();
        const diff = deadline - now;
        if (diff <= 0) {
          badge.innerHTML = '⏱️ Expired';
          badge.classList.add('expired');
        } else {
          badge.classList.remove('expired');
          const hours = Math.floor(diff / (1000 * 60 * 60));
          const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
          const secs = Math.floor((diff % (1000 * 60)) / 1000);
          const formatted = (hours > 0 ? `${hours}h ` : '') + `${String(mins).padStart(2, '0')}m ${String(secs).padStart(2, '0')}s left`;
          badge.innerHTML = `⏱️ ${formatted}`;
        }
      });
    };
    update();
    this.countdownInterval = setInterval(update, 1000);
  },

  // Atomic Claim Action
  async claimListing(listingId) {
    if (!Auth.currentUser) {
      App.showToast("Please sign in first to claim surplus food.", "warning");
      App.showLoginModal();
      return;
    }

    if (Auth.currentUser.role === 'volunteer' && !Auth.currentUser.is_verified) {
      App.showToast("⚠️ Only verified volunteers may claim food. Your account is currently pending verification.", "danger");
      return;
    }

    const res = await API.post(`/api/volunteer/listings/${listingId}/claim`);
    if (res.success) {
      App.showToast("🎉 " + res.message, "success");
      await this.loadAvailableListings();
      await this.loadMyPickups();
      App.switchTab('my-pickups');
    } else {
      App.showToast("❌ " + res.error, "danger");
      await this.loadAvailableListings();
    }
  },

  // Smart Volunteer Matching Modal (Feature 2)
  async openSmartMatching(listingId) {
    const res = await API.get(`/api/volunteer/listings/${listingId}/matching`);
    if (!res.success) {
      App.showToast(res.error, "danger");
      return;
    }

    const modalContent = document.getElementById('modalContent');
    const recs = res.recommendations || [];

    modalContent.innerHTML = `
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; color: var(--primary-dark);">🎯 Smart Volunteer Matching & Ranking</h3>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>

      <div style="margin-bottom: 12px; font-size: 0.8rem; color: var(--text-muted);">
        Evaluating verified volunteers for <b>${escapeHtml(res.listing_food)}</b> at <b>${escapeHtml(res.pickup_location)}</b>.
        (${res.minutes_remaining} minutes remaining in window)
      </div>

      <div style="display: flex; flex-direction: column; gap: 10px; max-height: 400px; overflow-y: auto;">
        ${recs.length === 0 ? `
          <div style="text-align: center; color: var(--text-muted); padding: 20px;">
            No verified volunteers available within active capacity constraints.
          </div>
        ` : recs.map((rec, idx) => `
          <div style="background: var(--bg-muted); border: 1px solid var(--border); border-radius: 8px; padding: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <strong>#${idx + 1} ${escapeHtml(rec.volunteer_name)}</strong>
              <span class="user-role-tag volunteer">Match Score: ${rec.score}</span>
            </div>
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 4px;">
              📍 Stationed: ${escapeHtml(rec.location_name)} • Active Load: ${rec.active_load} current pickups
            </div>
            <div style="font-size: 0.76rem; color: #166534; background: #dcfce7; padding: 6px 8px; border-radius: 4px;">
              💡 <b>Explanation:</b> ${escapeHtml(rec.explanation)}
            </div>
          </div>
        `).join('')}
      </div>

      <div style="margin-top: 16px; text-align: right;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
      </div>
    `;
    App.openModal();
  },

  // My Claimed Pickups Management
  async loadMyPickups() {
    const tableBody = document.getElementById('myPickupsTableBody');
    if (!tableBody) return;

    const res = await API.get('/api/volunteer/my-pickups');
    if (!res.success || !res.pickups || res.pickups.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">You have no active or previous claimed pickups. Discover available food in the feed!</td></tr>`;
      return;
    }

    tableBody.innerHTML = res.pickups.map(p => {
      const deadlineStr = new Date(p.operational_deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return `
        <tr>
          <td>
            <strong>${escapeHtml(p.food_name)}</strong>
            <div style="font-size: 0.72rem; color: var(--text-muted);">${p.quantity_value} ${p.quantity_unit}</div>
          </td>
          <td>📍 ${escapeHtml(p.location_name)}</td>
          <td><span style="font-size: 0.8rem; font-weight: 600;">${deadlineStr}</span></td>
          <td><span class="status-pill status-${p.status}">${p.status.replace('_', ' ')}</span></td>
          <td>${p.actual_collected_quantity_value ? `<b>${p.actual_collected_quantity_value} ${p.actual_collected_quantity_unit}</b>` : '—'}</td>
          <td>
            <div style="display: flex; gap: 4px;">
              ${p.status === 'claimed' ? `
                <button class="btn btn-primary btn-sm" onclick="Volunteer.startPickup(${p.id})">
                  🚶 Start Pickup
                </button>
              ` : ''}

              ${p.status === 'pickup_in_progress' ? `
                <button class="btn btn-success btn-sm" onclick="Volunteer.openCollectModal(${p.id}, '${escapeHtml(p.food_name)}', ${p.quantity_value}, '${p.quantity_unit}')">
                  ✓ Confirm Collection
                </button>
              ` : ''}

              ${p.status === 'claimed' || p.status === 'pickup_in_progress' ? `
                <button class="btn btn-danger btn-sm" onclick="App.openCancelModal(${p.id})">
                  ✕ Release
                </button>
              ` : ''}

              ${p.status === 'collected' ? `
                <span style="font-size: 0.75rem; color: #15803d; font-weight: bold;">✓ Completed</span>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  async startPickup(listingId) {
    const res = await API.post(`/api/volunteer/listings/${listingId}/start-pickup`);
    if (res.success) {
      App.showToast("Pickup in progress! Head to the mess counter.", "info");
      await this.loadMyPickups();
    } else {
      App.showToast(res.error, "danger");
    }
  },

  openCollectModal(listingId, foodName, defaultQty, defaultUnit) {
    const modalContent = document.getElementById('modalContent');
    modalContent.innerHTML = `
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; color: var(--primary-dark);">✓ Confirm Physical Food Collection</h3>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>

      <div style="margin-bottom: 12px; font-size: 0.82rem; color: var(--text-muted);">
        Item: <b>${escapeHtml(foodName)}</b>. Please enter the verified actual quantity physically handed over by staff.
      </div>

      <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 10px; margin-bottom: 16px;">
        <div>
          <label class="form-label">Actual Collected Quantity <span class="req">*</span></label>
          <input type="number" step="0.1" id="actualQuantityVal" class="form-control" value="${defaultQty}" required>
        </div>
        <div>
          <label class="form-label">Unit <span class="req">*</span></label>
          <select id="actualQuantityUnit" class="form-control">
            <option value="kg" ${defaultUnit === 'kg' ? 'selected' : ''}>kg</option>
            <option value="portions" ${defaultUnit === 'portions' ? 'selected' : ''}>portions</option>
            <option value="meal_boxes" ${defaultUnit === 'meal_boxes' ? 'selected' : ''}>meal_boxes</option>
            <option value="plates" ${defaultUnit === 'plates' ? 'selected' : ''}>plates</option>
            <option value="pieces" ${defaultUnit === 'pieces' ? 'selected' : ''}>pieces</option>
          </select>
        </div>
      </div>

      <div style="display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Cancel</button>
        <button class="btn btn-success" onclick="Volunteer.submitCollection(${listingId})">
          ✓ Confirm & Record Impact
        </button>
      </div>
    `;
    App.openModal();
  },

  async submitCollection(listingId) {
    const val = document.getElementById('actualQuantityVal').value;
    const unit = document.getElementById('actualQuantityUnit').value;

    if (!val || parseFloat(val) <= 0) {
      App.showToast("Please enter a valid actual quantity.", "danger");
      return;
    }

    const res = await API.post(`/api/volunteer/listings/${listingId}/collect`, {
      actual_quantity_value: parseFloat(val),
      actual_quantity_unit: unit
    });

    if (res.success) {
      App.showToast("🎉 Collection confirmed and recorded in impact statistics!", "success");
      App.closeModal();
      await this.loadMyPickups();
      App.refreshMetricsBanner();
    } else {
      App.showToast(res.error, "danger");
    }
  }
};
