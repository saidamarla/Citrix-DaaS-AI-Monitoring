# Citrix DaaS AI-Powered Monitoring System

A complete, production-ready AI-powered monitoring system for Citrix Cloud DaaS (Desktop-as-a-Service) that runs completely locally on Docker.

## Features

✅ **Real-time Metrics Collection** - Simulates/integrates Citrix Cloud Monitor API
✅ **Rule-Based Issue Detection** - Detects:
  - VDA unregistered (>5 min)
  - High disconnect rate (>20%)
  - Session unavailability (>30%)
  - High CPU usage (>85%)
  - High memory usage (>85%)
  - Unexpected power-off states

✅ **AI-Powered Explanations** - Uses local Ollama LLM to explain:
  - Root cause of issues
  - Suggested fixes and remediation steps

✅ **Beautiful Web Dashboard** - Real-time metrics visualization
✅ **PostgreSQL Database** - Persistent storage of metrics and alerts
✅ **100% Local** - No cloud dependencies, runs on Docker Desktop

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend API | FastAPI | 0.109.0 |
| Database | PostgreSQL | 15 |
| LLM Engine | Ollama + Mistral | Latest |
| Frontend | HTML5 + JavaScript | - |
| Containerization | Docker Compose | 3.8 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Dashboard (Frontend)                     │
│                    HTML5 + JavaScript                        │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────▼────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┬──────────────┬──────────────┐              │
│  │  Collector   │  Analyzer    │ Alert Agent  │              │
│  │   Agent      │   Agent      │              │              │
│  └──────────────┴──────────────┴──────────────┘              │
│           │              │              │                    │
│           └──────────────┼──────────────┘                    │
│                          │                                   │
│                  Uses Ollama for AI                          │
└────────────────────┬─────────────────┬──────────────────────┘
                     │                 │
        ┌────────────▼──┐         ┌────▼───────────┐
        │  PostgreSQL   │         │  Ollama (LLM)  │
        │   Database    │         │   (Mistral)    │
        └───────────────┘         └────────────────┘
```

## Prerequisites

- Docker Desktop (20.10+) - [Download](https://www.docker.com/products/docker-desktop)
- Docker Compose (2.0+) - Usually included with Docker Desktop
- At least 4GB RAM available for containers
- Disk space: ~3GB for initial downloads

## Quick Start

### 1. Clone/Create the Project

```bash
git clone <repository-url>
cd citrix-daas-monitor
# OR if creating from scratch, ensure all files from this repo are in place
```

### 2. Start All Services

```bash
docker-compose up --build -d
```

What happens:
- PostgreSQL starts and initializes
- Ollama downloads the Mistral 7B LLM (may take 5-15 mins on first run)
- Backend starts and creates database tables
- Frontend starts serving the dashboard

### 3. Verify Services are Running

```bash
# Check all containers
docker ps

# Check logs
docker-compose logs -f
```

Expected output:
```
postgres              ready
ollama                Listening on localhost:11434
backend               Uvicorn running on 0.0.0.0:8000
frontend              running on port 3000
```

### 4. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:3000
```

## Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://localhost:3000 | Web UI |
| API Health | http://localhost:8000/health | Backend health check |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| DB Admin | localhost:5432 | PostgreSQL (internal) |
| LLM | localhost:11434 | Ollama (internal) |

## API Endpoints

### Machines
- `GET /api/machines` - Get all VDA machines
- `GET /api/machines/{name}` - Get specific machine

### Alerts
- `GET /api/alerts` - Get active alerts
- `GET /api/alerts/{id}` - Get specific alert
- `POST /api/alerts/{id}/resolve` - Mark alert as resolved

### Metrics
- `GET /api/metrics` - Get historical metrics
- `GET /api/metrics?machine_name=VDA-01&hours=24` - Get machine metrics for last 24 hours

### Sessions
- `GET /api/sessions` - Get session overview

### Dashboard
- `GET /api/dashboard` - Get aggregated dashboard data

### Health
- `GET /api/health` - Check API health
- `GET /status` - Get system status

## Configuration

Edit `.env` file to customize:

