***

# SafePassage – Bihar Travel Safety Edition

## DLW Track: Public/Community Safety (Low-Connectivity Travel in Bihar, India)

**Hackathon:** DLW Track 2026
**Date:** March 2026
**Track Focus:** Public Safety – Emergency Response \& Proactive Monitoring

***

## 🎯 Executive Summary

### One-Liner

**SafePassage** – An AI-powered mobile travel safety app that provides proactive risk assessment, connectivity-aware emergency detection, and offline crisis guidance for travelers in low-connectivity regions of **Bihar, India** (e.g., rural Gaya, Jamui, Aurangabad, Kaimur).

### The Problem

Travelers and field workers moving through rural Bihar face critical safety gaps that current tools do not address.

- No proactive risk awareness about specific **districts / blocks / routes**.
- Emergency detection fails when people go **offline** in high‑risk, low‑tower areas.
- During emergencies with **no internet**, travelers lack crisis protocols, local emergency numbers, and navigation.
- Emergency contacts and authorities often learn about incidents **hours or days too late**.

When a solo traveler visits Bodh Gaya and then remote forested areas of Gaya and Aurangabad, there is no system that combines **risk prevention, connectivity-aware monitoring, and offline emergency support**. Delayed reporting and poor situational awareness allow emergencies to escalate.

### The Solution

SafePassage delivers a **three‑pillar safety system** that works across online and offline phases:

1. **PREVENTION** – AI-powered risk analysis of travel itineraries in Bihar before departure.
2. **CURE** – Automated emergency detection when travelers go offline longer than expected in high‑risk parts of Bihar.
3. **MITIGATION** – On-device AI crisis guidance with step‑by‑step protocols that work entirely offline.

The mobile app is built with **React Native (Expo)** and is designed to operate for days or weeks in zero connectivity while maintaining smart emergency escalation.

***

## 👥 Target Audience

### Primary Users

- Solo travelers and backpackers exploring **Bihar** (e.g., Bodh Gaya, Rajgir, Nalanda plus nearby rural areas).
- Domestic tourists from other Indian states visiting pilgrimage and heritage sites, then branching into **rural/forest areas**.
- Field staff and volunteers (NGOs, health workers, surveyors) operating in **low‑tower regions**.
- Digital nomads / remote workers staying in Bihar for extended periods with **unreliable internet**.

Key characteristics:

- Ages 22–45, smartphone owners, comfortable with apps.
- Travel by **trains, buses, shared jeeps, and motorbikes** in semi‑urban and rural Bihar.
- Often alone or in small groups, with limited local contacts.
- Face **language barriers** (non‑Hindi speakers) and unfamiliar emergency systems.


### Secondary Stakeholders

- **Emergency Contacts** – Family/friends elsewhere in India/abroad needing timely, actionable alerts.
- **Local Authorities in Bihar** – Police stations, GRP (railway police), district hospitals, 112 emergency response.
- **Travel / Social Organizations** – NGOs, travel operators, hostels in Patna/Bodh Gaya wanting safer guest experiences.[^1]

***

## 🌍 Use Cases \& Scenarios (Bihar-Focused)

### Scenario 1 – Solo Backpacker in Rural Gaya \& Aurangabad

**Background:** Aarti, 27, solo traveler from Bengaluru, plans a 6‑day trip: Patna → Bodh Gaya → rural Gaya → Aurangabad district (waterfalls, hill temples). Connectivity is patchy outside major towns.[^1]

#### PREVENTION Phase

- Aarti uploads her **Bihar itinerary PDF** into SafePassage mobile app.
- AI analyzes each location against:
    - State and district crime statistics (e.g., theft, harassment),
    - Travel advisories and news on bandhs, Naxal incidents,
    - **Connectivity maps** (tower density and known “no‑signal” stretches).
- Results:
    - Patna \& Bodh Gaya – **MODERATE** risk (petty theft in crowded areas; good connectivity).
    - Rural Gaya forest area – **HIGH** risk (very limited towers, history of robberies on certain roads).
    - Remote waterfall area in **Aurangabad** – **HIGH (connectivity)** with 3–4 hour expected offline periods.
- She adjusts:
    - Avoids certain roads after dark,
    - Shares her itinerary and emergency contacts,
    - Downloads **Bihar offline map pack** (e.g., 150 MB) with emergency contacts for relevant districts.


#### CURE Phase

