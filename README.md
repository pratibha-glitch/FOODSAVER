# SmartPlate AI — AI-Powered Campus Food Waste Reduction Platform

> **Tagline:** Turn Surplus Food into Shared Meals.  
> **Target Sustainable Development Goal:** UN SDG 2 — Zero Hunger.

**SmartPlate AI** is a production-ready, full-stack campus surplus food coordination web application designed for university canteens, hostel messes, and student volunteer networks (such as NSS / Green Brigade). It replaces guesswork with **AI-assisted food photo recognition**, **concurrency-protected volunteer dispatch**, **human-in-the-loop food safety verification**, and **honest database reporting**.

---

## 🌟 Key Features & Architectural Highlights

### 1. 🤖 AI Food Photo Assistant (Multimodal Vision)
- **Real Vision-Capable AI Integration:** Integrated with Google Gemini 1.5 Flash Vision API (`GEMINI_API_KEY`).
- **Strict Server-Side Schema Validation:** Validated with Python `jsonschema` ensuring structured, type-safe outputs (`food_name`, `category`, `visible_items_or_containers_count`, `approximate_quantity_range`, `confidence_score`, `confidence_reasoning`, `fields_requiring_staff_input`).
- **Honest Quantity Estimation:**
  - The system acknowledges that a 2D photograph **cannot** reveal exact mass or density.
  - Countable items or meal boxes are counted individually.
  - Bulk food (curries, rice) receives approximate portion ranges only when container boundaries are visible; otherwise, the system honestly flags the mass as unknown and requests scale measurement.
  - AI predictions are explicitly labelled in the UI as **AI Suggestions**, never verified facts.
- **Graceful Fallback:** If the external AI service is unavailable or `GEMINI_API_KEY` is not set, the platform falls back to an honest local heuristic engine with a clear notice. Canteen staff can always enter or correct details manually without being blocked.

### 2. 🛡️ Human-in-the-Loop Food Safety & Logistics
- **No Arbitrary Fixed Rules:** Food safety is not certified by an AI photograph.
- **Mandatory Staff Verification Checklist:** A listing cannot be published as `available` until canteen staff physically inspect and confirm:
  1. *Sensory Inspection:* Normal aroma, color, and fresh appearance.
  2. *Storage Temperature Check:* Proper hot-holding (>60°C), ambient covered, or chilled (<5°C) compliance.
  3. *Hygienic Handling Check:* Safe transport containers and clean utensils.
- **Logistical Pickup Window vs. Safety Expiration:** The system clearly distinguishes operational collection deadlines from biological safety determinations.

### 3. 🎯 Concurrency-Safe Volunteer Logistics (Race Condition Protection)
- **Lifecycle:** `Draft` → `Available` → `Claimed` → `Pickup in Progress` → `Collected` (plus `Cancelled` and `Expired`).
- **Atomic Concurrency Protection:** Conditional atomic SQLite updates (`UPDATE ... WHERE id = ? AND status = 'available'`) guarantee that if two volunteers attempt to claim the same meal simultaneously, only one succeeds; the second receives a clean conflict notification.
- **Full State Audit Trail:** Every status transition is logged in `status_audit_log` with the initiating user, timestamp, and audit notes.

### 4. 🧠 Meaningful AI Capabilities
- **Feature 1: Vision-Based Food Identification:** Detects food names, categories, and visual confidence.
- **Feature 2: Smart Volunteer Matching:** Uses deterministic eligibility rules (max concurrent pickup capacity, active availability) combined with location proximity and deadline windows to rank volunteers with **plain-language explanations**.
- **Feature 3: Urgency Prioritization:** Evaluates remaining operational window and flags urgent pickups (<45m critical, <90m high) with explicit food safety disclaimers.
- **Feature 4: AI Notification Writer:** Automatically drafts concise broadcast notifications derived strictly from verified database fields, including an optional WhatsApp Business formatted template preview.

### 5. 📊 Honest Dashboard Metrics & Defensible Impact Reporting
- **Separation of Units:** Confirmed collected quantities are separated strictly by unit (`kg`, `portions`, `boxes`). They are never mixed or aggregated misleadingly.
- **Defensible CO₂ Diversion:** Documented FAO methodology (1 kg diverted food waste avoids 2.5 kg CO₂-eq) applied exclusively to verified collected food in kilograms. Unclaimed listings are never counted as collected food.

---

## 👥 Role-Based Architecture & Demo Credentials

