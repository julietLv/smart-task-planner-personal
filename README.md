# Smart Task Planner - 智能任务规划系统

AI-powered intelligent task scheduling and planning system. Input tasks in natural language, and the system intelligently schedules them considering priorities, deadlines, habits, holidays, and weather.

Built with **Vue 3 + FastAPI**, featuring a hybrid NLP engine (LLM + rule-based), Google OR-Tools optimization engine, real-time WebSocket notifications, multi-country holiday support, and Docker deployment out of the box.

> `Download: 项目完整代码打包 (百度网盘/Google Drive)`
> `请将下载链接粘贴在此处，替换本行文字`
> `建议文件名: smart-task-planner-v2.0.0.zip`

![主界面截图](docs/screenshots/main-dashboard.png)

---

## Key Features

### Natural Language Task Input
Type "meeting with the team tomorrow at 3pm for an hour" or "buy groceries this weekend" and the system parses intent, extracts entities, and fills in missing details using learned habits. Supports both LLM-powered parsing (DeepSeek/OpenAI) and a rule-based fallback parser.

### Intelligent Scheduling Engine
Google OR-Tools CP-SAT solver powers the scheduling core. Three-layer constraint model combines hard constraints (no overlap, blocked hours), population standards (student/worker/elderly profiles), and personalized fine-tuning (learned preferences, time-slot offsets). Conflict detection with visual feedback and auto-resolve.

### Habit Learning System
The system learns from your scheduling adjustments. Each time you reschedule a task, the learning engine records the pattern. Over time, it automatically applies learned preferences - default durations, preferred time slots, priority levels - reducing manual input.

### Multi-Country Holiday Calendar
Integrated with the Python `holidays` library covering 150+ countries. Displays public holidays, weekend days, and compensatory rest/adjustment days on the calendar. Properly handles complex rules like lunar calendar holidays (Chinese New Year, Mid-Autumn Festival), floating holidays, and country-specific weekend patterns (Fri-Sat in UAE, Thu-Fri in Iran).

![天气小部件](docs/screenshots/weather-widget.png)

### Live Weather Integration
Real-time weather data and 3-day forecast. Configurable city selection with a preset list of major Chinese cities. Weather condition displayed alongside the calendar for context-aware planning.

![国家选择器 + 节假日显示](docs/screenshots/country-selector.png)

### AI Chat Assistant
Markdown-rendered chat interface with WebSocket streaming. The assistant can parse tasks, answer scheduling questions, generate reports, and provide productivity insights. Conversation history preserved during the session.

### Real-Time Notifications
WebSocket-based notification system with automatic reconnection. Supports deadline reminders, daily summaries, conflict alerts, and custom notifications. Notification center with badge counts and mark-as-read functionality.

### Reporting & Analytics
Weekly and monthly report generation with ECharts visualizations (priority distribution, completion status, workload trends). Export to Word documents via python-docx. Automated report generation through the async task queue.

### Task Management
Full CRUD with drag-and-drop calendar interface (day/week/month views). Task detail/edit dialog with priority levels, status tracking, deadline management, and quick time-slot buttons. Skeleton loading states and optimized rendering.

