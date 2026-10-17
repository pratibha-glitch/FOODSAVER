// SmartPlate AI - Frontend Logic & WhatsApp Broadcast Simulator
// AI-Driven Canteen Waste Reduction & Logistics

// Active category expiry configuration (Hours)
const SHELF_LIFE_RULES = {
  dry: { hours: 5, label: "Dry Item (Roti, Dry Sabzi, Breads)", risk: "Low Risk", color: "#15803d" },
  wet: { hours: 3, label: "Wet / Curry (Dal, Gravy, Rice)", risk: "Medium Risk", color: "#b45309" },
  dairy: { hours: 2, label: "Dairy / Sweets (Paneer, Kheer, Milk)", risk: "High Risk", color: "#dc2626" }
};

// Preset sample photos for instant live presentation
const PRESET_PHOTOS = {
  "dal-rice": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=600&auto=format&fit=crop&q=80",
  "roti-sabzi": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?w=600&auto=format&fit=crop&q=80",
  "kheer": "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?w=600&auto=format&fit=crop&q=80",
  "default": "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=600&auto=format&fit=crop&q=80"
};

// Global application state
let currentFoodPhoto = null;
let activeCountdownInterval = null;
let lastGeneratedBroadcast = "";
let currentActiveItemData = null;

// Initial state and sample records for college demo
let surplusLogs = [
  {
    id: 1,
    item: "Basmati Rice & Mixed Dal",
    category: "wet",
    quantity: "8 kg (~25 plates)",
    location: "North Campus Mess - Counter 1",
    photo: PRESET_PHOTOS["dal-rice"],
    loggedAt: new Date(Date.now() - 40 * 60 * 1000), // 40 mins ago
    expiryTime: new Date(Date.now() + (3 * 3600 - 40 * 60) * 1000),
    status: "Available"
  },
  {
    id: 2,
    item: "Wheat Rotis & Aloo Gobi",
    category: "dry",
    quantity: "35 Rotis + 3 kg Sabzi",
    location: "Central Hostel Canteen",
    photo: PRESET_PHOTOS["roti-sabzi"],
    loggedAt: new Date(Date.now() - 75 * 60 * 1000), // 75 mins ago
    expiryTime: new Date(Date.now() + (5 * 3600 - 75 * 60) * 1000),
    status: "Claimed by NSS Team A"
  }
];

// Initialize upon document ready
document.addEventListener("DOMContentLoaded", () => {
  renderSurplusTable();
  setupCategorySync();
});

// Sync Category Select and Chip Highlights
function setupCategorySync() {
  const categorySelect = document.getElementById("category");
  if (!categorySelect) return;

  categorySelect.addEventListener("change", (e) => {
    updateCategoryChipUI(e.target.value);
  });
}

function updateCategoryChipUI(categoryValue) {
  document.querySelectorAll(".rule-chip").forEach((chip) => {
    if (chip.getAttribute("data-cat") === categoryValue) {
      chip.classList.add("active");
    } else {
      chip.classList.remove("active");
    }
  });
}

function selectCategoryChip(cat) {
  const categorySelect = document.getElementById("category");
  if (categorySelect) {
    categorySelect.value = cat;
    updateCategoryChipUI(cat);
  }
}

// Handle Image Upload and Instant Preview
function handleImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  if (!file.type.startsWith("image/")) {
    showToast("⚠️ Please upload a valid image file (JPG, PNG, WebP)!", "warning");
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    currentFoodPhoto = e.target.result;
    const previewContainer = document.getElementById("imagePreviewContainer");
    const previewImg = document.getElementById("imagePreview");
    
    if (previewImg && previewContainer) {
      previewImg.src = currentFoodPhoto;
      previewContainer.style.display = "block";
    }
    showToast("📷 Food photo loaded successfully!", "success");
  };
  reader.readAsDataURL(file);
}

