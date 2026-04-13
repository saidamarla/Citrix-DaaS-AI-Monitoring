"""
FastAPI Main Application
Citrix DaaS AI-Powered Monitoring System
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db.database import init_db, SessionLocal
from api.routes import router
from agents.collector import CollectorAgent
from agents.analyzer import AnalyzerAgent
from agents.alert_agent import AlertAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize agents
collector_agent = CollectorAgent()
analyzer_agent = AnalyzerAgent()
alert_agent = AlertAgent()
scheduler = BackgroundScheduler()


def run_collection_cycle():
    """Run metric collection, analysis, and alert processing"""
    logger.info(f"=== Starting collection cycle at {datetime.utcnow()} ===")
    
    db = SessionLocal()
    try:
        # Step 1: Collect metrics
        logger.info("Step 1: Collecting metrics...")
        collection_result = collector_agent.collect_metrics(db)
        logger.info(f"Collection result: {collection_result}")
        
        # Step 2: Analyze metrics
        logger.info("Step 2: Analyzing metrics...")
        analysis_result = analyzer_agent.analyze_metrics(db)
        logger.info(f"Analysis result: {analysis_result}")
        
        # Step 3: Process alerts and add AI explanations
        logger.info("Step 3: Processing alerts with AI...")
        alert_result = alert_agent.process_alerts(db)
        logger.info(f"Alert processing result: {alert_result}")
        
        # Step 4: Get alert summary
        alert_summary = alert_agent.get_alert_summary(db)
        logger.info(f"Alert summary: {alert_summary['total_active']} active alerts "
                   f"({alert_summary['critical']} critical, {alert_summary['warning']} warning)")
        
        logger.info("=== Collection cycle completed ===")
        
    except Exception as e:
        logger.error(f"Error in collection cycle: {e}", exc_info=True)
    finally:
        db.close()


def schedule_collection_jobs():
    """Schedule the collection cycle to run every 60 seconds"""
    collection_interval = int(os.getenv("COLLECTION_INTERVAL_SECONDS", "60"))
    
    logger.info(f"Scheduling collection job to run every {collection_interval} seconds")
    
    scheduler.add_job(
        run_collection_cycle,
        trigger=IntervalTrigger(seconds=collection_interval),
        id='collection_job',
        name='Metric Collection Cycle',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    # Startup
    logger.info("Initializing application...")
    try:
        init_db()
        schedule_collection_jobs()
        logger.info("Application initialized successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Citrix DaaS AI Monitoring",
    description="AI-Powered monitoring system for Citrix Cloud DaaS",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Citrix DaaS AI Monitoring",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/status")
async def get_status():
    """Get application status"""
    db = SessionLocal()
    try:
        # Check database
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        db_status = "disconnected"
    finally:
        db.close()
    
    return {
        "status": "running",
        "database": db_status,
        "scheduler": "running" if scheduler.running else "stopped",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