- Day 4: Aarti travels by shared jeep from Bodh Gaya to a remote waterfall near **Aurangabad**.
- Expected offline time on that segment from analysis: **90 minutes**.
- Actual: jeep breaks down in a low‑coverage stretch; Aarti’s device stays offline **4 hours**.
- Backend detects anomaly at ~3‑hour mark and sends SMS to her father:
> "SafePassage Alert: Aarti has been offline for 3 hours near Aurangabad district, Bihar.
> Expected reconnection: 1:00 PM. Last GPS: 24.xxxx, 84.xxxx. Next waypoint: [Homestay name]. Monitor for updates."
- At a configured escalation threshold (e.g., 6 hours), app sends a second alert including:
    - Nearest police station in Aurangabad,
    - Nearest community health center,
    - A pre‑filled **incident report** with Aarti’s route, last GPS, and medical info.[^1]


#### MITIGATION Phase

- Aarti realizes she is stranded, with no signal.
- Opens SafePassage → **Emergency → Vehicle Breakdown**.
- App shows offline protocol tailored to Bihar:
    - "Stay with vehicle; do not walk into forested areas."
    - "Use reflective items / flashlight to signal passing vehicles."
    - "Nearest town: [Local town], 18 km NE."
- On‑device LLM personalizes:
    - "Aarti, you’re on the road between Bodh Gaya and [waterfall name]. Your homestay is expecting you by 6 PM; they can alert local authorities if you don’t arrive."
- She logs photos and a voice note. When she later reconnects in town, SafePassage auto‑sends the report to her father and (if configured) to local police email/WhatsApp channel.[^1]

***

### Scenario 2 – Digital Nomad in Remote Champaran \& Jamui

**Background:** Rohan, 32, remote worker, spends a month in **West Champaran (Valmiki Tiger Reserve area) and Jamui** district for nature and rural homestays.

#### PREVENTION Phase

- Rohan imports his 14‑day Bihar itinerary (multiple villages in West Champaran, Jamui).
- Risk analysis shows:
    - Around **40% of his route** will be offline (forest and hill areas).
    - Certain stretches near forests have **SEVERE connectivity risk** plus wildlife and night‑time safety issues.
- App recommends:
    - Download **Hindi + local language phrase packs**,
    - Set daily check‑ins at **12 PM and 7 PM** via SafePassage.


#### CURE Phase

- Day 7: Rohan goes trekking near a hill in **Jamui** and misses both check‑ins.
- Backend sees no heartbeats for 12+ hours in an area where expected offline duration was 2–3 hours.
- It triggers an alert to his sister:
    - "Rohan has missed 2 check‑ins near Jamui district, Bihar. Last GPS: [coords]. Expected offline period: 3 hours; offline now: 12 hours."
- Escalation adds:
    - Local police station and forest department contacts,
    - Homestay contact where he is staying.


#### MITIGATION Phase

- Rohan gets lost on a trail; zero signal.
- Opens SafePassage → **Emergency → Lost**.
- Offline map shows:
    - He’s ~3.2 km from his village homestay.
    - Arrow pointing downhill toward the village.
- LLM guidance:
    - "Follow the path downhill toward [village name]. Avoid entering dense forest off-path. Use phrase helper if you meet locals."
- Phrase helper plays local Hindi phrases like:
    - "Main raasta bhatak gaya hoon. Kya aap madad kar sakte hain?"
(“I am lost. Can you help?”)
- He reaches the village, reconnects, and cancels the alert.

***

## 🛡️ Core Features – Three Pillars

### Pillar 1: PREVENTION – Proactive Risk Analysis (Bihar Itineraries)

#### User Story

> As a traveler planning a trip across low-connectivity regions of **Bihar**, I want to understand the safety risks and connectivity challenges of my planned route so I can make informed decisions and prepare appropriately.[^1]

#### What It Does

**Input:**

- User uploads itinerary: PDF, Excel, CSV, Google Sheets, or manual entry (e.g., Patna → Gaya → Bodh Gaya → rural village in Aurangabad → Jamui).[^1]

**AI Processing (Backend):**
Cloud LLM (e.g., GPT‑4 / Claude) parses into structured format:

- Dates, times, duration of stay per stop.
- Place names mapped to coordinates (Patna, Bodh Gaya, village in Aurangabad, etc.).
- Transport segments (train, bus, jeep).
- Expected connectivity patterns using cell‑tower data and route type.[^1]

**Risk Analysis Engine (Bihar-adapted):**


| Risk Factor | Bihar-Relevant Data Sources (Example) | Output |
| :-- | :-- | :-- |
| Crime Risk | Bihar police / NCRB district stats, crowdsourced indices | Theft/assault/scam risk |
| Health Risk | Local hospital density, recent outbreaks, PHC proximity | Medical preparedness |
| Infrastructure Risk | Road quality, accident reports, night‑time safety | Disruption likelihood |
| Connectivity Risk | OpenCellID / tower data per route / village | Expected offline duration |
| Political/Social | News on bandhs, protests, Naxal/militancy alerts | Conflict/instability risk |
| Environmental Risk | Flood/drought history, forest proximity (wildlife, landslides) | Environmental hazards |

**Outputs:**