// Remove Uploaded Image
function removeImage() {
  currentFoodPhoto = null;
  const fileInput = document.getElementById("foodPhoto");
  if (fileInput) fileInput.value = "";

  const previewContainer = document.getElementById("imagePreviewContainer");
  const previewImg = document.getElementById("imagePreview");
  if (previewImg) previewImg.src = "";
  if (previewContainer) previewContainer.style.display = "none";

  showToast("Photo removed.", "info");
}

// Preset Quick-Fill for instant demonstration
function applyPreset(presetType) {
  const itemInput = document.getElementById("item");
  const catInput = document.getElementById("category");
  const qtyInput = document.getElementById("quantity");
  const locInput = document.getElementById("location");

  if (presetType === "dal-rice") {
    itemInput.value = "Cooked Jeera Rice & Dal Tadka";
    catInput.value = "wet";
    qtyInput.value = "6 kg (~20 plates)";
    locInput.value = "Main Dining Hall - Service Counter A";
    currentFoodPhoto = PRESET_PHOTOS["dal-rice"];
  } else if (presetType === "roti-sabzi") {
    itemInput.value = "Fresh Chapatis & Mix Veg Sabzi";
    catInput.value = "dry";
    qtyInput.value = "40 Rotis + 4 kg Sabzi";
    locInput.value = "Girls Hostel 2 Canteen";
    currentFoodPhoto = PRESET_PHOTOS["roti-sabzi"];
  } else if (presetType === "kheer") {
    itemInput.value = "Rice Kheer & Sweet Halwa";
    catInput.value = "dairy";
    qtyInput.value = "3 kg (~15 servings)";
    locInput.value = "Executive Guest House Mess";
    currentFoodPhoto = PRESET_PHOTOS["kheer"];
  }

  // Display photo in preview container
  const previewContainer = document.getElementById("imagePreviewContainer");
  const previewImg = document.getElementById("imagePreview");
  if (previewImg && previewContainer && currentFoodPhoto) {
    previewImg.src = currentFoodPhoto;
    previewContainer.style.display = "block";
  }

  updateCategoryChipUI(catInput.value);
  showToast("⚡ Quick preset with photo loaded! Click 'Calculate Shelf-Life & Broadcast'.", "success");
}

// Main logic: Calculate AI Shelf Life and Generate WhatsApp Alert
function calculateAndAlert() {
  const item = document.getElementById("item").value.trim();
  const category = document.getElementById("category").value;
  const quantity = document.getElementById("quantity").value.trim();
  const location = document.getElementById("location").value.trim();

  if (!item || !quantity || !location) {
    showToast("⚠️ Please fill in all required fields!", "warning");
    return;
  }

  // AI Rule-Based Shelf Life
  const rule = SHELF_LIFE_RULES[category] || { hours: 3, label: "Standard", risk: "Medium", color: "#15803d" };
  const expiryHours = rule.hours;

  const now = new Date();
  const expiryDate = new Date(now.getTime() + expiryHours * 60 * 60 * 1000);

  const formattedExpiryTime = expiryDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
  const formattedExpiryDate = expiryDate.toLocaleDateString([], { month: 'short', day: 'numeric' });
  const currentTimeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });

  const finalPhoto = currentFoodPhoto || PRESET_PHOTOS["default"];

  // WhatsApp Alert Formatted Payload
  lastGeneratedBroadcast = 