The platform includes pre-seeded demo accounts for instant evaluation:

| Role | Username / Email | Password | Details & Location |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` / `admin@smartplate.campus` | `AdminPassword123!` | System oversight, verification, metrics, audit logs |
| **Canteen Staff** | `staff_north` / `staff@smartplate.campus` | `StaffPassword123!` | Canteen Staff, Main Student Mess |
| **Canteen Staff** | `staff_central` / `staff2@smartplate.campus` | `StaffPassword123!` | Canteen Staff, Campus Dining Hall |
| **Verified Volunteer** | `volunteer_priya` / `volunteer@smartplate.campus` | `VolunteerPassword123!` | Verified Volunteer, Campus Central |
| **Verified Volunteer** | `volunteer_rohit` / `volunteer2@smartplate.campus` | `VolunteerPassword123!` | Verified Volunteer, Campus North |
| **Unverified Volunteer** | `volunteer_pending` / `volunteer.pending@smartplate.campus` | `VolunteerPassword123!` | Pending verification (Demonstrates authorization gate) |

> 💡 **Quick Switcher:** A demo switcher bar is pinned to the top of the application for one-click role switching during faculty presentations.

---

## 🛠️ Tech Stack & Architecture

- **Backend:** Python 3.13 + Flask 3.1
- **Database:** SQLite with WAL Mode, Foreign Keys enabled, and Atomic Transactions
- **Image Processing & Validation:** Pillow (PIL)
- **Schema Validation:** `jsonschema` (Draft 7)
- **AI Integration:** Google Gemini Multimodal Vision API (`gemini-1.5-flash`)
- **Frontend:** Responsive Vanilla HTML5, CSS3 Custom Properties (Eco-Friendly Green & Clean Warm Neutrals), Modular JavaScript ES6 Modules
- **Testing:** Python `unittest` test suite covering authentication, listings, claims concurrency, AI schema, and honest metrics.

---

## 🚀 Local Setup & Running Instructions

### 1. Prerequisites
- Python 3.10+ installed on your computer.

### 2. Install Dependencies
Open PowerShell or your terminal in the project directory:
```powershell
pip install flask python-dotenv requests pillow jsonschema
```

### 3. Environment Configuration
Copy the provided `.env.example` file to `.env`:
```powershell
copy .env.example .env
```
To enable live Google Gemini Cloud Vision:
1. Obtain a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Set your key in `.env`:
   ```ini
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```
*(Note: If left empty, SmartPlate AI runs in local heuristic demonstration mode without breaking or throwing unhandled errors).*

### 4. Run the Automated Test Suite
Verify that all 17 automated tests pass:
```powershell
python -m unittest discover tests
```
Expected output:
```text
Ran 17 tests in ...s
OK
```

### 5. Start the Application Server
```powershell
python app.py
```
Open your web browser and navigate to:
👉 **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**

---

## 🧪 Verified Workflows to Demonstrate

1. **AI Vision & Human Verification Workflow:**
   - Sign in as `staff_north`.
   - In "Canteen Staff Logging", click one of the quick presets (*Dal & Rice*, *Roti & Sabzi*, *Kheer*) or upload a food photo.
   - Observe the AI Assistant analyze the image and display confidence scores, visual reasoning, and fields requiring verification.
   - Note that publishing as "Available" is blocked until all 3 items of the **Mandatory Food Safety Checklist** are checked.
   - Publish the listing.

2. **Volunteer Discovery & Smart Matching:**
   - Switch to **Verified Volunteer** in the top bar.
   - In "Available Food Feed", view the published meal with live countdown badges.
   - Click "🎯 Volunteer Match" to view the smart volunteer matching ranking with plain-language explanations.

3. **Concurrency-Safe Claim & Physical Collection:**
   - As **Verified Volunteer**, click "🤝 Claim Food (1-Click)".
   - Under "My Claimed Pickups", click "🚶 Start Pickup" (updates status to *Pickup in Progress*).
   - Click "✓ Confirm Collection", enter the verified physical weight (e.g., `8.2 kg`), and confirm.

4. **Honest Reporting & Administrator Oversight:**
   - Switch to **Admin** in the top bar.
   - View the Admin Dashboard to see updated metrics: confirmed kg collected, completed pickups, and defensible CO₂ reduction calculation.
   - In "User Management", verify unverified volunteers with a single click.
   - In "System Audit Trail", inspect the tamper-evident log of every status transition.
