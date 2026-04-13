"""
FastAPI API Routes
"""

import logging
from typing import List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from fastapi import APIRouter, Depends
from models.schemas import (
    VDAMachineRead, AlertRead, MetricSnapshotRead, SystemStatus, DashboardData
)
from models.schemas import VDAMachine, Alert, MetricSnapshot
from db.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])


@router.get("/machines", response_model=List[VDAMachineRead])
async def get_machines(db: Session = Depends(get_db)):
    """Get all VDA machines"""
    machines = db.query(VDAMachine).all()
    return machines


@router.get("/machines/{machine_name}", response_model=VDAMachineRead)
async def get_machine(machine_name: str, db: Session = Depends(get_db)):
    """Get specific machine by name"""
    machine = db.query(VDAMachine).filter(
        VDAMachine.machine_name == machine_name
    ).first()
    return machine


@router.get("/alerts", response_model=List[AlertRead])
async def get_alerts(
    resolved: bool = False,
    severity: str = None,
    db: Session = Depends(get_db)
):
    """Get alerts with optional filtering"""
    query = db.query(Alert)
    
    if not resolved:
        query = query.filter(Alert.is_resolved == False)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(desc(Alert.created_at)).all()
    return alerts


@router.get("/alerts/{alert_id}", response_model=AlertRead)
async def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get specific alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    return alert


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """Mark alert as resolved"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        db.commit()
        return {"status": "success", "message": "Alert resolved"}
    return {"status": "error", "message": "Alert not found"}


@router.get("/metrics")
async def get_metrics(
    machine_name: str = None,
    metric_type: str = None,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get historical metrics"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(MetricSnapshot).filter(
        MetricSnapshot.recorded_at >= cutoff_time
    )
    
    if machine_name:
        query = query.filter(MetricSnapshot.machine_name == machine_name)
    
    if metric_type:
        query = query.filter(MetricSnapshot.metric_type == metric_type)
    
    metrics = query.order_by(desc(MetricSnapshot.recorded_at)).all()
    
    return {
        "total": len(metrics),
        "metrics": [
            {
                "id": m.id,
                "machine_name": m.machine_name,
                "metric_type": m.metric_type,
                "metric_value": m.metric_value,
                "recorded_at": m.recorded_at.isoformat(),
            }
            for m in metrics
        ]
    }


@router.get("/sessions")
async def get_sessions(machine_name: str = None, db: Session = Depends(get_db)):
    """Get session information"""
    query = db.query(VDAMachine)
    
    if machine_name:
        query = query.filter(VDAMachine.machine_name == machine_name)
    
    machines = query.all()
    
    return {
        "total_machines": len(machines),
        "total_sessions": sum(m.session_count for m in machines),
        "total_available": sum(m.available_sessions for m in machines),
        "total_unavailable": sum(m.unavailable_sessions for m in machines),
        "machines": [
            {
                "machine_name": m.machine_name,
                "session_count": m.session_count,
                "available_sessions": m.available_sessions,
                "unavailable_sessions": m.unavailable_sessions,
            }
            for m in machines
        ]
    }


@router.get("/health")
async def get_health(db: Session = Depends(get_db)):
    """Get system health status"""
    try:
        # Check database connectivity
        db_connected = True
        db.execute("SELECT 1")
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db_connected = False
    
    return {
        "status": "healthy" if db_connected else "unhealthy",
        "database": "connected" if db_connected else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(db: Session = Depends(get_db)):
    """Get aggregated dashboard data"""
    
    # Get machine status
    machines = db.query(VDAMachine).all()
    healthy_machines = len([m for m in machines if m.state == "Registered" and m.power_state == "On"])
    
    # Get alert summary
    active_alerts = db.query(Alert).filter(Alert.is_resolved == False).all()
    critical_alerts = len([a for a in active_alerts if a.severity == "critical"])
    warning_alerts = len([a for a in active_alerts if a.severity == "warning"])
    
    # Get last collection time
    last_metric = db.query(MetricSnapshot).order_by(
        desc(MetricSnapshot.recorded_at)
    ).first()
    
    system_status = SystemStatus(
        total_machines=len(machines),
        healthy_machines=healthy_machines,
        critical_alerts=critical_alerts,
        warning_alerts=warning_alerts,
        database_connected=True,
        ollama_available=True,
        last_collection=last_metric.recorded_at if last_metric else None
    )
    
    # Get recent metrics
    cutoff_time = datetime.utcnow() - timedelta(hours=1)
    recent_metrics = db.query(MetricSnapshot).filter(
        MetricSnapshot.recorded_at >= cutoff_time
    ).all()
    
    return DashboardData(
        system_status=system_status,
        machines=[VDAMachineRead.from_orm(m) for m in machines],
        active_alerts=[AlertRead.from_orm(a) for a in active_alerts],
        recent_metrics=[MetricSnapshotRead.from_orm(m) for m in recent_metrics]
    )
