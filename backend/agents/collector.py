"""
Collector Agent - Responsible for gathering Citrix DaaS metrics
Integrates with Citrix Cloud Monitor API
"""

import logging
import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from models.schemas import VDAMachine, MetricSnapshot

logger = logging.getLogger(__name__)


class CollectorAgent:
    """Collects metrics from Citrix Cloud DaaS environment"""

    def __init__(self):
        # Citrix Cloud API configuration
        self.client_id = os.getenv("CITRIX_CLIENT_ID")
        self.client_secret = os.getenv("CITRIX_CLIENT_SECRET")
        self.customer_id = os.getenv("CITRIX_CUSTOMER_ID")
        self.api_base_url = os.getenv("CITRIX_API_URL", "https://api.cloud.com")

        # OAuth token management
        self.access_token = None
        self.token_expires_at = None
        
        # Always initialize mock data as fallback
        self.machines_data = {}
        self._initialize_mock_machines()

        # Fallback to mock data if API not configured
        self.use_mock_data = not all([
            self.client_id,
            self.client_secret,
            self.customer_id
        ])

        if self.use_mock_data:
            logger.warning("Citrix API credentials not found, using mock data")
        else:
            logger.info("Citrix API credentials found, will use real API")

    def _initialize_mock_machines(self):
        """Initialize baseline machine data for mock mode"""
        MACHINE_NAMES = [
            "VDA-01", "VDA-02", "VDA-03", "VDA-04", "VDA-05",
            "VDA-06", "VDA-07", "VDA-08", "VDA-09", "VDA-10"
        ]

        for name in MACHINE_NAMES:
            self.machines_data[name] = {
                "state": "Registered",
                "power_state": "On",
                "cpu_usage": 45.0,
                "memory_usage": 60.0,
                "disconnect_rate": 5.0,
                "session_count": 12,
                "available_sessions": 10,
                "unavailable_sessions": 2,
                "ghost_sessions": 0,
                "hdx_latency": 25.5,
                "disk_usage": 65.0,
                "failed_logins": 0,
                "is_in_maintenance": False,
                "uptime_percentage": 100.0,
            }

    def _get_access_token(self) -> Optional[str]:
        """Get OAuth access token for Citrix Cloud API"""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.access_token

        try:
            token_url = f"{self.api_base_url}/cctrustoauth2/{self.customer_id}/tokens/clients"

            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            response = requests.post(token_url, json=payload, timeout=30)
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data.get("access_token")

            # Set expiration (usually 1 hour)
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            logger.info("Successfully obtained Citrix API access token")
            return self.access_token

        except Exception as e:
            logger.error(f"Failed to get Citrix API token: {e}")
            return None

    def _call_citrix_api(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated API call to Citrix Cloud"""
        token = self._get_access_token()
        if not token:
            return None

        try:
            url = f"{self.api_base_url}{endpoint}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Citrix API call failed: {e}")
            return None

    def _get_vda_machines(self) -> List[Dict]:
        """Get VDA machines from Citrix Cloud"""
        if self.use_mock_data:
            return self._get_mock_vda_machines()

        # Real Citrix API call
        machines_data = self._call_citrix_api("/cvad/manage/machines")
        if not machines_data:
            logger.warning("Failed to get VDA machines from API, falling back to mock data")
            return self._get_mock_vda_machines()

        # Parse Citrix API response
        machines = []
        for machine in machines_data.get("items", []):
            machines.append({
                "machine_name": machine.get("name", "Unknown"),
                "state": machine.get("registration_state", "Unknown"),
                "power_state": machine.get("power_state", "Unknown"),
                "cpu_usage": machine.get("cpu_usage_percent", 0.0),
                "memory_usage": machine.get("memory_usage_percent", 0.0),
                "session_count": machine.get("session_count", 0),
                "available_sessions": machine.get("available_sessions", 0),
                "unavailable_sessions": machine.get("session_count", 0) - machine.get("available_sessions", 0),
                "disconnect_rate": machine.get("disconnect_rate_percent", 0.0),
                "ghost_sessions": machine.get("ghost_sessions", 0),
                "hdx_latency": machine.get("hdx_latency_ms", 0.0),
                "disk_usage": machine.get("disk_usage_percent", 0.0),
                "failed_logins": machine.get("failed_logins", 0),
                "is_in_maintenance": machine.get("is_in_maintenance", False),
                "uptime_percentage": machine.get("uptime_percentage", 100.0),
            })

        return machines

    def _get_mock_vda_machines(self) -> List[Dict]:
        """Get mock VDA machines for testing"""
        machines = []
        for name, data in self.machines_data.items():
            machines.append({
                "machine_name": name,
                **data
            })
        return machines

    def _get_session_metrics(self) -> Dict[str, Any]:
        """Get session metrics from Citrix Cloud"""
        if self.use_mock_data:
            return self._get_mock_session_metrics()

        # Real Citrix API call for sessions
        sessions_data = self._call_citrix_api("/citrixcloud/inventory/api/v2/sessions")
        if not sessions_data:
            logger.warning("Failed to get session metrics from API")
            return self._get_mock_session_metrics()

        # Aggregate session data
        total_sessions = len(sessions_data.get("items", []))
        active_sessions = len([s for s in sessions_data.get("items", [])
                              if s.get("state") == "Active"])
        disconnected_sessions = len([s for s in sessions_data.get("items", [])
                                    if s.get("state") == "Disconnected"])

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "disconnected_sessions": disconnected_sessions,
            "disconnect_rate": (disconnected_sessions / total_sessions * 100) if total_sessions > 0 else 0
        }

    def _get_mock_session_metrics(self) -> Dict[str, Any]:
        """Get mock session metrics"""
        total = sum(m["session_count"] for m in self.machines_data.values())
        available = sum(m["available_sessions"] for m in self.machines_data.values())
        unavailable = sum(m["unavailable_sessions"] for m in self.machines_data.values())

        return {
            "total_sessions": total,
            "active_sessions": available,
            "disconnected_sessions": unavailable,
            "disconnect_rate": (unavailable / total * 100) if total > 0 else 0
        }
    
    def collect_metrics(self, db: Session) -> Dict[str, Any]:
        """
        Collect metrics from Citrix Cloud API or mock data

        Returns:
            Dictionary with collected metrics
        """
        logger.info("Starting metric collection...")

        try:
            # Get VDA machines
            machines = self._get_vda_machines()
            logger.info(f"Retrieved {len(machines)} VDA machines")

            # Get session metrics
            session_metrics = self._get_session_metrics()
            logger.info(f"Session metrics: {session_metrics}")

            # Process each machine
            for machine_data in machines:
                machine_name = machine_data["machine_name"]

                # Save to database
                self._update_or_create_machine(db, machine_name, machine_data)
                self._save_metric_snapshots(db, machine_name, machine_data)

            logger.info(f"Successfully collected metrics for {len(machines)} machines")
            return {
                "status": "success",
                "machines_collected": len(machines),
                "data_source": "mock" if self.use_mock_data else "citrix_api",
                "timestamp": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Error during metric collection: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    def _update_or_create_machine(self, db: Session, machine_name: str, data: Dict[str, Any]):
        """Update or create machine record in database"""
        machine = db.query(VDAMachine).filter(
            VDAMachine.machine_name == machine_name
        ).first()
        
        if machine:
            machine.state = data["state"]
            machine.power_state = data["power_state"]
            machine.cpu_usage = data["cpu_usage"]
            machine.memory_usage = data["memory_usage"]
            machine.disconnect_rate = data["disconnect_rate"]
            machine.session_count = data["session_count"]
            machine.available_sessions = data["available_sessions"]
            machine.unavailable_sessions = data["unavailable_sessions"]
            machine.ghost_sessions = data.get("ghost_sessions", 0)
            machine.hdx_latency = data.get("hdx_latency", 0.0)
            machine.disk_usage = data.get("disk_usage", 0.0)
            machine.failed_logins = data.get("failed_logins", 0)
            machine.is_in_maintenance = data.get("is_in_maintenance", False)
            machine.uptime_percentage = data.get("uptime_percentage", 100.0)
            machine.last_updated = datetime.utcnow()
        else:
            machine = VDAMachine(
                machine_name=machine_name,
                state=data["state"],
                power_state=data["power_state"],
                cpu_usage=data["cpu_usage"],
                memory_usage=data["memory_usage"],
                disconnect_rate=data["disconnect_rate"],
                session_count=data["session_count"],
                available_sessions=data["available_sessions"],
                unavailable_sessions=data["unavailable_sessions"],
                ghost_sessions=data.get("ghost_sessions", 0),
                hdx_latency=data.get("hdx_latency", 0.0),
                disk_usage=data.get("disk_usage", 0.0),
                failed_logins=data.get("failed_logins", 0),
                is_in_maintenance=data.get("is_in_maintenance", False),
                uptime_percentage=data.get("uptime_percentage", 100.0),
            )
            db.add(machine)
        
        db.commit()
    
    def _save_metric_snapshots(self, db: Session, machine_name: str, data: Dict[str, Any]):
        """Save metric snapshots for historical tracking"""
        metrics = [
            ("cpu_usage", data["cpu_usage"]),
            ("memory_usage", data["memory_usage"]),
            ("disconnect_rate", data["disconnect_rate"]),
            ("session_count", data["session_count"]),
            ("ghost_sessions", data.get("ghost_sessions", 0)),
            ("hdx_latency", data.get("hdx_latency", 0.0)),
            ("disk_usage", data.get("disk_usage", 0.0)),
            ("uptime_percentage", data.get("uptime_percentage", 100.0)),
        ]
        
        for metric_type, metric_value in metrics:
            snapshot = MetricSnapshot(
                machine_name=machine_name,
                metric_type=metric_type,
                metric_value=metric_value,
            )
            db.add(snapshot)
        
        db.commit()
