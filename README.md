<div align="center">

# 🛡️ Safe Passage

**AI-Powered Traveler Safety Companion for Low-Connectivity Environments**

[![React Native](https://img.shields.io/badge/React%20Native-0.81.5-blue.svg)](https://reactnative.dev/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9.2-blue.svg)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

[Features](#-key-features) • [Architecture](#-architecture) • [Quick Start](#-quick-start) • [Documentation](#-documentation)

</div>

---

## 📖 Overview

**Safe Passage** is an AI-powered traveler safety solution designed to proactively assess risk, monitor traveler well-being, and respond intelligently in low-connectivity environments. Built for solo travelers venturing into remote or high-risk areas, the system provides a comprehensive safety net through intelligent risk prevention, real-time monitoring, and automated emergency response.

### The Problem

Travelers in remote areas face unique challenges:
- **Unpredictable connectivity** in rural or mountainous regions
- **Delayed emergency response** when communication is lost
- **Lack of proactive risk assessment** before entering dangerous areas
- **Limited local safety knowledge** about destinations

---

## Key Features

### Intelligent Risk Assessment
- **AI-Powered Itinerary Analysis**: Upload travel plans (PDF/DOCX) and receive category-specific risk assessments
- **GPT-5.2 & GPT-4.1-nano Integration**: Multi-agent architecture for comprehensive risk evaluation
- **Actionable Insights**: Detailed mitigation strategies for crime, infrastructure, health, political, and environmental risks
- **Travel Risk Scoring**: Overall risk quantification with confidence intervals

### Predictive Connectivity Monitoring
- **Deterministic Connectivity Model**: Regional cellular coverage prediction using real-world signal metrics
- **Expected Offline Duration**: Calculate anticipated connectivity loss based on destination coordinates
- **Smart Threshold Management**: Dynamic offline detection based on location risk profiles

### Heartbeat-Based Safety System
- **Background Health Signals**: Periodic location, battery, and timestamp transmission
- **Offline Anomaly Detection**: Automated escalation when travelers exceed expected offline thresholds
- **Historical Pattern Analysis**: User-specific baseline establishment for accurate anomaly detection
- **Privacy-Conscious Design**: Minimal data transmission with encrypted storage

### Multi-Channel Emergency Response
- **SMS Notifications**: Twilio-powered emergency contact alerts with last-known location
- **Telegram Bot Integration**: Real-time emergency contact activation and notifications
- **Automated Escalation**: Triggered alerts to local authorities with structured safety data
- **Manual SOS Trigger**: User-initiated emergency broadcast with contextual information

###  Offline-First Mobile Experience
- **React Native + Expo**: Cross-platform mobile app (iOS/Android)
- **SQLite Local Storage**: Complete offline data persistence
- **Background Task Execution**: Heartbeat transmission even when app is closed
- **Progressive Enhancement**: Full functionality offline with sync when connected

---

## Architecture

Safe Passage follows a **multi-agent AI architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Mobile App (React Native)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Itinerary   │  │  Heartbeat   │  │  Emergency           │  │
│  │  Upload      │  │  Monitor     │  │  Dashboard           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                    SQLite (Offline-First)                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTPS / REST API
┌───────────────────────────────┴─────────────────────────────────┐
│                      Backend (Flask + Python)                    │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │  Risk Engine         │  │  Connectivity Predictor        │  │
│  │  (GPT-5.2/4.1-nano)  │  │  (Regional Signal Data)        │  │
│  └──────────────────────┘  └────────────────────────────────┘  │
│  ┌──────────────────────┐  ┌────────────────────────────────┐  │
│  │  Heartbeat Monitor   │  │  Emergency Dispatcher          │  │
│  │  (APScheduler)       │  │  (Twilio + Telegram)           │  │
│  └──────────────────────┘  └────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ PostgreSQL (Supabase)
┌───────────────────────────────┴─────────────────────────────────┐
│                           Database Layer                         │
│  Users • Trips • Itineraries • Risk Reports • Heartbeats         │
│  Alerts • Incidents • Emergency Contacts • Traveler Status       │
└──────────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Frontend
- **Framework**: React Native 0.81.5 with Expo 54
- **Navigation**: Expo Router 6.0
- **Styling**: NativeWind (Tailwind CSS for React Native)
- **State Management**: AsyncStorage + SQLite
- **Network Detection**: NetInfo for connectivity awareness
- **Background Tasks**: Expo Background Fetch & Task Manager

#### Backend
- **Framework**: Flask 3.1.0 (Python 3.11+)
- **Database**: Supabase (PostgreSQL) with SQLAlchemy ORM
- **AI Models**: OpenAI GPT-5.2 (analysis) + GPT-4.1-nano (filtering)
- **Task Scheduling**: APScheduler 3.10.4
- **Validation**: Pydantic 2.11+
- **Notifications**: Twilio (SMS) + Telegram Bot API

#### Infrastructure
- **Containerization**: Docker + Docker Compose
- **WSGI Server**: Gunicorn 23.0.0
- **Email Validation**: email-validator 2.2.0
- **Document Parsing**: pdfplumber 0.10.3 + python-docx 1.1.2

---

## Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+ 
- **Docker** (optional, for containerized backend)
- **Expo CLI** (install via `npm install -g expo-cli`)
- **Supabase Account** (for database)
- **OpenAI API Key** (for AI features)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/safe-passage.git
cd safe-passage
```

### 2. Backend Setup

#### Option A: Docker (Recommended)

```powershell
# Copy environment template
Copy-Item backend/.env.example backend/.env

# Edit backend/.env with your credentials
# Then start the backend
docker compose up --build backend
```

Backend will be available at `http://localhost:5000`

#### Option B: Local Python Environment

```powershell
cd backend

# Create virtual environment
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Configure environment
Copy-Item .env.example .env
# Edit .env with your credentials

# Run Flask development server
flask run --host=0.0.0.0 --port=5000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with backend URL

# Start Expo development server
npm start
```

Scan QR code with Expo Go app (iOS/Android) or press:
- `a` for Android emulator
- `i` for iOS simulator
- `w` for web browser

### 4. Telegram Bot Setup (Optional)

```powershell
cd telegram-bot

# Create virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt

# Configure bot
Copy-Item .env.example .env
# Add TELEGRAM_BOT_TOKEN and database URI

# Run bot
python bot.py
```

---

## Documentation

### Core Systems

- **[Heartbeat System Guide](backend/HEARTBEAT.md)**: Backend integration and monitoring controls
- **[Heartbeat Frontend Integration](frontend/src/features/heartbeat/README.md)**: Mobile runtime and implementation
- **[Offline Storage Architecture](frontend/src/features/storage/README.md)**: SQLite schema and synchronization
- **[Backend API Documentation](backend/README.md)**: Complete API reference and smoke tests
- **[Telegram Bot Setup](telegram-bot/README.md)**: Emergency contact activation guide

### API Contracts

Comprehensive API contracts are documented in the `contracts/` directory:
- **Prevention**: Itinerary upload and risk analysis endpoints
- **Cure**: Heartbeat ingestion and monitoring APIs
- **Mitigation**: Emergency alert and incident management
- **Shared**: Authentication, user management, and common schemas

### Database Schema

Database schema and seed data are available in `contracts/db/`:
- `schema_outline.sql`: Complete PostgreSQL schema
- `seed_stage1_bootstrap_missing_status_*.sql`: Bootstrap data
- `seed_stage1_watchdog_*.sql`: Heartbeat monitoring configuration

---

## Testing

### Backend Tests

```powershell
cd backend
pytest tests/

# Run specific test suites
pytest tests/test_itinerary_analysis.py
pytest tests/test_connectivity_model.py
pytest tests/test_heartbeat_monitor.py
```

### Performance Tests

The backend includes a comprehensive performance test suite for heartbeat monitoring and emergency escalation systems:

```powershell
cd backend

# Run all performance tests
python run_performance_tests.py --all

# Run specific test categories
python run_performance_tests.py --load          # Heartbeat ingestion
python run_performance_tests.py --watchdog      # Watchdog scalability
python run_performance_tests.py --escalation    # Emergency escalation
python run_performance_tests.py --alerts        # Alert delivery

# View help and all options
python run_performance_tests.py --help
```

**What these tests measure:**
- ✓ Code correctness and algorithm logic
- ✓ Memory usage patterns
- ✓ Error handling robustness
- ✓ Concurrent execution behavior

**Important:** These tests use mocked I/O (in-memory database, intercepted network calls) to validate code quality.

**Test output:**
- JSON results: `backend/test_results/performance_YYYYMMDD_HHMMSS.json`
- HTML dashboard: `backend/test_results/performance_report.html`

### Frontend Type Checking

```bash
cd frontend
npm run typecheck
```

### Integration Tests

```powershell
# Run smoke test for complete user flow
cd backend
python tools/smoke_user_flow.py
```

---

##  Development Workflow

### Connectivity Predictor (Standalone Component)

The deterministic connectivity model can be used independently:

```python
from app.services.connectivity_predictor import predict_connectivity_for_latlon

result = predict_connectivity_for_latlon(25.6009, 85.1452)  # Bihar, India
print(f"Score: {result['connectivity_score']}")
print(f"Group: {result['connectivity_group']}")
print(f"Expected offline: {result['expected_offline_minutes']} minutes")
```

**Connectivity Bands**:
- `Poor`: 0-24 (High risk)
- `Average`: 25-49 (Moderate risk)
- `Good`: 50-74 (Low risk)
- `Excellent`: 75-100 (Minimal risk)

### Environment Configuration

Required environment variables for backend:

```env
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-key

# AI Models
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # Optional

# Notifications
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
TELEGRAM_BOT_TOKEN=...

# Configuration
APP_CONFIG=development  # or production
ENABLE_HEARTBEAT_SCHEDULER=1
HEARTBEAT_WATCHDOG_INTERVAL_MINUTES=5
```

### Docker Management Scripts

```powershell
# Start services
./scripts/backend-docker.ps1 -Action up

# Check status
./scripts/backend-docker.ps1 -Action status

# View logs
./scripts/backend-docker.ps1 -Action logs

# Stop services
./scripts/backend-docker.ps1 -Action down
```

---

## 📊 Project Structure

```
safe-passage/
├── backend/                    # Flask API server
│   ├── app/
│   │   ├── models/            # Database models (SQLAlchemy)
│   │   ├── routes/            # API endpoints
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # Business logic
│   │   │   ├── connectivity_predictor.py
│   │   │   ├── risk_engine.py
│   │   │   └── data/          # Signal metrics dataset
│   │   ├── tasks/             # Background jobs
│   │   └── utils/             # Shared utilities
│   ├── tests/                 # Unit and integration tests
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # React Native mobile app
│   ├── app/                   # Expo Router pages
│   │   ├── dashboard.tsx
│   │   ├── heartbeat.tsx
│   │   ├── trips/
│   │   └── emergency/
│   ├── src/
│   │   ├── features/          # Feature modules
│   │   ├── lib/               # API clients
│   │   └── shared/            # Shared components
│   └── package.json
│
├── telegram-bot/              # Emergency contact bot
│   ├── bot.py
│   └── requirements.txt
│
├── contracts/                 # API & DB contracts
│   ├── api/                   # OpenAPI specifications
│   └── db/                    # Database schemas
│
├── scripts/                   # Automation scripts
│   └── backend-docker.ps1
│
└── docker-compose.yml         # Container orchestration
```

---
