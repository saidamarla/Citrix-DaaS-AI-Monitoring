"""
Analyzer Agent - Responsible for detecting issues and generating alerts
Uses rule-based logic to identify problems
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.schemas import VDAMachine, Alert

logger = logging.getLogger(__name__)


class Rule:
    """Base class for alert rules"""
    
    def __init__(self, rule_type: str, severity: str):
        self.rule_type = rule_type
        self.severity = severity
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        """
        Check if rule is violated
        
        Returns:
            Tuple of (violated: bool, title: str, description: str)
        """
        raise NotImplementedError


class VDAUnregisteredRule(Rule):
    """Check if VDA is unregistered for more than 5 minutes"""
    
    def __init__(self):
        super().__init__("vda_unregistered", "critical")
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        if machine.state == "Unregistered":
            time_diff = datetime.utcnow() - machine.last_updated
            if time_diff > timedelta(minutes=5):
                return (
                    True,
                    f"VDA {machine.machine_name} Unregistered",
                    f"{machine.machine_name} has been unregistered for more than 5 minutes."
                )
        return (False, "", "")


class HighDisconnectRateRule(Rule):
    """Check if disconnect rate exceeds 20%"""
    
    def __init__(self):
        super().__init__("high_disconnect_rate", "warning")
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        if machine.disconnect_rate > 20:
            return (
                True,
                f"High Disconnect Rate on {machine.machine_name}",
                f"Disconnect rate is {machine.disconnect_rate:.1f}%, exceeding the 20% threshold."
            )
        return (False, "", "")


class SessionUnavailableRule(Rule):
    """Check if session unavailability is high"""
    
    def __init__(self):
        super().__init__("session_unavailable", "warning")
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        if machine.session_count > 0:
            unavailable_rate = (machine.unavailable_sessions / machine.session_count) * 100
            if unavailable_rate > 30:  # More than 30% unavailable
                return (
                    True,
                    f"High Session Unavailability on {machine.machine_name}",
                    f"{machine.unavailable_sessions} out of {machine.session_count} sessions unavailable "
                    f"({unavailable_rate:.1f}%)."
                )
        return (False, "", "")


class HighCPURule(Rule):
    """Check if CPU usage exceeds 85%"""
    
    def __init__(self):
        super().__init__("high_cpu", "warning")
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        if machine.cpu_usage > 85:
            return (
                True,
                f"High CPU Usage on {machine.machine_name}",
                f"CPU usage is {machine.cpu_usage:.1f}%, exceeding the 85% threshold."
            )
        return (False, "", "")


class HighMemoryRule(Rule):
    """Check if memory usage exceeds 85%"""
    
    def __init__(self):
        super().__init__("high_memory", "warning")
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        if machine.memory_usage > 85:
            return (
                True,
                f"High Memory Usage on {machine.machine_name}",
                f"Memory usage is {machine.memory_usage:.1f}%, exceeding the 85% threshold."
            )
        return (False, "", "")


class PowerOffRule(Rule):
    """Check if VDA is powered off unexpectedly"""
    
    def __init__(self):
        super().__init__("power_off", "info")
    
    def check(self, machine: VDAMachine) -> Tuple[bool, str, str]:
        if machine.power_state == "Off":
            return (
                True,
                f"VDA {machine.machine_name} Powered Off",
                f"{machine.machine_name} is currently powered off."
            )
        return (False, "", "")


class AnalyzerAgent:
    """Analyzes collected metrics and detects issues"""
    
    def __init__(self):
        self.rules: List[Rule] = [
            VDAUnregisteredRule(),
            HighDisconnectRateRule(),
            SessionUnavailableRule(),
            HighCPURule(),
            HighMemoryRule(),
            PowerOffRule(),
        ]
    
    def analyze_metrics(self, db: Session) -> Dict[str, Any]:
        """
        Analyze collected metrics and generate alerts
        
        Returns:
            Dictionary with analysis results
        """
        logger.info("Starting metric analysis...")
        
        try:
            # Get all machines
            machines = db.query(VDAMachine).all()
            
            if not machines:
                logger.info("No machines found in database")
                return {
                    "status": "success",
                    "alerts_generated": 0,
                    "timestamp": datetime.utcnow()
                }
            
            alerts_generated = 0
            
            for machine in machines:
                for rule in self.rules:
                    violated, title, description = rule.check(machine)
                    
                    if violated:
                        # Check if alert already exists and is unresolved
                        existing_alert = db.query(Alert).filter(
                            Alert.machine_name == machine.machine_name,
                            Alert.alert_type == rule.rule_type,
                            Alert.is_resolved == False
                        ).first()
                        
                        if not existing_alert:
                            alert = Alert(
                                alert_type=rule.rule_type,
                                machine_name=machine.machine_name,
                                severity=rule.severity,
                                title=title,
                                description=description,
                            )
                            db.add(alert)
                            alerts_generated += 1
                            logger.info(f"Generated alert: {title}")
                        else:
                            # Update timestamp of existing alert
                            existing_alert.updated_at = datetime.utcnow()
                    else:
                        # Rule not violated, check if we need to resolve existing alert
                        unresolved_alert = db.query(Alert).filter(
                            Alert.machine_name == machine.machine_name,
                            Alert.alert_type == rule.rule_type,
                            Alert.is_resolved == False
                        ).first()
                        
                        if unresolved_alert:
                            unresolved_alert.is_resolved = True
                            unresolved_alert.resolved_at = datetime.utcnow()
                            logger.info(f"Resolved alert: {unresolved_alert.title}")
            
            db.commit()
            
            logger.info(f"Analysis complete. Generated {alerts_generated} new alerts")
            return {
                "status": "success",
                "machines_analyzed": len(machines),
                "alerts_generated": alerts_generated,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error during metric analysis: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }
    
    def get_active_alerts(self, db: Session) -> List[Alert]:
        """Get all active (unresolved) alerts"""
        return db.query(Alert).filter(Alert.is_resolved == False).all()
