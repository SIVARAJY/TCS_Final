#  AI Financial Crime Network Investigator

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B.svg)](https://streamlit.io/)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg)](https://tailwindcss.com/)
[![NetworkX](https://img.shields.io/badge/NetworkX-3.0%2B-orange.svg)](https://networkx.org/)
[![Google Gemini API](https://img.shields.io/badge/AI-Gemini_2.5_Flash-4285F4.svg)](https://ai.google.dev/)

An enterprise-grade financial crime intelligence platform designed for Financial Intelligence Units (FIUs), AML compliance officers, and forensic investigators. The system ingests up to 7 multi-relational financial entity datasets, constructs directed knowledge graphs, detects complex money laundering topologies (cycles, rapid movement, shared infrastructure, synthetic identities), and leverages Google Gemini to synthesize admissible case dossiers with competing hypotheses and cited evidence.

---

## Table of Contents

- [Architectural Overview](#-architectural-overview)
- [Two Application Frontends](#-two-application-frontends)
- [10 Core Forensic Detectors](#-10-core-forensic-detectors)
- [Supported 7-CSV Data Schemas](#-supported-7-csv-data-schemas)
- [Quick Start & Installation](#-quick-start--installation)
  - [Prerequisites](#prerequisites)
  - [Option A: Streamlit 7-CSV Network Investigator (Port 8501)](#option-a-streamlit-7-csv-network-investigator-port-8501)
  - [Option B: React + FastAPI Full-Stack Platform (Ports 5173 & 8000)](#option-b-react--fastapi-full-stack-platform-ports-5173--8000)
- [Project Directory Layout](#-project-directory-layout)
- [AI Case Reporting & Gemini Configuration](#-ai-case-reporting--gemini-configuration)
- [Deployment Guide](#-deployment-guide)

---

## Architectural Overview

The system operates across three core analytical layers without requiring any external database:

1. **Deterministic Multi-Entity Graph Engine (NetworkX)**:
   - Ingests accounts, customers, beneficiaries, merchants, hardware devices, and network IPs as typed nodes.
   - Preserves transaction attributes (`transaction_id`, `amount`, `timestamp`, `channel`) and relationship links (`USED_DEVICE`, `LOGGED_IP`, `BENEFICIARY_OF`, `OWNS_ACCOUNT`).
2. **Modular Anomaly & Syndicate Detectors**:
   - 10 standalone detector functions evaluating topological cycles, rapid velocity pass-throughs, funnel/dispersal hubs, beneficiary concentration, and shared infrastructure.
   - Graph bipartite clustering automatically groups multi-detector findings into cohesive syndicate investigation cases.
3. **Forensic Evidence Synthesis & AI Dossier (Gemini)**:
   - Synthesizes findings into cited, admissible FIU investigation reports.
   - Formulates competing hypotheses with confidence scores, evaluates legitimate commercial alternatives, and provides actionable compliance next steps.

---

## Two Application Frontends

| Platform | Address | Core Purpose |
| :--- | :--- | :--- |
| **Streamlit Network Investigator** | [http://localhost:8501](http://localhost:8501) | **Primary 7-CSV Upload Center**, PyVis physics simulation, Plotly 2D ego networks, account explorer, all 10 detector tabs, and instant demo dataset loader. |
| **React Enterprise Web App** | [http://localhost:5173](http://localhost:5173) | High-performance interactive 2D canvas, analyst role-based login (`Sarah Jenkins`, INV-4092), entity search tool, and expandable evidence dossiers. Powered by Tailwind CSS. |
| **FastAPI REST Backend** | [http://localhost:8000](http://localhost:8000) | Headless API endpoints providing graph serialization, case clustering, detector execution, and Gemini AI synthesis. Interactive docs at `/docs`. |

---

## 10 Core Forensic Detectors

All 10 detectors are implemented as separate, modular functions in `src/detectors/` and return a standardized finding schema.

| Pattern ID | Name & Module | Logic & Algorithmic Rationale | Severity & Scoring Policy |
| :---: | :--- | :--- | :--- |
| **G05** | **Shared Beneficiary**<br>`src/detectors/g05_shared_beneficiary.py` | Detects multiple unrelated accounts or customers funneling funds to the exact same external beneficiary/payee. | `HIGH` / `MEDIUM`<br>(Score: 62–78) |
| **G06** | **Shared Device**<br>`src/detectors/g06_shared_device.py` | Detects multi-accounting from identical hardware fingerprints. *Strictly capped at Low/Medium risk policy.* | **Capped at `LOW` / `MEDIUM`**<br>(Score: 32–48, **never Critical**) |
| **G07** | **Shared IP**<br>`src/detectors/g07_shared_ip.py` | Identifies concentrated sessions originating from the exact same network IP. *Strictly capped at Low/Medium risk policy.* | **Capped at `LOW` / `MEDIUM`**<br>(Score: 28–42, **never Critical**) |
| **T06** | **Rapid Fund Movement**<br>`src/detectors/t06_rapid_fund_movement.py` | Simple time logic identifying accounts where incoming deposits are moved out within $\le 2$ hours (turnover ratio $\ge 80\%$). | `CRITICAL` / `HIGH`<br>(Score: 84–94) |
| **T08** | **Circular Transactions**<br>`src/detectors/t08_circular_transactions.py` | Uses `nx.simple_cycles` on the directed transaction graph to discover closed round-trip money loops (lengths 3–7). | `CRITICAL`<br>(Score: 96) |
| **A07** | **Funnel Account**<br>`src/detectors/a07_funnel_account.py` | In-degree count analysis: identifies central aggregation hubs receiving inflows from $\ge 3$ distinct source accounts. | `HIGH` / `MEDIUM`<br>(Score: 68–86) |
| **A09** | **Dispersal Account**<br>`src/detectors/a09_dispersal_account.py` | Out-degree count analysis: identifies dispersal hubs rapidly distributing funds to $\ge 3$ distinct destination endpoints. | `HIGH` / `MEDIUM`<br>(Score: 68–86) |
| **K03** | **Reused Contact Info**<br>`src/detectors/k03_reused_contact_info.py` | Pandas `groupby` across `phone_number`, `email`, and `tax_id` to uncover shared synthetic identity clusters. | `HIGH` / `MEDIUM`<br>(Score: 65–88) |
| **D04** | **New Device**<br>`src/detectors/d04_new_device.py` | Set comparison between historical baseline hardware and active session device logs to flag account takeovers. | `HIGH` / `MEDIUM`<br>(Score: 60–75) |
| **B02** | **Beneficiary Concentration**<br>`src/detectors/b02_beneficiary_concentration.py` | Single formula: $\frac{\text{Dominant Payee Outflow}}{\text{Total Account Outflow}} \ge 0.70$ (minimum \$5,000 threshold). | `HIGH` / `MEDIUM`<br>(Score: 68–82) |

### Standardized Finding Output Schema

Every detector returns records strictly matching this contract:

```json
{
  "finding_id": "FND-T08-001",
  "pattern_id": "T08",
  "pattern_name": "Circular Transactions",
  "severity": "CRITICAL",
  "risk_score": 96,
  "score_reasons": {
    "cycle_node_count": 3,
    "closed_money_ring": true,
    "cycled_volume_total": 45000.0,
    "topological_pattern": "Elementary directed cycle",
    "base_risk": 96
  },
  "entities": ["ACC-101", "ACC-102", "ACC-103"],
  "transaction_ids": ["TXN-101", "TXN-102", "TXN-103"],
  "evidence": [
    "Loop Trajectory: ACC-101 → ACC-102 → ACC-103 → ACC-101",
    "Ring Participants: 3 distinct accounts",
    "Total Cycled Capital: $45,000.00"
  ],
  "alternative_explanation": "Corporate treasury cash pooling or intercompany debt netting.",
  "recommended_review": "Subpoena full account ledgers and verify underlying commercial contracts."
}
```

---

## Supported 7-CSV Data Schemas

The platform accommodates flexible column names, auto-resolves common aliases, tolerates missing optional fields, and **gracefully runs analysis on partial uploads** without requiring a database.

1. **`transactions.csv`**:
   - *Required*: `transaction_id`, `source_account_id`, `target_account_id`, `amount`, `timestamp`
   - *Optional*: `channel`, `currency`, `status`
2. **`customers.csv`**:
   - *Required*: `customer_id`, `full_name`, `risk_rating`
   - *Optional*: `phone_number`, `email`, `tax_id`, `address`
3. **`accounts.csv`**:
   - *Required*: `account_id`, `customer_id`, `account_type`, `balance`
   - *Optional*: `opened_date`, `status`
4. **`beneficiaries.csv`**:
   - *Required*: `account_id`, `beneficiary_account`, `name`
   - *Optional*: `relationship`, `added_date`
5. **`merchants.csv`**:
   - *Required*: `merchant_id`, `merchant_name`, `risk_level`
   - *Optional*: `category`, `registration_number`
6. **`device_activity.csv`**:
   - *Required*: `device_id`, `customer_id` (or `account_id`), `ip_address`, `location`
   - *Optional*: `timestamp`, `device_type`, `user_agent`
7. **`fraud_alerts.csv`**:
   - *Required*: `alert_id`, `entity_id`, `alert_type`, `severity`
   - *Optional*: `timestamp`, `status`, `notes`

---

## Quick Start & Installation

### Prerequisites

- **Python 3.10+** (Python 3.12 recommended)
- **Node.js 18+** & npm (for React frontend)

### Option A: Streamlit 7-CSV Network Investigator (Port 8501)

The fastest way to test file uploads, graph explorer, and all 10 detectors:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (optional Gemini API key)
cp .env.example .env

# 3. Launch the Streamlit application
streamlit run app.py
```

- Open **[http://localhost:8501](http://localhost:8501)** in your browser.
- Click **" Load 7 Pre-Planted Demo CSVs"** to immediately populate the workspace with planted money laundering rings, or drag-and-drop your own files in the **CSV Upload Center**.

### Option B: React + FastAPI Full-Stack Platform (Ports 5173 & 8000)

For the interactive Web canvas with analyst login and Tailwind CSS UI:

```bash
# Terminal 1: Start Backend API
cd backend
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000

# Terminal 2: Start Frontend Application
cd frontend
npm install
cp .env.example .env
npm run dev
```

- Open **[http://localhost:5173](http://localhost:5173)**.
- Default Analyst Credentials:
  - **Email**: `investigator@fincrime.org`
  - **Password**: `investigator123`
  - *(Alternate demo accounts for Elena Rostova and Marcus Chen are selectable on the login screen)*.

---

## Project Directory Layout

```text
├── app.py                     # Main Streamlit 7-CSV Network Investigator app
├── requirements.txt           # Python dependencies (NetworkX, Streamlit, Plotly, PyVis, etc.)
├── .env.example               # Environment template (GEMINI_API_KEY)
├── sample_data/               # Pre-planted 7 synthetic CSV files exercising all 10 detectors
│   ├── transactions.csv
│   ├── customers.csv
│   ├── accounts.csv
│   ├── beneficiaries.csv
│   ├── merchants.csv
│   ├── device_activity.csv
│   └── fraud_alerts.csv
├── src/
│   ├── loader.py              # CSV ingestion, header normalization & validation engine
│   ├── graph_builder.py       # NetworkX multi-entity graph, Plotly & PyVis visualizers
│   ├── investigation.py       # Case clustering, evidence packages & Gemini report synthesis
│   └── detectors/             # 10 modular detector implementations
│       ├── __init__.py        # Central detector registry & execution runner
│       ├── g05_shared_beneficiary.py
│       ├── g06_shared_device.py
│       ├── g07_shared_ip.py
│       ├── t06_rapid_fund_movement.py
│       ├── t08_circular_transactions.py
│       ├── a07_funnel_account.py
│       ├── a09_dispersal_account.py
│       ├── k03_reused_contact_info.py
│       ├── d04_new_device.py
│       └── b02_beneficiary_concentration.py
├── backend/                   # FastAPI REST API backend
│   ├── main.py                # FastAPI routes (/api/graph, /api/cases, /api/auth)
│   ├── detectors.py           # Graph analytics & scoring
│   ├── llm.py                 # Gemini integration & cited narrative generation
│   └── data_gen.py            # Synthetic ring generator
└── frontend/                  # React + Vite web client
    ├── src/
    │   ├── App.jsx            # Main graph investigation canvas & dossier panel (Tailwind CSS)
    │   ├── LoginPage.jsx      # Analyst authentication portal with demo profiles
    │   ├── api.js             # API client bindings
    │   └── index.css          # Tailwind CSS v4 styling & frosted glass panels
    ├── package.json
    └── vite.config.js
```

---

##  AI Case Reporting & Gemini Configuration

To enable automated AI narrative synthesis:

1. Obtain a Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
2. Add it to your `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```
3. If no API key is provided, the platform automatically utilizes a deterministic template fallback that compiles cited hypotheses and regulatory next steps directly from the gathered evidence.

---

## 🚢 Render & Cloud Deployment Guide

The repository includes a ready-to-deploy [`render.yaml`](render.yaml) blueprint and root [`requirements.txt`](requirements.txt), allowing instant deployment on [Render](https://render.com).

### Method 1: 1-Click Render Blueprint (Recommended)

1. Push your repository to GitHub.
2. Sign in to your [Render Dashboard](https://dashboard.render.com).
3. Click **New +** → **Blueprint**.
4. Select your GitHub repository (`TCS_Final`).
5. Render reads [`render.yaml`](render.yaml) and automatically configures:
   - **`fincrime-network-investigator`** (Streamlit Web Service on Python 3.11)
   - **`fincrime-api`** (FastAPI Backend Web Service)
   - **`fincrime-dashboard`** (React + Tailwind Static Site linked to the backend)
6. Fill in your `GEMINI_API_KEY` when prompted and click **Apply**.

---

### Method 2: Deploy Streamlit App Manually on Render

If you only want the standalone 7-CSV interactive Streamlit investigator:

1. Click **New +** → **Web Service** in Render.
2. Connect your GitHub repository.
3. Configure settings:
   - **Name**: `fincrime-investigator`
   - **Runtime**: `Python 3`
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `OPENBLAS_NUM_THREADS`: `1`
   - `GEMINI_API_KEY`: *(Your Google AI Studio API Key)*
   - `GEMINI_MODEL`: `gemini-2.5-flash`
5. Click **Create Web Service**. Render will provision your app with a public `https://<service-name>.onrender.com` URL.

---

### Method 3: Deploy Full-Stack App (FastAPI + React) on Render

#### Step A: FastAPI Backend (Web Service)
1. Click **New +** → **Web Service**.
2. Connect repo and set:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Environment Variables:
   - `PYTHON_VERSION`: `3.11.9`
   - `OPENBLAS_NUM_THREADS`: `1`
   - `GEMINI_API_KEY`: *(Your key)*
4. Deploy and copy your backend URL (e.g. `https://fincrime-api.onrender.com`).

#### Step B: React Frontend (Static Site)
1. Click **New +** → **Static Site**.
2. Connect repo and set:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
3. Under **Redirects/Rewrites**:
   - Source: `/*`
   - Destination: `/index.html`
   - Action: `Rewrite`
4. Environment Variables:
   - `VITE_API_URL`: `https://fincrime-api.onrender.com` (from Step A)
5. Click **Create Static Site**.

---

### Other Cloud Platforms

- **Streamlit Community Cloud**:
  - Connect your GitHub repo, select `app.py`, and set `GEMINI_API_KEY` in *App Settings → Secrets*.
- **Vercel / Netlify (Frontend)**:
  - Root directory: `frontend`
  - Build command: `npm run build`
  - Output directory: `dist`
  - Environment variable: `VITE_API_URL=https://<your-backend-url>`

---

##  License

MIT License. Developed for advanced financial crime network intelligence and AML compliance analytics.
