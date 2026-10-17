// SmartPlate AI - Canteen & Hostel Staff Workflow Controller
const Staff = {
  currentPhotoFilename: null,
  currentAiData: null,

  async init() {
    await this.loadLocationsDropdown();
    await this.loadStaffListings();
    this.setupOperationalDeadlineDefaults();
  },

  async loadLocationsDropdown() {
    const res = await API.get('/api/locations');
    const select = document.getElementById('staffLocationSelect');
    if (!select) return;

    if (res.success && res.locations) {
      select.innerHTML = res.locations.map(loc => 
        `<option value="${loc.id}">${loc.name} (${loc.building} - ${loc.zone})</option>`
      ).join('');

      // If current staff user has assigned location, preselect it
      if (Auth.currentUser && Auth.currentUser.campus_location_id) {
        select.value = Auth.currentUser.campus_location_id;
      }
    }
  },

  setupOperationalDeadlineDefaults() {
    const deadlineInput = document.getElementById('staffDeadlineInput');
    if (!deadlineInput) return;

    // Default to +3 hours from now
    const now = new Date();
    now.setHours(now.getHours() + 3);
    
    // Format for datetime-local: YYYY-MM-DDTHH:MM
    const isoString = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    deadlineInput.value = isoString;
  },

  // Preset Fast Demos for Viva/Testing
  applyDemoPreset(presetType) {
    const nameInput = document.getElementById('staffFoodName');
    const catSelect = document.getElementById('staffCategory');
    const qtyInput = document.getElementById('staffQuantityValue');
    const unitSelect = document.getElementById('staffQuantityUnit');
    const sourceSelect = document.getElementById('staffQuantitySource');
    const storageSelect = document.getElementById('staffStorageCondition');
    const allergensInput = document.getElementById('staffAllergens');
    const notesInput = document.getElementById('staffNotes');

    if (presetType === 'dal-rice') {
      nameInput.value = "Cooked Jeera Rice & Yellow Dal Tadka";
      catSelect.value = "cooked_rice";
      qtyInput.value = "8.5";
      unitSelect.value = "kg";
      sourceSelect.value = "measured";
      storageSelect.value = "hot_holding";
      allergensInput.value = "Dairy (butter/ghee in dal)";
      notesInput.value = "Freshly prepared for midday service. Kept in insulated stainless steel hot containers.";
      this.currentPhotoFilename = "preset_dal_rice.jpg";
    } else if (presetType === 'roti-sabzi') {
      nameInput.value = "Wheat Rotis & Aloo Gobi Dry Sabzi";
      catSelect.value = "bread_roti";
      qtyInput.value = "30";
      unitSelect.value = "portions";
      sourceSelect.value = "manually_estimated";
      storageSelect.value = "ambient_covered";
      allergensInput.value = "Gluten (whole wheat)";
      notesInput.value = "Kept stacked in clean covered chafing warmers.";
      this.currentPhotoFilename = "preset_roti_sabzi.jpg";
    } else if (presetType === 'kheer') {
      nameInput.value = "Chilled Rice Kheer & Gulab Jamun";
      catSelect.value = "dairy_sweets";
      qtyInput.value = "15";
      unitSelect.value = "portions";
      sourceSelect.value = "measured";
      storageSelect.value = "chilled_refrigerated";
      allergensInput.value = "Dairy (milk), Nuts (almonds/pistachios)";
      notesInput.value = "Hostel banquet dessert surplus. Refrigerated at 4°C.";
      this.currentPhotoFilename = "preset_kheer.jpg";
    }

    // Set preview photo
    const previewContainer = document.getElementById('staffPhotoPreviewContainer');
    const previewImg = document.getElementById('staffPhotoPreview');
    if (previewImg && previewContainer) {
      previewImg.src = `/static/uploads/${this.currentPhotoFilename}`;
      previewContainer.style.display = 'block';
    }

    App.showToast(`Loaded ${presetType} preset! Review details and confirm human checklist before publishing.`, 'info');
  },

  // Image Upload and Real AI Vision Analysis Trigger
  async handlePhotoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const previewContainer = document.getElementById('staffPhotoPreviewContainer');
    const previewImg = document.getElementById('staffPhotoPreview');
    const aiBox = document.getElementById('staffAiSuggestionBox');

    // Show instant local preview
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewContainer.style.display = 'block';
    };
    reader.readAsDataURL(file);

    // Show analyzing state
    aiBox.style.display = 'block';
    aiBox.innerHTML = `
      <div style="text-align: center; padding: 20px;">
        <div class="pulse-dot" style="margin: 0 auto 10px; width: 14px; height: 14px;"></div>
        <strong style="color: #6b21a8;">🤖 AI Food Vision Assistant Analyzing Photograph...</strong>
        <p style="font-size: 0.78rem; color: #7e22ce; margin-top: 4px;">
          Evaluating food category, countable items, container boundaries & quantity constraints...
        </p>
      </div>
    `;

    // Send to backend
    const formData = new FormData();
    formData.append('photo', file);

    const res = await API.post('/api/staff/analyze-photo', formData);
    if (!res.success) {
      aiBox.innerHTML = `
        <div style="color: #b91c1c; font-size: 0.8rem;">
          ⚠️ <b>AI Analysis Failed:</b> ${res.error}<br>
          <i>You can still fill in the listing details manually below.</i>
        </div>
      `;
      return;
    }

    this.currentPhotoFilename = res.photo_filename;
    this.currentAiData = res.ai_data;

    if (res.ai_data) {
      this.renderAiSuggestions(res.ai_data);
      this.prefillFormWithAi(res.ai_data);
    } else if (res.warning) {
      aiBox.innerHTML = `
        <div style="color: #b45309; font-size: 0.8rem;">
          ℹ️ <b>AI Notice:</b> ${res.warning}<br>
          <i>Please specify food item details manually.</i>
        </div>
      `;
    }
  },

  renderAiSuggestions(ai) {
    const aiBox = document.getElementById('staffAiSuggestionBox');
    if (!aiBox) return;

    aiBox.style.display = 'block';
    const confPercent = Math.round((ai.confidence_score || 0.7) * 100);

    aiBox.innerHTML = `
      <div class="ai-suggestion-header">
        <span class="ai-badge">✨ AI Vision Prediction (${confPercent}% Confidence)</span>
        <span style="font-size: 0.72rem; color: #7e22ce; font-weight: 600;">${ai.ai_provider || 'Cloud Vision'}</span>
      </div>
      
      <div class="ai-meta-text">
        <strong>Identified:</strong> ${ai.food_name} • <strong>Category:</strong> ${ai.category.replace('_', ' ').toUpperCase()}<br>
        <strong>Visual Estimate:</strong> ${ai.approximate_quantity_range || 'Unknown - scale measurement needed'}<br>
        <strong>Visual Reasoning:</strong> <i>"${ai.confidence_reasoning}"</i>
      </div>

      <div class="ai-fields-notice">
        ⚠️ <b>Staff Verification Required:</b> ${ai.fields_requiring_staff_input ? ai.fields_requiring_staff_input.join(', ') : 'Exact mass, temperature check'}
      </div>
    `;
  },

  prefillFormWithAi(ai) {
    const nameInput = document.getElementById('staffFoodName');
    const catSelect = document.getElementById('staffCategory');
    const sourceSelect = document.getElementById('staffQuantitySource');
    const notesInput = document.getElementById('staffNotes');

    if (ai.food_name && !nameInput.value) nameInput.value = ai.food_name;
    if (ai.category) catSelect.value = ai.category;
    if (sourceSelect) sourceSelect.value = "ai_estimated";

    if (ai.storage_recommendation && !notesInput.value) {
      notesInput.value = `[AI Guideline]: ${ai.storage_recommendation}`;
    }

    App.showToast("Form prefilled with AI suggestions. Please verify quantity and handling details.", "success");
  },

  // Submit Listing (Draft or Available)
  async submitListing(targetStatus) {
    const name = document.getElementById('staffFoodName').value.trim();
    const category = document.getElementById('staffCategory').value;
    const quantityVal = document.getElementById('staffQuantityValue').value;
    const quantityUnit = document.getElementById('staffQuantityUnit').value;
    const quantitySource = document.getElementById('staffQuantitySource').value;
    const cookingTimeElem = document.getElementById('staffCookingTime');
    const cookingTime = cookingTimeElem ? cookingTimeElem.value : '';
    const storageCondition = document.getElementById('staffStorageCondition').value;
    const allergens = document.getElementById('staffAllergens').value.trim();
    const deadline = document.getElementById('staffDeadlineInput').value;
    const notes = document.getElementById('staffNotes').value.trim();

    // Human Safety Checklist Checkboxes
    const chk1 = document.getElementById('chkSafetySensory').checked;
    const chk2 = document.getElementById('chkSafetyTemp').checked;
    const chk3 = document.getElementById('chkSafetyHygiene').checked;
    const safetyChecklistConfirmed = chk1 && chk2 && chk3;

    if (!name || !quantityVal || !locationId || !deadline) {
      App.showToast("Please fill in all required fields (Name, Quantity, Location, Pickup Deadline).", "danger");
      return;
    }

    if (targetStatus === 'available' && !safetyChecklistConfirmed) {
      App.showToast("⚠️ Cannot publish as 'Available': You must physically verify and check all 3 food safety checklist items.", "danger");
      return;
    }

    const payload = {
      food_name: name,
      category: category,
      quantity_value: quantityVal,
      quantity_unit: quantityUnit,
      quantity_source: quantitySource,
      location_id: parseInt(locationId),
      photo_filename: this.currentPhotoFilename,
      cooking_time: cookingTime,
      storage_condition: storageCondition,
      known_allergens: allergens,
      operational_deadline: deadline,
      safety_checklist_confirmed: safetyChecklistConfirmed ? 1 : 0,
      safety_notes: safetyChecklistConfirmed ? "Physical sensory, temperature, and clean storage verified." : "",
      staff_notes: notes,
      status: targetStatus
    };

    const res = await API.post('/api/staff/listings', payload);
    if (res.success) {
      App.showToast(
        targetStatus === 'available'
          ? "🎉 Food listing published and broadcasted to verified volunteers!"
          : "Saved as Draft listing.",
        "success"
      );
      this.resetForm();
      await this.loadStaffListings();
    } else {
      App.showToast(res.error, "danger");
    }
  },

  resetForm() {
    document.getElementById('staffListingForm').reset();
    document.getElementById('staffPhotoPreviewContainer').style.display = 'none';
    document.getElementById('staffAiSuggestionBox').style.display = 'none';
    this.currentPhotoFilename = null;
    this.currentAiData = null;
    this.setupOperationalDeadlineDefaults();
  },

  async loadStaffListings() {
    const tableBody = document.getElementById('staffListingsTableBody');
    if (!tableBody) return;

    const res = await API.get('/api/staff/listings');
    if (!res.success || !res.listings || res.listings.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No listings logged yet. Use the form above to add surplus food.</td></tr>`;
      return;
    }

    tableBody.innerHTML = res.listings.map(l => {
      const deadlineStr = new Date(l.operational_deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return `
        <tr>
          <td>
            <strong>${escapeHtml(l.food_name)}</strong>
            <div style="font-size: 0.72rem; color: var(--text-muted);">${l.quantity_value} ${l.quantity_unit} (${l.quantity_source.replace('_', ' ')})</div>
          </td>
          <td><span style="font-size: 0.8rem; text-transform: capitalize;">${l.category.replace('_', ' ')}</span></td>
          <td><span style="font-size: 0.8rem;">📍 ${escapeHtml(l.location_name)}</span></td>
          <td><span style="font-size: 0.8rem; font-weight: 600;">${deadlineStr}</span></td>
          <td><span class="status-pill status-${l.status}">${l.status.replace('_', ' ')}</span></td>
          <td><span style="font-size: 0.78rem;">${l.volunteer_name ? '👤 ' + escapeHtml(l.volunteer_name) : '—'}</span></td>
          <td>
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-secondary btn-sm" onclick="App.showListingDetails(${l.id})" title="View complete confirmed details">
                🔍 Details
              </button>
              <button class="btn btn-secondary btn-sm" onclick="Staff.openNotificationDraft(${l.id})" title="Review In-App & WhatsApp Notification Draft">
                📢 Broadcast
              </button>
              ${l.status === 'available' || l.status === 'claimed' ? `
                <button class="btn btn-danger btn-sm" onclick="App.openCancelModal(${l.id})" title="Cancel Listing">
                  ✕ Cancel
                </button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  async openNotificationDraft(listingId) {
    const res = await API.post(`/api/staff/listings/${listingId}/draft-notification`);
    if (!res.success) {
      App.showToast(res.error, "danger");
      return;
    }

    const draft = res.draft;
    const modalContent = document.getElementById('modalContent');
    modalContent.innerHTML = `
      <div class="modal-header">
        <h3 style="font-size: 1.1rem; color: var(--primary-dark);">📢 AI Notification Writer (Review Draft)</h3>
        <button class="modal-close" onclick="App.closeModal()">✕</button>
      </div>

      <div style="margin-bottom: 14px;">
        <label class="form-label">In-App Broadcast Title</label>
        <input type="text" id="notifTitleInput" class="form-control" value="${escapeHtml(draft.title)}">
      </div>

      <div style="margin-bottom: 14px;">
        <label class="form-label">In-App Broadcast Message Body</label>
        <textarea id="notifBodyInput" class="form-control" rows="3">${escapeHtml(draft.in_app_body)}</textarea>
      </div>

      <div style="background: #efeae2; padding: 12px; border-radius: 8px; border: 1px solid #cbd5e1; margin-bottom: 16px;">
        <div style="font-size: 0.75rem; font-weight: 700; color: #075e54; margin-bottom: 4px;">
          💬 WhatsApp Formatted Template Preview (Verified Volunteer Group)
        </div>
        <pre style="white-space: pre-wrap; font-family: monospace; font-size: 0.78rem; color: #111b21;">${escapeHtml(draft.whatsapp_template)}</pre>
        <div style="font-size: 0.68rem; color: #64748b; margin-top: 6px;">
          ℹ️ ${escapeHtml(draft.integration_note)}
        </div>
      </div>

      <div style="display: flex; gap: 8px; justify-content: flex-end;">
        <button class="btn btn-secondary" onclick="App.closeModal()">Close</button>
        <button class="btn btn-primary" onclick="Staff.sendInAppNotification(${listingId})">
          🚀 Confirm & Dispatch In-App Alert
        </button>
      </div>
    `;
    App.openModal();
  },

  async sendInAppNotification(listingId) {
    const title = document.getElementById('notifTitleInput').value.trim();
    const message = document.getElementById('notifBodyInput').value.trim();

    const res = await API.post(`/api/staff/listings/${listingId}/send-notification`, { title, message });
    if (res.success) {
      App.showToast("In-app notification broadcasted to all verified volunteers!", "success");
      App.closeModal();
    } else {
      App.showToast(res.error, "danger");
    }
  }
};
