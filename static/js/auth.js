// SmartPlate AI - Authentication & Role State Manager
const Auth = {
  currentUser: null,

  async init() {
    const res = await API.get('/api/auth/me');
    if (res.authenticated && res.user) {
      this.currentUser = res.user;
    } else {
      // Default to demo admin on fresh evaluation
      await this.switchDemoUser('admin');
    }
    this.renderUserUI();
  },

  async login(identifier, password) {
    const res = await API.post('/api/auth/login', { identifier, password });
    if (res.success) {
      this.currentUser = res.user;
      this.renderUserUI();
      App.showToast(res.message, 'success');
      App.refreshCurrentView();
      return true;
    } else {
      App.showToast(res.error, 'danger');
      return false;
    }
  },

  async logout() {
    await API.post('/api/auth/logout');
    this.currentUser = null;
    this.renderUserUI();
    App.showToast('Signed out successfully.', 'info');
    App.switchTab('volunteer-feed');
  },

  async switchDemoUser(roleKey) {
    const res = await API.post('/api/auth/demo-switch', { username: roleKey });
    if (res.success) {
      this.currentUser = res.user;
      this.renderUserUI();

      const roleLabels = {
        'admin': 'Admin',
        'staff': 'Canteen Staff',
        'volunteer': 'Verified Volunteer'
      };
      const label = roleLabels[res.user.role] || res.user.role;
      App.showToast(`Switched active role to: <b>${label}</b>`, 'success');
      
      // Auto-switch to most relevant tab for that role
      if (res.user.role === 'staff') {
        App.switchTab('staff-dashboard');
      } else if (res.user.role === 'volunteer') {
        App.switchTab('volunteer-feed');
      } else if (res.user.role === 'admin') {
        App.switchTab('admin-dashboard');
      }
      App.refreshCurrentView();
    } else {
      App.showToast(res.error, 'danger');
    }
  },

  getRoleLabel(role) {
    if (role === 'admin') return 'Admin';
    if (role === 'staff') return 'Canteen Staff';
    if (role === 'volunteer') return 'Verified Volunteer';
    return role;
  },

  renderUserUI() {
    const userContainer = document.getElementById('userProfileContainer');
    if (!userContainer) return;

    if (this.currentUser) {
      const u = this.currentUser;
      const roleLabel = this.getRoleLabel(u.role);
      const icon = u.role === 'admin' ? '👑' : (u.role === 'staff' ? '👨‍🍳' : '🤝');

      userContainer.innerHTML = `
        <div class="user-pill">
          <span>${icon} ${roleLabel}</span>
          <span class="user-role-tag ${u.role}">Active</span>
        </div>
      `;
    } else {
      userContainer.innerHTML = `
        <button class="btn btn-primary btn-sm" onclick="App.showLoginModal()">Sign In</button>
      `;
    }

    // Highlight current active role button in top bar
    document.querySelectorAll('.demo-btn').forEach(btn => {
      const btnRole = btn.getAttribute('data-role');
      if (this.currentUser && this.currentUser.role === btnRole) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Control visibility of tabs based on role
    this.updateTabPermissions();
  },

  updateTabPermissions() {
    const role = this.currentUser ? this.currentUser.role : 'public';
    const staffTab = document.getElementById('tab-staff');
    const adminTab = document.getElementById('tab-admin');
    const claimsTab = document.getElementById('tab-my-pickups');

    if (staffTab) staffTab.style.display = (role === 'staff' || role === 'admin') ? 'flex' : 'none';
    if (adminTab) adminTab.style.display = (role === 'admin') ? 'flex' : 'none';
    if (claimsTab) claimsTab.style.display = (role === 'volunteer' || role === 'admin') ? 'flex' : 'none';
  }
};