```env
# Collection Interval (seconds) - how often metrics are collected
COLLECTION_INTERVAL_SECONDS=60

# Ollama Configuration
OLLAMA_MODEL=mistral  # or llama2, neural-chat, etc.

# Database
DATABASE_URL=postgresql://citrix_user:citrix_password@postgres:5432/citrix_daas_db

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## How It Works

### 1. Data Collection Cycle (Every 60 seconds)

**Collector Agent:**
- Simulates or integrates with Citrix Cloud API
- Collects VDA machine metrics:
  - CPU, Memory, Disk usage
  - Session counts and availability
  - Registration state
  - Power state
  - Disconnect rate
- Saves metrics to PostgreSQL

### 2. Analysis & Alert Detection

**Analyzer Agent:**
- Applies rule-based logic to detect issues
- Rules check for:
  - Unregistered VDAs (>5 minutes)
  - High disconnect rates (>20%)
  - Session unavailability (>30% unavailable)
  - High resource usage (CPU >85%, Memory >85%)
  - Power-off states
- Creates alerts in database when rules are violated
- Auto-resolves alerts when issues clear

### 3. AI Explanation

**AI Agent:**
- Processes unresolved alerts
- Calls local Ollama LLM (Mistral 7B)
- Generates:
  - **Root Cause:** Why did this alert trigger?
  - **Suggested Fix:** How to resolve it?
- Uses fallback explanations if Ollama unavailable

### 4. Dashboard Display

**Frontend:**
- Auto-refreshes every 10 seconds
- Shows:
  - System health overview
  - Active alerts with AI explanations
  - VDA machine status and metrics
  - Session aggregation
  - Time-series data trends
- Allows resolving alerts

## Citrix Cloud API Integration

### Option 1: Use Mock Data (Current Default)

The system currently uses **simulated data** for demonstration. No API credentials needed.

### Option 2: Connect to Real Citrix Cloud API

To use real Citrix Cloud data:

#### 1. Get Citrix Cloud API Credentials

1. Log into [Citrix Cloud Console](https://cloud.com)
2. Go to **API Access** → **Secure Clients**
3. Create a new Secure Client
4. Copy the **Client ID** and **Client Secret**
5. Note your **Customer ID** (shown in the console URL)

#### 2. Configure Environment Variables

Edit `.env` file:

```env
# Citrix Cloud API Configuration
CITRIX_CLIENT_ID=your_actual_client_id_here
CITRIX_CLIENT_SECRET=your_actual_client_secret_here
CITRIX_CUSTOMER_ID=your_actual_customer_id_here
CITRIX_API_URL=https://api.cloud.com
```

#### 3. Restart the System

```bash
docker-compose down
docker-compose up --build -d
```

#### 4. Verify API Connection

Check logs:
```bash
docker-compose logs backend | grep -i "citrix\|api"
```

You should see:
```
INFO - Citrix API credentials found, will use real API
INFO - Successfully obtained Citrix API access token
```

### API Endpoints Used

The system calls these Citrix Cloud APIs:

- **Machines**: `/cvad/manage/machines` - Get VDA machine status
- **Sessions**: `/citrixcloud/inventory/api/v2/sessions` - Get session metrics
- **OAuth**: `/cctrustoauth2/{customer_id}/tokens/clients` - Get access tokens

### Fallback Behavior

If API credentials are missing or API calls fail, the system automatically falls back to mock data with a warning in the logs.

## Docker Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f ollama
docker-compose logs -f frontend
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove All Data
```bash
docker-compose down -v  # -v removes volumes too
```

### Rebuild Containers
```bash
docker-compose build --no-cache
docker-compose up --build -d
```

### Restart a Service
```bash
docker-compose restart backend
```

### Check Service Health
```bash
docker-compose ps
```

## Troubleshooting

### Issue: "postgres connection refused"
**Solution:** Wait for postgres to be fully ready
```bash
docker-compose logs postgres
# Wait for "database system is ready to accept connections"
```

### Issue: "Ollama not found" / "Connection refused on 11434"
**Solution:** Ollama is downloading the model (5-15 mins on first run)
```bash
docker-compose logs ollama
# Wait for "Listening on" message indicating readiness
```

### Issue: Dashboard shows "Loading..." indefinitely
**Solution:** Backend API not responding
```bash
# Check backend logs
docker-compose logs backend