`🚨 *SMARTPLATE AI: CAMPUS SURPLUS FOOD ALERT* 🚨
----------------------------------------
🍲 *Item:* ${item}
📦 *Quantity:* ${quantity}
🏷️ *Category:* ${rule.label}
📍 *Location:* ${location}
⏳ *Safe Shelf-Life:* Until ${formattedExpiryTime} (~${expiryHours} hrs window)
⚠️ *Risk Level:* ${rule.risk}
📷 *Photo:* Attached for volunteer verification
----------------------------------------
🌱 *Target SDG 2:* Zero Campus Food Waste
📲 *Action Required:* NSS / Student volunteers please claim and pickup immediately!`;

  currentActiveItemData = {
    item,
    category,
    quantity,
    location,
    photo: finalPhoto,
    expiryHours,
    expiryDate,
    formattedExpiryTime,
    formattedExpiryDate,
    currentTimeStr,
    rule
  };

  // Render Right-Hand Column with Photo, Food Details, and Live Countdown Timer
  displayResults(currentActiveItemData);

  // Start live ticking countdown timer
  startLiveCountdown(expiryDate);

  // Add new item to Active Surplus Board
  const newLog = {
    id: Date.now(),
    item,
    category,
    quantity,
    location,
    photo: finalPhoto,
    loggedAt: now,
    expiryTime: expiryDate,
    status: "Available"
  };
  surplusLogs.unshift(newLog);
  renderSurplusTable();

  // Update dynamic metric counter
  const mealsCount = document.getElementById("meals-saved-count");
  if (mealsCount) {
    const current = parseInt(mealsCount.innerText) || 350;
    mealsCount.innerText = (current + 18).toString();
  }

  showToast("🎉 Shelf-life assessed! Live volunteer dispatch ready.", "success");
}

// Display AI Calculation, Food Photo, Details & WhatsApp Broadcast Preview
function displayResults(data) {
  const container = document.getElementById("resultsContainer");
  if (!container) return;

  container.innerHTML = `
    <!-- Surplus Food Photo Display -->
    <div class="dispatch-food-photo-card">
      <img src="${data.photo}" alt="${escapeHtml(data.item)}" class="dispatch-food-img">
      <div class="dispatch-photo-tag">
        <span>📷 Verified Surplus Photo</span>
      </div>
    </div>

    <!-- Food Item Details & Location Grid -->
    <div class="dispatch-details-grid">
      <div class="dispatch-detail-item">
        <div class="dispatch-detail-label">Food Item</div>
        <div class="dispatch-detail-value">${escapeHtml(data.item)}</div>
      </div>
      <div class="dispatch-detail-item">
        <div class="dispatch-detail-label">Quantity</div>
        <div class="dispatch-detail-value">${escapeHtml(data.quantity)}</div>
      </div>
      <div class="dispatch-detail-item">
        <div class="dispatch-detail-label">Category & Risk</div>
        <div class="dispatch-detail-value" style="color: ${data.rule.color};">
          ${escapeHtml(data.rule.label.split('(')[0])} • ${data.rule.risk}
        </div>
      </div>
      <div class="dispatch-detail-item">
        <div class="dispatch-detail-label">Pickup Location</div>
        <div class="dispatch-detail-value">📍 ${escapeHtml(data.location)}</div>
      </div>
    </div>

    <!-- Live Countdown Timer Banner -->
    <div class="countdown-container">
      <div class="countdown-label-group">
        <div class="countdown-title">
          <span class="pulse-dot"></span>
          <span>Live Safe Window</span>
        </div>
        <div class="countdown-sub">Until ${data.formattedExpiryTime} (${data.expiryHours} hrs window)</div>
      </div>
      <div class="countdown-digits" id="liveCountdownDisplay">--:--:--</div>
    </div>

    <!-- AI Shelf Life Progress Bar -->
    <div class="ai-shelf-card">
      <div class="ai-header-badge">
        <span class="ai-pill">✨ AI Shelf-Life Assessment</span>
        <span style="font-size: 0.72rem; color: #166534; font-weight: 600;">Status: Verified Fresh</span>
      </div>

      <div class="progress-bar-bg">
        <div class="progress-bar-fill" id="countdownProgressBar" style="width: 100%;"></div>
      </div>

      <div class="shelf-meta">
        <span>🕒 Prepared / Logged: Just now</span>
        <span>🛡️ Expiry: ${data.formattedExpiryDate} ${data.formattedExpiryTime}</span>
      </div>
    </div>

    <!-- WhatsApp Broadcast Simulation Card -->
    <div class="wa-card">
      <div class="wa-header">
        <div class="wa-sender">
          <div class="wa-avatar">🍽️</div>
          <div>
            <div class="wa-name">SmartPlate AI: NSS Volunteer Network</div>
            <div class="wa-status"><span class="pulse-dot" style="width:6px; height:6px;"></span> 45 volunteers active</div>
          </div>
        </div>
        <div style="font-size: 0.72rem; background: rgba(255,255,255,0.15); padding: 2px 7px; border-radius: 4px;">Verified Broadcast</div>
      </div>

      <div class="wa-body">
        <div class="wa-bubble">
          <!-- Photo Thumbnail inside WhatsApp message -->
          <img src="${data.photo}" alt="Surplus meal" class="wa-bubble-img">
          
          <div class="wa-bubble-header">
            <span>🚨</span>
            <span>SMARTPLATE AI SURPLUS ALERT</span>
          </div>
          <div class="wa-content-line">🍲 <b>Item:</b> ${escapeHtml(data.item)}</div>
          <div class="wa-content-line">📦 <b>Quantity:</b> ${escapeHtml(data.quantity)}</div>
          <div class="wa-content-line">🏷️ <b>Category:</b> ${escapeHtml(data.rule.label)}</div>
          <div class="wa-content-line">📍 <b>Pickup:</b> ${escapeHtml(data.location)}</div>
          <div class="wa-content-line">⏳ <b>Safe Until:</b> ${data.formattedExpiryTime} (~${data.expiryHours} hrs left)</div>
          <div class="wa-content-line" style="margin-top: 6px; color: #15803d; font-weight: 600;">
            🌱 Target SDG 2: Zero Campus Food Waste
          </div>
          
          <div class="wa-footer-info">
            <span>${data.currentTimeStr}</span>
            <span class="wa-ticks">✓✓</span>
          </div>
        </div>
      </div>

      <!-- WhatsApp Broadcast Actions -->
      <div class="wa-actions">
        <!-- Main Required Action Button -->
        <button type="button" class="btn-wa-broadcast" onclick="simulateWhatsAppBroadcast()">
          📲 Simulate WhatsApp Broadcast Alert
        </button>

        <div class="wa-actions-row">
          <button type="button" class="btn-wa-copy" onclick="copyBroadcast()">
            📋 Copy Alert
          </button>
          <button type="button" class="btn-wa-share" onclick="shareWhatsApp()">
            🌐 Open Web
          </button>
        </div>
      </div>
    </div>
  `;
}