- **Risk score per location**: SEVERE / HIGH / MODERATE / LOW with explanation.
- **Connectivity forecast**: For each leg, expected offline windows (e.g., “Gaya → Aurangabad: up to 3h offline”).
- **Actionable recommendations** (Bihar-tuned):
    - "Avoid traveling this rural stretch after 7 PM."
    - "Download offline maps for Aurangabad blocks X, Y."
    - "Inform homestay and family before entering forest area."
- **Emergency contacts**: Bihar‑specific:
    - Nearest police station, PHC/CHC, district hospital, emergency helplines (112, 108), plus embassy if foreigner.[^1]

**Backend Sync:**

- Complete itinerary and risk report stored in **PostgreSQL**.
- Risk and connectivity expectations feed **Pillar 2 monitoring** and **Pillar 3 protocols**.[^1]


#### Mobile \& Backend Tech (Pillar 1)

**Mobile (React Native + Expo)**

- File upload: `react-native-document-picker`.
- PDF parsing: `react-native-pdf` or custom backend parsing.
- Excel/CSV: `xlsx` + upload via REST.
- UI: `react-native-paper` for lists, cards, dialogs.
- Map: `react-native-mapbox-gl` or MapLibre for risk pins and Bihar maps.
- State: React Context + `@react-native-async-storage/async-storage` for local persistence.

**Backend**

- Node.js + Express on AWS Lambda.
- PostgreSQL for users, itineraries, locations, risk tables.[^1]
- Redis (optional) for caching external responses.
- OpenAI / Anthropic API for itinerary parsing and summarization.

***

### Pillar 2: CURE – Connectivity-Aware Emergency Detection

#### User Story

> As an emergency contact for a traveler in rural Bihar, I want to be automatically notified if they stay offline longer than expected in a high‑risk area so I can act before it’s too late.[^1]

#### What It Does

**Intelligent Monitoring System:**

- SafePassage predicts when the traveler **should** reconnect based on Bihar itinerary segments and cell‑tower density.
- It only alerts when actual offline duration significantly exceeds those expectations, reducing false alarms.[^1]

**Risk-Adaptive Thresholds (same logic, Bihar context):**


| Location Risk | Expected Offline Window | Alert Threshold | Escalation Threshold |
| :-- | :-- | :-- | :-- |
| LOW (city/town) | up to 4 hours | +50% (6 hours) | +150% (10 hours) |
| MODERATE (mixed) | up to 2 hours | +50% (3 hours) | +150% (5 hours) |
| HIGH (remote roads) | up to 1 hour | +50% (90 minutes) | +100% (2 hours) |
| SEVERE (deep rural/forest) | up to 30 minutes | +30% (40 minutes) | +60% (48 minutes) |

**Three-Stage Alert System (Bihar-specific content):**

1. **Stage 1 – Initial Alert**
    - SMS + push to all emergency contacts.
    - Message example:
> "SafePassage Alert: Aarti has been offline for 3 hours near Aurangabad, Bihar.
> Expected reconnection: 1:00 PM. Last GPS: [coords]. Next waypoint: [homestay]. Try calling her and monitor for reconnection."
2. **Stage 2 – Escalation**
    - Enhanced alert with **local authority** information:
        - Nearest police station (name, address, phone),
        - District control room, 112/108 numbers,
        - Pre‑filled PDF incident report with:
            - Traveler identity, last known location, itinerary in Bihar, medical info, emergency contacts.[^1]
3. **Stage 3 – Auto-Reconnection**
    - When traveler comes back online, all contacts receive:
> "[Name] is now online near [Location]. Offline duration: X hours. Status: SAFE / CHECK-IN NEEDED."
    - Incident logged for analytics.[^1]

#### Mobile \& Backend Tech (Pillar 2)

**On Mobile**

- Heartbeat pings every 10 minutes while online:
    - Implemented via **Expo Background Fetch**.
    - Payload: `userId`, `timestamp`, GPS coordinates, battery, connectivity status.[^1]

**Backend Monitoring**

- AWS Lambda (cron via EventBridge) every 5 minutes:
    - Reads `heartbeats` and `itineraries` from PostgreSQL.
    - Computes offline duration vs expected offline window per segment.
    - Triggers alerts using:
        - **Twilio** for SMS,
        - **Firebase Cloud Messaging (FCM)** for push,
        - Optional email (SendGrid) for detailed escalation reports.[^1]

**Core Dependencies**

- `expo` / `react-native`
- `expo-background-fetch`, `expo-task-manager`
- `@react-native-community/netinfo` for connectivity status
- `@react-native-community/geolocation` or `expo-location`
- Backend: Node.js, Express, PostgreSQL client (`pg`), Twilio SDK, Firebase Admin SDK.[^1]

***

### Pillar 3: MITIGATION – Offline Crisis Guidance with On-Device AI

