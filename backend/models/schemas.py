from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()


# ==================== SQLAlchemy ORM Models ====================

class VDAMachine(Base):
    """VDA (Virtual Delivery Agent) Machine model"""
    __tablename__ = "vda_machines"

    id = Column(Integer, primary_key=True, index=True)
    machine_name = Column(String(255), unique=True, index=True)
    state = Column(String(50))  # registered, unregistered, etc.
    power_state = Column(String(50))  # on, off, etc.
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    disconnect_rate = Column(Float, default=0.0)
    session_count = Column(Integer, default=0)
    available_sessions = Column(Integer, default=0)
    unavailable_sessions = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class MetricSnapshot(Base):
    """Historical metric snapshot"""
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    machine_name = Column(String(255), index=True)
    metric_type = Column(String(100))  # cpu, memory, disconnect_rate, etc.
    metric_value = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """Alert model"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(100), index=True)  # vda_unregistered, high_cpu, etc.
    machine_name = Column(String(255), index=True)
    severity = Column(String(20))  # critical, warning, info
    title = Column(String(255))
    description = Column(Text)
    root_cause = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class AlertHistory(Base):
    """Alert history for tracking"""
    __tablename__ = "alert_history"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, index=True)
    status_change = Column(String(100))  # created, acknowledged, resolved
    changed_at = Column(DateTime, default=datetime.utcnow)


# ==================== Pydantic Schemas ====================

class VDAMachineRead(BaseModel):
    """Schema for reading VDA machine data"""
    id: int
    machine_name: str
    state: str
    power_state: str
    cpu_usage: float
    memory_usage: float
    disconnect_rate: float
    session_count: int
    available_sessions: int
    unavailable_sessions: int
    last_updated: datetime
    
    class Config:
        from_attributes = True


class VDAMachineCreate(BaseModel):
    """Schema for creating VDA machine"""
    machine_name: str
    state: str
    power_state: str
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disconnect_rate: float = 0.0
    session_count: int = 0
    available_sessions: int = 0
    unavailable_sessions: int = 0


class MetricSnapshotRead(BaseModel):
    """Schema for reading metric snapshot"""
    id: int
    machine_name: str
    metric_type: str
    metric_value: float
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class AlertRead(BaseModel):
    """Schema for reading alert"""
    id: int
    alert_type: str
    machine_name: str
    severity: str
    title: str
    description: str
    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    is_resolved: bool
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    """Schema for creating alert"""
    alert_type: str
    machine_name: str
    severity: str
    title: str
    description: str


class AlertUpdate(BaseModel):
    """Schema for updating alert"""
    root_cause: Optional[str] = None
    suggested_fix: Optional[str] = None
    is_resolved: Optional[bool] = None


class SystemStatus(BaseModel):
    """System health status"""
    total_machines: int
    healthy_machines: int
    critical_alerts: int
    warning_alerts: int
    database_connected: bool
    ollama_available: bool
    last_collection: Optional[datetime] = None


class DashboardData(BaseModel):
    """Dashboard data aggregation"""
    system_status: SystemStatus
    machines: List[VDAMachineRead]
    active_alerts: List[AlertRead]
    recent_metrics: List[MetricSnapshotRead]