// Real-time ticking live countdown timer
function startLiveCountdown(expiryDate) {
  if (activeCountdownInterval) {
    clearInterval(activeCountdownInterval);
  }

  function updateTimer() {
    const now = new Date().getTime();
    const distance = expiryDate.getTime() - now;
    const displayElement = document.getElementById("liveCountdownDisplay");
    const progressFill = document.getElementById("countdownProgressBar");

    if (!displayElement) return;

    if (distance <= 0) {
      clearInterval(activeCountdownInterval);
      displayElement.innerText = "00:00:00";
      displayElement.style.color = "#ef4444";
      if (progressFill) progressFill.style.width = "0%";
      showToast("⚠️ Safe consumption window has ended for this item!", "warning");
      return;
    }

    const hours = Math.floor(distance / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);

    const pad = (n) => (n < 10 ? "0" + n : n);
    displayElement.innerText = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

    // Optional progress percentage
    if (progressFill && currentActiveItemData) {
      const totalDuration = currentActiveItemData.expiryHours * 3600 * 1000;
      const percentage = Math.max(0, Math.min(100, (distance / totalDuration) * 100));
      progressFill.style.width = `${percentage}%`;
    }
  }

  updateTimer();
  activeCountdownInterval = setInterval(updateTimer, 1000);
}

// Simulate WhatsApp Broadcast Alert Button Trigger
function simulateWhatsAppBroadcast() {
  // Required toast notification message
  const exactMessage = "Successfully broadcasted alert with photo & location to NSS volunteers via WhatsApp!";
  showToast(`📲 <b>Broadcast Sent!</b><br>${exactMessage}`, "wa-toast");
}