### User Preferences & Personalization
Configurable working hours, blocked time slots, task buffer minutes, default priority. Three standard profiles (student, worker, elderly) with pre-configured schedules. Custom keyword mapping for task classification.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Vue 3 (Composition API + `<script setup>`), Vite, Element Plus, FullCalendar, ECharts / Vue-ECharts, Pinia, Vue Router, Axios, marked |
| **Backend** | FastAPI, SQLAlchemy ORM + Alembic, Pydantic, APScheduler, Redis |
| **AI** | OpenAI-compatible API (DeepSeek), Hybrid NLP (LLM + rule-based), Prompt engineering |
| **Scheduling** | Google OR-Tools (CP-SAT), Three-layer constraint model |
| **Database** | MySQL (production), SQLite (development/lite) |
| **DevOps** | Docker, Docker Compose, Nginx (multi-stage build) |
| **Tools** | Matplotlib (charts), python-docx (Word export), python-holidays (calendar) |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Vue 3 Frontend                    │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────┐  │
│  │Calendar │ │ChatWindow│ │TaskInput│ │ReportChart│  │
│  │  View   │ │          │ │(NLP)   │ │  (ECharts)│  │
│  └────┬────┘ └────┬─────┘ └───┬────┘ └─────┬────┘  │
│       │           │           │             │        │
│  ┌────┴───────────┴───────────┴─────────────┴────┐  │
│  │            Pinia Stores + Axios                │  │
│  └────────────────────┬──────────────────────────┘  │
└───────────────────────┼──────────────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────┼──────────────────────────────┐
│          FastAPI Backend                             │
│  ┌────────┐ ┌─────────┐ ┌────────┐ ┌─────────────┐  │
│  │Routers │ │Services │ │Models  │ │WebSocket Mgr│  │
│  └───┬────┘ └────┬────┘ └───┬────┘ └──────┬──────┘  │
│      │           │           │              │        │
│  ┌───┴───────────┴───────────┴──────────────┴────┐   │
│  │  OR-Tools  │  NLP Engine  │  Habit Learner    │   │
│  │  Scheduler │  (LLM+Rules) │                   │   │
│  └────────────┴──────────────┴───────────────────┘   │
│                      │                                │
│         ┌────────────┼────────────┐                   │
│    ┌────┴────┐ ┌─────┴─────┐ ┌───┴────┐              │
│    │ MySQL / │ │  Redis    │ │   AI   │              │
│    │ SQLite  │ │(Cache+Q)  │ │  API   │              │
│    └─────────┘ └───────────┘ └────────┘              │
└──────────────────────────────────────────────────────┘
```

![功能演示截图](docs/screenshots/feature-showcase.png)

---

## Quick Start

### Option 0: Try Online with Docker (1 command)

```bash
docker compose -f docker-compose.lite.yml up -d
```

Then Open http://localhost (frontend) and http://localhost:8080/docs (API docs).



> **Prerequisites**: [Docker](https://www.docker.com/products/docker-desktop/) 24.0+ and [Docker Compose](https://docs.docker.com/compose/install/) v2.0+
> Get your [DeepSeek API Key](https://platform.deepseek.com/) (free) and [Weather API Key](https://www.qweather.com/) (free) before deploying.

### Option 1: Docker (Lite - SQLite, no external dependencies)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/smart-task-planner
cd smart-task-planner

# 2. Copy and configure environment variables
cp .env.docker .env
# Edit .env to add DEEPSEEK_API_KEY and WEATHER_API_KEY

# 3. Start with Docker Compose
docker compose -f docker-compose.lite.yml up -d

# 4. Open in browser
Open http://localhost
```

### Option 2: Local Development

**Prerequisites**: Python 3.10+, Node.js 18+