# Check health endpoint
curl http://localhost:8000/health

# Restart backend
docker-compose restart backend
```

### Issue: No alerts appearing
**Solution:** System running but no data yet
- Collection runs every 60 seconds
- First alert may take 1-2 minutes to appear
- Check logs: `docker-compose logs backend | grep -i collecting`

### Issue: Out of memory
**Solution:** Reduce Ollama memory limit in docker-compose.yml
```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Reduce from 2G to 1G
```

### Issue: Port already in use
**Solution:** Change port mappings in docker-compose.yml
```yaml
ports:
  - "8001:8000"  # Backend on 8001 instead of 8000
  - "3001:3000"  # Frontend on 3001 instead of 3000
```

## Database

The system uses PostgreSQL with four main tables:

### vda_machines
Stores current state of VDA machines
```sql
SELECT * FROM vda_machines;
```

### alerts
Stores generated alerts with AI explanations
```sql
SELECT * FROM alerts WHERE is_resolved = false;
```

### metric_snapshots
Historical time-series metric data
```sql
SELECT * FROM metric_snapshots WHERE recorded_at > NOW() - INTERVAL '1 hour';
```

### alert_history
Track of alert status changes
```sql
SELECT * FROM alert_history;
```

## Development

### Local Backend Development
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend directly (requires running PostgreSQL + Ollama in Docker)
python main.py
```

### Local Frontend Development
```bash
cd frontend

# No dependencies needed, just open in browser
# Or use local HTTP server:
python -m http.server 3000
```

## Performance Tuning

### Reduce Collection Interval
```env
COLLECTION_INTERVAL_SECONDS=30  # Collect every 30 seconds instead of 60
```

### Increase LLM Response Speed
```env
OLLAMA_MODEL=neural-chat:7b  # Faster than mistral for explanations
```

MEMORY USAGE:
- PostgreSQL: ~100-200 MB
- Ollama: 1-2 GB (depending on model)
- Backend: 50-100 MB
- Frontend: ~10 MB

## Production Considerations

1. **Security:**
   - Change default PostgreSQL password in docker-compose.yml
   - Add authentication to API endpoints
   - Use HTTPS in production

2. **Scaling:**
   - For multiple environments, use docker-compose overrides
   - Consider separate PostgreSQL instance
   - Add load balancer for multiple backend replicas

3. **Monitoring:**
   - Integrate with Prometheus/Grafana
   - Export metrics to external monitoring systems
   - Add alerting to external systems

4. **Backup:**
   - Regular PostgreSQL backups
   - `docker-compose exec postgres pg_dump ... > backup.sql`

## Customization

### Add New Detection Rules

Edit `backend/agents/analyzer.py`:

```python
class CustomRule(Rule):
    def __init__(self):
        super().__init__("custom_rule", "warning")
    
    def check(self, machine):
        if machine.some_metric > threshold:
            return (True, "Title", "Description")
        return (False, "", "")

# Add to analyzer
self.rules.append(CustomRule())
```

### Integrate Real Citrix API

Edit `backend/agents/collector.py` to replace mock data:

```python
async def get_machines_from_citrix():
    # Install: pip install citrix-cloud-sdk
    # Implement real API calls here
    pass
```

### Change LLM Model

Edit `.env`:
```env
OLLAMA_MODEL=llama2  # Or neural-chat, orca, etc.
```

First run will download the new model (~5-15 mins).

## Support & Issues

### Debug Mode
```bash
# Set log level to DEBUG
.env: LOG_LEVEL=DEBUG

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Check Container Health
```bash
docker-compose ps
# All services should show "healthy"
```

### Database Connection
```bash
# Connect to PostgreSQL directly
docker-compose exec postgres psql -U citrix_user -d citrix_daas_db
```

## License

MIT License - Feel free to use in production with attribution

## Version

1.0.0 - Initial Release

---

**Ready to monitor your Citrix DaaS with AI!**

```bash
docker-compose up --build -d
# Visit http://localhost:3000
```
