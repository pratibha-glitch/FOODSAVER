// SmartPlate AI - Administrator Dashboard & Oversight Controller
const Admin = {
  async init() {
    await this.loadMetrics();
    await this.loadUsers();
    await this.loadLocations();
    await this.loadConfig();
    await this.loadAuditLogs();
  },

  async loadMetrics() {
    const res = await API.get('/api/admin/metrics');
    if (!res.success || !res.metrics) return;

    const m = res.metrics;

    // Update main metrics cards
    const mKg = document.getElementById('metricKgCollected');
    const mPickups = document.getElementById('metricPickupsCount');
    const mActive = document.getElementById('metricActiveListings');
    const mVolunteers = document.getElementById('metricVerifiedVolunteers');
    const mAvgClaim = document.getElementById('metricAvgClaimTime');
    const mCo2 = document.getElementById('metricCo2Prevented');
    const mCo2Top = document.getElementById('metricCo2PreventedTop');
    const mCo2Note = document.getElementById('metricCo2Methodology');
    const mUnitBreakdown = document.getElementById('metricUnitBreakdown');

    if (mKg) mKg.innerText = `${m.total_kg_collected} kg`;
    if (mPickups) mPickups.innerText = m.completed_pickups;
    if (mActive) mActive.innerText = m.active_available_listings;
    if (mVolunteers) mVolunteers.innerText = m.verified_volunteers_count;
    if (mAvgClaim) mAvgClaim.innerText = `${m.avg_time_to_claim_minutes} min`;
    if (mCo2) mCo2.innerText = `${m.environmental_impact.co2_prevented_kg} kg`;
    if (mCo2Top) mCo2Top.innerText = `${m.environmental_impact.co2_prevented_kg} kg`;
    if (mCo2Note) mCo2Note.innerText = m.environmental_impact.calculation_basis;

    if (mUnitBreakdown && m.collected_quantity_by_unit) {
      const units = Object.entries(m.collected_quantity_by_unit);
      if (units.length === 0) {
        mUnitBreakdown.innerHTML = '<span style="color: var(--text-muted); font-size: 0.75rem;">No verified collections recorded yet.</span>';
      } else {
        mUnitBreakdown.innerHTML = units.map(([u, data]) => 
          `<span class="user-role-tag staff">${data.total_quantity} ${u} (${data.pickups_count} pickups)</span>`
        ).join(' ');
      }
    }
  },

  async loadUsers() {
    const tableBody = document.getElementById('adminUsersTableBody');
    if (!tableBody) return;

    const res = await API.get('/api/admin/users');
    if (!res.success || !res.users) return;

    tableBody.innerHTML = res.users.map(u => `
      <tr>
        <td>
          <strong>${escapeHtml(u.full_name)}</strong>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(u.email)} • @${escapeHtml(u.username)}</div>
        </td>
        <td><span class="user-role-tag ${u.role}">${u.role}</span></td>
        <td><span style="font-size: 0.8rem;">${escapeHtml(u.location_name || 'Campus Wide')}</span></td>
        <td>
          ${u.role === 'volunteer' ? `
            <span class="status-pill ${u.is_verified ? 'status-available' : 'status-expired'}">
              ${u.is_verified ? '✓ Verified' : '⏳ Pending'}
            </span>
          ` : `
            <span class="status-pill status-available">✓ Authorized</span>
          `}
        </td>
        <td>
          ${u.role === 'volunteer' ? `
            <button class="btn ${u.is_verified ? 'btn-secondary' : 'btn-success'} btn-sm" onclick="Admin.toggleUserVerification(${u.id}, ${!u.is_verified})">
              ${u.is_verified ? 'Revoke' : '✓ Verify Volunteer'}
            </button>
          ` : '—'}
        </td>
      </tr>
    `).join('');
  },

  async toggleUserVerification(userId, newStatus) {
    const res = await API.post(`/api/admin/users/${userId}/verify`, { is_verified: newStatus });
    if (res.success) {
      App.showToast(res.message, "success");
      await this.loadUsers();
      await this.loadMetrics();
    } else {
      App.showToast(res.error, "danger");
    }
  },

  async loadLocations() {
    const container = document.getElementById('adminLocationsList');
    if (!container) return;

    const res = await API.get('/api/admin/locations');
    if (!res.success || !res.locations) return;

    container.innerHTML = res.locations.map(l => `
      <div style="background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong>${escapeHtml(l.name)}</strong>
          <span class="user-role-tag volunteer">${escapeHtml(l.zone)}</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
          🏢 ${escapeHtml(l.building)} (${escapeHtml(l.floor || 'Ground')}) • 📞 ${escapeHtml(l.contact_person || 'Supervisor')} ${escapeHtml(l.phone || '')}
        </div>
      </div>
    `).join('');
  },

  async addLocation() {
    const name = document.getElementById('locNameInput').value.trim();
    const code = document.getElementById('locCodeInput').value.trim();
    const building = document.getElementById('locBuildingInput').value.trim();
    const floor = document.getElementById('locFloorInput').value.trim();
    const zone = document.getElementById('locZoneInput').value.trim();
    const contact = document.getElementById('locContactInput').value.trim();
    const phone = document.getElementById('locPhoneInput').value.trim();

    if (!name || !code || !building) {
      App.showToast("Location Name, Code, and Building are required.", "danger");
      return;
    }

    const res = await API.post('/api/admin/locations', {
      name, code, building, floor, zone, contact_person: contact, phone
    });

    if (res.success) {
      App.showToast("Campus location registered successfully.", "success");
      document.getElementById('adminLocationForm').reset();
      await this.loadLocations();
    } else {
      App.showToast(res.error, "danger");
    }
  },

  async loadConfig() {
    const res = await API.get('/api/admin/config');
    if (!res.success || !res.config) return;

    const c = res.config;
    if (document.getElementById('cfgHotHolding')) document.getElementById('cfgHotHolding').value = c.deadline_hot_holding_hours || 3.0;
    if (document.getElementById('cfgAmbientDry')) document.getElementById('cfgAmbientDry').value = c.deadline_ambient_dry_hours || 4.0;
    if (document.getElementById('cfgAmbientWet')) document.getElementById('cfgAmbientWet').value = c.deadline_ambient_wet_hours || 2.5;
    if (document.getElementById('cfgDairy')) document.getElementById('cfgDairy').value = c.deadline_dairy_hours || 2.0;
    if (document.getElementById('cfgMaxClaims')) document.getElementById('cfgMaxClaims').value = c.volunteer_max_concurrent_claims || 2;
  },

  async saveConfig() {
    const payload = {
      deadline_hot_holding_hours: document.getElementById('cfgHotHolding').value,
      deadline_ambient_dry_hours: document.getElementById('cfgAmbientDry').value,
      deadline_ambient_wet_hours: document.getElementById('cfgAmbientWet').value,
      deadline_dairy_hours: document.getElementById('cfgDairy').value,
      volunteer_max_concurrent_claims: document.getElementById('cfgMaxClaims').value
    };

    const res = await API.post('/api/admin/config', payload);
    if (res.success) {
      App.showToast("Operational rules updated successfully.", "success");
    } else {
      App.showToast(res.error, "danger");
    }
  },

  async loadAuditLogs() {
    const tableBody = document.getElementById('adminAuditLogsTableBody');
    if (!tableBody) return;

    const res = await API.get('/api/admin/audit-logs');
    if (!res.success || !res.logs) return;

    tableBody.innerHTML = res.logs.map(log => {
      const timeStr = new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return `
        <tr>
          <td><span style="font-size: 0.75rem; color: var(--text-muted);">${timeStr}</span></td>
          <td><strong>${escapeHtml(log.food_name)}</strong></td>
          <td>
            <span class="status-pill status-${log.old_status}">${log.old_status}</span> 
            → 
            <span class="status-pill status-${log.new_status}">${log.new_status}</span>
          </td>
          <td><span style="font-size: 0.78rem;">👤 ${escapeHtml(log.user_name)} (${log.user_role})</span></td>
          <td><span style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(log.change_note || '—')}</span></td>
        </tr>
      `;
    }).join('');
  }
};