```bash
# Backend
cd backend
python -m venv venv
venv\Scriptsctivate    # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Then Open http://localhost:5173 (frontend) and http://localhost:8080/docs (API docs).

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app entry, router registration
│   ├── app/
│   │   ├── models/              # SQLAlchemy ORM models (task, notification)
│   │   ├── routers/             # 12 route modules (task, chat, weather, holiday...)
│   │   ├── services/            # Business logic (~30 service modules)
│   │   │   ├── or_tools_scheduler.py   # OR-Tools CP-SAT scheduling engine
│   │   │   ├── hybrid_parser.py        # LLM + rule-based NLP parser
│   │   │   ├── holiday_service.py      # Multi-country holiday calendar
│   │   │   ├── scoring_engine.py       # Three-layer scoring model
│   │   │   ├── report_generator.py     # Weekly/monthly report generation
│   │   │   ├── task_queue.py           # Redis-based async task queue
│   │   │   └── ...                     # Weather, notification, cache, security...
│   │   ├── schemas/             # Pydantic request/response schemas
│   ├── config/                  # Configuration files
│   ├── scripts/                 # Utility scripts
│   └── tests/                   # Test suite
│
├── frontend/
│   ├── src/
│   │   ├── components/          # Vue components (Calendar, Chat, Weather...)
│   │   ├── views/               # Page views (Home, Profile)
│   │   ├── stores/              # Pinia stores (task, notification)
│   │   ├── services/            # Service modules (WebSocket)
│   │   ├── api/                 # Axios API client modules
│   │   ├── utils/               # Utility modules (cache monitor)
│   │   └── router/              # Vue Router config
│   └── public/                  # Static assets
│
├── docker-compose.yml           # Full deployment (MySQL + Redis)
├── docker-compose.lite.yml      # Lite deployment (SQLite)
├── .env.docker                  # Environment template
├── dev.ps1                      # Windows dev startup script
└── README_DOCKER.md             # Docker deployment guide
```

---

## What This Project Demonstrates

**Full-Stack Development** - Complete Vue 3 SPA with a modular FastAPI backend. Component-based architecture with state management (Pinia), client-side routing, and RESTful API design.

**Systems Design** - Multi-layer architecture separating routers, services, and data models. Caching strategy across Redis, in-memory, and localStorage with TTL-based invalidation. Async task queue for background job processing.

**Algorithm Design** - Implemented Google OR-Tools CP-SAT solver for constraint-based scheduling with a three-layer model (hard constraints + population standards + personalization). Conflict detection with auto-resolve and manual override paths.

**AI/LLM Integration** - Hybrid NLP approach combining LLM-powered parsing (OpenAI-compatible API) with a rule-based fallback engine. Prompt engineering for structured entity extraction. Habit learning system that adapts to user behavior over time.

**Real-Time Systems** - WebSocket-based push notifications with automatic reconnection, heartbeat mechanism, and visibility-aware connectivity management.

**Database Design** - SQLAlchemy ORM with Alembic migrations supporting both MySQL and SQLite. Relational model for tasks, notifications, and user preferences.

**DevOps** - Multi-stage Docker builds for both frontend (Nginx) and backend (Python). Two deployment modes: complete (MySQL + Redis) and lite (SQLite). Environment-based configuration.

**Internationalization** - Multi-country holiday calendar supporting 50+ countries with correct weekend mapping, public holiday observance rules, lunar calendar events, and compensatory rest days.

---

## Deploy to Public Server

To share your running instance with others on a cloud server:

```bash
# 1. Clone on your server
git clone https://github.com/YOUR_USERNAME/smart-task-planner
cd smart-task-planner

# 2. Copy and configure
cp .env.docker .env
# Edit .env with your actual API keys (DeepSeek, Weather)

# 3. Start (lite version, no database setup needed)
docker compose -f docker-compose.lite.yml up -d --build

# 4. Your app is live at http://YOUR_SERVER_IP:80
# API docs at http://YOUR_SERVER_IP:8080/docs
```

> Note: The lite version uses SQLite for simplicity. For production, use `docker compose -f docker-compose.yml up -d --build` for MySQL + Redis.

## API Documentation

When the server is running, interactive OpenAPI documentation is available at:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### Available API Routes

- `GET /api/tasks` - Task CRUD operations
- `POST /api/chat/stream` - AI chat with streaming response
- `GET /api/weather/current?city=...` - Current weather
- `GET /api/holidays/month?year=...&month=...&country=...` - Month holidays
- `GET /api/holidays/countries` - Supported country list
- `GET /api/preferences/` - User preferences
- `GET /api/notifications/` - User notifications
- `POST /api/report/...` - Report generation
- `POST /api/scheduling/optimize` - Schedule optimization
- `WS /ws/{user_id}` - WebSocket for real-time updates