#### User Story

> As a traveler in rural Bihar with no internet, I want immediate, personalized guidance on what to do so I can stay calm, take the right actions, and document evidence for authorities.[^1]

#### What It Does

**Always-Available Emergency Button**

- Large red button on mobile home screen.
- Works even when offline; opens full‑screen emergency mode with large scenario icons.[^1]

**Pre-Loaded Crisis Scenarios (adapted to Bihar)**

1. Lost / Disoriented (e.g., off a rural road or forest path)
2. Theft / Robbery (bus/train/market)
3. Physical Assault / Harassment
4. Medical Emergency
5. Flood / Natural Disaster (e.g., monsoon flooding in North Bihar)
6. Vehicle Breakdown (rural highways)
7. Detained by Authorities (police/railway checks)
8. Witness to Crime

Each stored as structured JSON/SQLite entries with steps, phrase helpers, and calm messages.[^1]

**Personalization with On-Device LLM**

- Model: **Microsoft Phi‑3 Mini** (3.8B, 4‑bit) or fallback **Llama 3.2 1B**; quantized and bundled locally.[^1]
- Input context:
    - User’s name,
    - Current GPS,
    - Planned Bihar itinerary (nearest planned waypoint),
    - Known POIs: nearest police station/hospital/homestay.[^1]
- Output:
    - Personalized text:
        - "Aarti, walk 0.5 km back towards [village name]; do not take side trails into the forest."
        - "Nearest CHC is [Name], 4.2 km east; follow the main road downhill."
    - Calm guidance:
        - "You’re doing well. Focus on staying safe and visible."[^1]

**Offline Maps \& Navigation**

- Bihar regional offline map in **MBTiles** format (vector tiles).
- GPS via native APIs; works fully offline.
- App shows:
    - Blue dot for user, pins for safe locations (police, hospitals, homestays).
    - Arrow/distance to nearest safe location.[^1]

**Incident Logging**

- Photos of scene, vehicles, injuries using `expo-camera` or `react-native-camera`.
- Voice notes via `expo-av` or `react-native-audio`.
- Text notes and auto-tagged GPS + timestamp.
- Data stored locally (SQLite, encrypted); synchronized to backend when connectivity returns, and forwarded to emergency contacts / authorities.[^1]


#### Mobile \& On-Device Tech (Pillar 3)

**React Native / Expo**

- Emergency UI: standard RN screens + `react-native-paper` buttons.
- SQLite: `expo-sqlite` or `react-native-sqlite-storage` for protocols, incident logs.
- Offline maps: RN Mapbox/MapLibre with MBTiles integration.
- Camera \& audio: `expo-camera`, `expo-av`.

**On-Device LLM**

- Inference:
    - iOS: Core ML / ONNX Runtime.
    - Android: TensorFlow Lite.
- Packaged quantized model file (~600 MB–2 GB) in app assets or downloaded once as a “Bihar Safety AI Pack”.[^1]

Fallback if LLM absent/slow: use pre-scripted templates with variable substitution.

***

## 🏗️ Technical Architecture (Mobile-Centric)

### Mobile App (React Native + Expo)

- **Platforms:** iOS and Android.
- **Key packages:**
    - `expo`, `react-native`, `react-native-paper`, `@react-navigation/native`
    - `expo-document-picker`, `expo-file-system`
    - `expo-location`, `expo-background-fetch`, `expo-task-manager`
    - `expo-sqlite`, `@react-native-async-storage/async-storage`
    - Map: `@rnmapbox/maps` or MapLibre wrapper.[^1]


### Backend (Flask RESTful + PostgreSQL)

- **APIs:**
    - `/itinerary/upload` – parse \& store.
    - `/risk/analyze` – compute Bihar-specific risk \& connectivity.
    - `/heartbeat` – ingest device pings.
    - `/alerts` – generate \& log alerts.
    - `/incidents/sync` – sync offline incidents.[^1]
- **Services:**
    - Risk Analysis Service (uses GPT‑4/Claude + data sources).
    - Monitoring Service (cron) for CURE.
    - Alert Service (Twilio, FCM).

***

## 📦 Key Mobile Dependencies (Checklist)

To build the SafePassage **mobile app** with all described features:

- Core:
    - `expo`, `react-native`, `react-native-paper`, `react-navigation`
- Storage:
    - `@react-native-async-storage/async-storage`
    - `expo-sqlite`
- Location \& Background:
    - `expo-location`
    - `expo-background-fetch`
    - `expo-task-manager`
- Files \& Parsing:
    - `expo-document-picker`
    - Backend-based parsing for PDF/Excel via Node.js libs (`pdf-parse`, `xlsx`)
- LLM Inference (if on-device):
    - Platform-specific native bindings to Core ML / TFLite (via custom native modules)


***
