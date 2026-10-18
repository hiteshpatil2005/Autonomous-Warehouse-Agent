# WareBot AI — Autonomous Warehouse AGV Simulation Platform

WareBot AI is a full-stack autonomous mobile robot simulation platform built for academic research and industrial demonstrations. It features discrete-event physics, 4-directional A* pathfinding, transparent utility-based multi-factor decision dispatching, battery management, dynamic obstacle avoidance with instant replanning, and a modern, high-performance React dashboard.

---

## 📋 Table of Contents

1. [System Architecture](#-system-architecture)
2. [Prerequisites](#-prerequisites)
3. [Quick Start (Run Both Server & Client)](#-quick-start)
4. [Backend Setup & Run Guide (FastAPI)](#-backend-setup--run-guide)
5. [Frontend Setup & Run Guide (React + Vite)](#-frontend-setup--run-guide)
6. [Interactive Simulation Guide](#-interactive-simulation-guide)
   - [Top Control Panel](#top-control-panel)
   - [Exact-Cell Obstacle Placement](#exact-cell-obstacle-placement)
   - [Starting Point & Goal Definition](#starting-point--goal-definition)
   - [Agent Mission & Live Activity Log](#agent-mission--live-activity-log)
7. [Benchmark & Analytics (A* vs Nearest Neighbor)](#-benchmark--analytics)
8. [Running Tests](#-running-tests)
9. [API & WebSocket Documentation](#-api--websocket-documentation)
10. [Troubleshooting](#-troubleshooting)

---

## 🏗️ System Architecture

```text
WareBot-AI/
├── client/                         # React 18 + Vite frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/             # Top navigation & simulation controls
│   │   │   ├── warehouse/          # Maximized 30x30 grid, cells, legend
│   │   │   ├── dashboard/          # Agent Mission & telemetry sidebar
│   │   │   ├── analytics/          # Benchmark suite & Activity Log
│   │   │   └── orders/             # Order queue inspector
│   │   ├── hooks/                  # useSimulation hook (REST + WebSocket stream)
│   │   ├── services/               # simulationApi & simulationSocket
│   │   └── App.jsx                 # Streamlined dashboard root layout
│   ├── package.json
│   └── vite.config.js
│
├── server/                         # Python FastAPI simulation engine
│   ├── app/
│   │   ├── api/                    # REST routers: /simulation, /benchmark, /health
│   │   ├── core/                   # Utility weights & configuration
│   │   ├── models/                 # Warehouse, Robot, Order, Event models
│   │   ├── schemas/                # Pydantic schemas for request/response serialization
│   │   ├── services/               # SimulationManager & WebSocket connection manager
│   │   ├── simulation/             # Discrete-event engine, A* pathfinding, decision engine
│   │   └── main.py                 # FastAPI application entrypoint
│   ├── tests/                      # 41 unit, integration & benchmark tests (pytest)
│   └── requirements.txt            # Python dependencies
│
└── README.md
```

---

## ⚙️ Prerequisites

Before getting started, make sure you have the following installed on your system:

- **Python**: Version `3.10` or higher (`3.11` / `3.12` / `3.13` recommended).
- **Node.js**: Version `18.x` or higher (includes `npm`).
- **Git**: For cloning and repository management.

---

## 🚀 Quick Start

To launch the full WareBot AI platform, open **two terminal windows**:

### Terminal 1: FastAPI Backend
```bash
# Navigate to the server directory
cd server

# Create and activate Python virtual environment
python -m venv .venv
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\.venv\Scripts\activate.bat
# On macOS / Linux:
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt

# Start the simulation backend server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: React Frontend Dashboard
```bash
# Navigate to the client directory
cd client

# Install frontend dependencies
npm install

# Start Vite development server
npm run dev -- --port 5200
```

Once running:
- **Frontend Dashboard**: Open [http://localhost:5200](http://localhost:5200) in your browser.
- **Backend API & Swagger Docs**: Available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 🐍 Backend Setup & Run Guide

The backend is built with **FastAPI**, **Uvicorn**, and **Pydantic**. It runs discrete-event simulation ticks at configured frequencies (1Hz to 20Hz) and streams live state over WebSockets.

### Step-by-Step Instructions

1. **Open a terminal** and navigate into the `server/` folder:
   ```bash
   cd server
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
     > *Note for PowerShell users:* If script execution is disabled, run:
     > `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
   - **Windows (CMD)**:
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - **macOS / Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Start the FastAPI backend server**:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **Verify backend health**:
   Open [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) in your browser. You should see:
   ```json
   {
     "status": "healthy",
     "timestamp": "...",
     "simulation_active": true
   }
   ```

---

## 💻 Frontend Setup & Run Guide

The frontend is built with **React 18**, **Vite**, and **Tailwind CSS**.

### Step-by-Step Instructions

1. **Open a second terminal** and navigate into the `client/` folder:
   ```bash
   cd client
   ```

2. **Install node dependencies**:
   ```bash
   npm install
   ```

3. **Start the local development server**:
   ```bash
   npm run dev -- --port 5200
   ```

4. **Access the application**:
   Open [http://localhost:5200](http://localhost:5200) in your browser.

5. **Production Build (Optional)**:
   To verify or build the production bundle:
   ```bash
   npm run build
   ```

---

## 🎮 Interactive Simulation Guide

The interface is streamlined, modern, and uncluttered, designed specifically for clean interaction and demonstration:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [WareBot AI]  [Start/Play] [Pause] [Stop/Reset] [Step] [+ Add Obstacle]  T-0042  LIVE   │
├──────────────────────────────────────────────────────────┬─────────────────────────────┤
│                                                          │ [WareBot RB-01]  [RUNNING]  │
│                                                          │                             │
│                  WAREHOUSE MAP                           │ 🏁 STARTING POINT: [28, 1]  │
│                  (30 × 30 GRID)                          │ 🎯 CURRENT GOAL: Shelf SH-04│
│                                                          │                             │
│       • Large, high-visibility cells                     │ Battery: [========  ] 88%   │
│       • Checkered Flag: Starting Point [28, 1]           │ Travelled: 120m | Del: 5    │
│       • Pulsing Amber Beacon: Current Goal               ├─────────────────────────────┤
│       • Red ✕ Boxes: User-placed Obstacles               │ [Agent Activity Log]        │
│       • Click any floor box to toggle an obstacle        │ • T-0042: Assigned ORD-003  │
│                                                          │ • T-0045: Obstacle detected │
│                                                          │ • T-0046: Route replanned   │
└──────────────────────────────────────────────────────────┴─────────────────────────────┘
```

### Top Control Panel
- **Start / Play**: Initiates autonomous agent mission execution.
- **Pause**: Halts simulation execution at the current tick for inspection.
- **Resume**: Continues running from the paused state.
- **Stop / Reset**: Resets the robot back to Dock Alpha `[28, 1]` with seed-reproducible warehouse orders.
- **Step**: Advances simulation by exactly 1 tick to inspect step-by-step decision making.
- **+ Add Obstacle**: Toggles obstacle placement mode with an active visual indicator.
- **Speed Selector**: Tunable from `1x (2Hz)` up to `5x (20Hz)`.
- **View Toggle**: Switch between **Simulation** and **Analytics** benchmark view.

### Exact-Cell Obstacle Placement
- **Targeted Placement**: Obstacles are added **only to the exact box clicked by the user** (never placed randomly).
- **Toggle Behavior**: Clicking an existing obstacle box immediately removes it.
- **Dynamic A\* Replanning**: When an obstacle is placed anywhere along the robot's upcoming route:
  1. The robot detects the obstacle immediately.
  2. The A* engine calculates a collision-free detour around the barrier.
  3. The activity log records the obstacle detection and replan event: `Obstacle detected on route! Path replanned (X steps remaining)`.
  4. If all routes to the goal are completely blocked, the robot safely transitions to `BLOCKED` status until the path is cleared.

### Starting Point & Goal Definition
- **Starting Point `[28, 1]`**: Clearly designated on both the grid (checkered flag 🏁) and the sidebar as **Base Dock Alpha (Dispatch Origin)**.
- **Current Goal 🎯**: Always visible with an animated pulsing beacon on the warehouse floor and explicitly defined in the sidebar:
  - When fetching an item: Points to target shelf (e.g. `Shelf SH-04 [9, 10] — Microcontroller Unit`).
  - When packing an order: Points to **Packing Station Bay `[28, 14]`**.
  - When charging: Points to **Charging Station Dock `[28, 27]`**.

### Agent Mission & Live Activity Log
- **Sidebar Telemetry**: Shows active robot status (`NAVIGATING`, `PICKING`, `PACKING`, `CHARGING`, `BLOCKED`), live battery gauge, total meters travelled, completed deliveries, and replan count.
- **Live Activity Log**: Displays chronological, real-time audit logs of every movement, order assignment, inventory deduction, obstacle detection, and delivery completion. Filterable by `All`, `Robot`, `Obstacles`, and `Orders`.

---

## 📊 Benchmark & Analytics

WareBot AI includes a quantitative benchmarking suite comparing **A\* Utility-Based Decision Engine** against a baseline **Nearest Order First** strategy across identical scenarios:

1. Click the **Analytics** tab in the top header.
2. Select scenarios (e.g., *Normal Flow*, *High Congestion*, *Battery Drain*).
3. Click **Run Benchmark**.
4. Inspect visual comparison charts:
   - Order Completion Rate (%)
   - Average Order Lead Time (ticks)
   - Energy Efficiency (units / delivery)
   - Total Obstacle Replans
5. Click **Export CSV** to download raw benchmark metrics for reporting and analysis.

---

## 🧪 Running Tests

### Backend Test Suite (Pytest)
The backend includes 41 comprehensive tests covering map generation, A* pathfinding, battery safety, decision utility formulas, order lifecycles, and REST/WebSocket endpoints.

```bash
cd server
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate   # macOS / Linux
python -m pytest -v
```

### Frontend Test Suite (Vitest)
The client includes component tests covering layout rendering, controls interaction, state mapping, and grid cell validation:

```bash
cd client
npm test
```

---

## 🔌 API & WebSocket Documentation

### Interactive Swagger Docs
When the backend is running, visit:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Primary REST Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Backend health check |
| `GET` | `/api/simulation/state` | Full state snapshot (grid, robot, orders, metrics) |
| `POST` | `/api/simulation/start` | Start autonomous simulation |
| `POST` | `/api/simulation/pause` | Pause simulation |
| `POST` | `/api/simulation/resume` | Resume simulation |
| `POST` | `/api/simulation/reset` | Reset simulation to initial seed |
| `POST` | `/api/simulation/step` | Advance simulation by N ticks (`{"steps": 1}`) |
| `POST` | `/api/simulation/speed` | Set execution speed level 1-5 (`{"speed": 2}`) |
| `POST` | `/api/simulation/obstacles` | Place/toggle obstacle at exact cell (`{"row": 12, "col": 14}`) |
| `POST` | `/api/simulation/orders/urgent` | Inject an urgent priority order |
| `POST` | `/api/benchmark/run` | Execute comparative benchmark run |
| `GET` | `/api/benchmark/{id}/export` | Export benchmark results as CSV |

### WebSocket Real-Time Stream
- **URL**: `ws://127.0.0.1:8000/api/simulation/stream`
- **Protocol**: Broadcasts JSON `simulation_state` payloads on every discrete tick with automatic reconnection and fallback.

---

## 🛠️ Troubleshooting

### 1. `python: command not found` or Microsoft Store opens (Windows)
Make sure Python is installed and added to your system `PATH`. Alternatively, use the Python launcher:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. PowerShell Script Execution Disabled
If activating the virtual environment throws an execution policy error, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Port 8000 or 5200 Already in Use
- To run the backend on a different port:
  ```bash
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
  ```
- To run the frontend on a different port:
  ```bash
  npm run dev -- --port 3000
  ```
  *(If changing ports, update `VITE_API_URL` and `VITE_WS_URL` in `client/.env.example` / `client/.env`).*

### 4. Frontend Shows "OFFLINE" Badge
1. Ensure the FastAPI backend is running on `http://127.0.0.1:8000`.
2. Check that the `/api/health` endpoint responds with `"status": "healthy"`.
3. Click the **Retry** button in the dashboard header.

---