// Reset Form & Results
function resetForm() {
  document.getElementById("surplusForm").reset();
  removeImage();
  updateCategoryChipUI("dry");

  if (activeCountdownInterval) {
    clearInterval(activeCountdownInterval);
    activeCountdownInterval = null;
  }

  const container = document.getElementById("resultsContainer");
  if (container) {
    container.innerHTML = `
      <div class="preview-placeholder">
        <div class="icon">🥗</div>
        <h3 style="font-size: 1.05rem; color: var(--text-main); margin-bottom: 6px;">Ready to Analyze Surplus</h3>
        <p style="font-size: 0.85rem; max-width: 320px; color: var(--text-muted);">
          Enter surplus meal details, optionally upload a photo, and click <b>Calculate Shelf-Life & Broadcast</b> to view the live volunteer dispatch & countdown!
        </p>
      </div>
    `;
  }
  showToast("Form reset successfully.", "info");
}

// Render dynamic surplus items table
function renderSurplusTable() {
  const tbody = document.getElementById("logsTableBody");
  if (!tbody) return;

  tbody.innerHTML = surplusLogs.map((log) => {
    const isClaimed = log.status.toLowerCase().includes("claimed");
    const expiryStr = log.expiryTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
    const photoUrl = log.photo || PRESET_PHOTOS["default"];

    return `
      <tr>
        <td>
          <div style="display: flex; align-items: center;">
            <img src="${photoUrl}" alt="${escapeHtml(log.item)}" class="table-food-thumbnail">
            <div>
              <strong>${escapeHtml(log.item)}</strong>
              <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(log.quantity)}</div>
            </div>
          </div>
        </td>
        <td>
          <span style="font-size: 0.8rem; text-transform: capitalize;">${log.category}</span>
        </td>
        <td>
          <span style="font-size: 0.8rem;">📍 ${escapeHtml(log.location)}</span>
        </td>
        <td>
          <strong style="color: ${isClaimed ? '#64748b' : '#15803d'}; font-size: 0.82rem;">${expiryStr}</strong>
        </td>
        <td>
          <span class="badge-status ${isClaimed ? 'claimed' : 'available'}">${log.status}</span>
        </td>
        <td>
          <button 
            type="button" 
            class="btn-claim" 
            onclick="claimFoodItem(${log.id})" 
            ${isClaimed ? 'disabled' : ''}>
            ${isClaimed ? '✓ Claimed' : 'Claim Food'}
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

// Interactive volunteer claim toggle
function claimFoodItem(id) {
  const item = surplusLogs.find(x => x.id === id);
  if (item && !item.status.includes("Claimed")) {
    item.status = "Claimed by Volunteer";
    renderSurplusTable();
    showToast(`✅ "${item.item}" marked as claimed by volunteer team!`, "success");
  }
}

// Copy WhatsApp Alert to Clipboard
function copyBroadcast() {
  if (!lastGeneratedBroadcast) {
    showToast("Please generate an alert first!", "warning");
    return;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(lastGeneratedBroadcast).then(() => {
      showToast("📋 Alert text copied to clipboard!", "success");
    }).catch(() => {
      fallbackCopy(lastGeneratedBroadcast);
    });
  } else {
    fallbackCopy(lastGeneratedBroadcast);
  }
}

function fallbackCopy(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
  showToast("📋 Alert text copied to clipboard!", "success");
}

// Open WhatsApp Web with pre-filled message
function shareWhatsApp() {
  if (!lastGeneratedBroadcast) {
    showToast("Please generate an alert first!", "warning");
    return;
  }
  const encodedText = encodeURIComponent(lastGeneratedBroadcast);
  const waUrl = `https://api.whatsapp.com/send?text=${encodedText}`;
  window.open(waUrl, '_blank');
}

// Clean Toast Generator
function showToast(message, type = "info") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  let toastClass = "toast";
  if (type === "success") toastClass += " success";
  if (type === "wa-toast") toastClass += " wa-toast";

  toast.className = toastClass;
  toast.innerHTML = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Utility: HTML Sanitizer
function escapeHtml(string) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(string));
  return div.innerHTML;
}
