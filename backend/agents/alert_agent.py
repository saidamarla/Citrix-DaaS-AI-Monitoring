"""
Alert Agent - Responsible for processing alerts and enriching them with AI explanations
"""

import logging
from typing import Dict, Any
from sqlalchemy.orm import Session

from models.schemas import Alert
from agents.ai_agent import AIAgent

logger = logging.getLogger(__name__)


class AlertAgent:
    """Processes alerts and enriches them with AI-generated explanations"""
    
    def __init__(self):
        self.ai_agent = AIAgent()
    
    def process_alerts(self, db: Session) -> Dict[str, Any]:
        """
        Process all active alerts and enrich with AI explanations
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with processing results
        """
        logger.info("Starting alert processing...")
        
        try:
            # Get alerts that don't have AI explanations yet
            unprocessed_alerts = db.query(Alert).filter(
                Alert.is_resolved == False,
                Alert.root_cause.is_(None)
            ).all()
            
            alerts_processed = 0
            
            for alert in unprocessed_alerts:
                logger.info(f"Processing alert {alert.id}: {alert.title}")
                
                # Generate AI explanation
                explanation = self.ai_agent.explain_alert(alert)
                
                # Update alert with explanation
                alert.root_cause = explanation.get("root_cause")
                alert.suggested_fix = explanation.get("suggested_fix")
                
                db.commit()
                alerts_processed += 1
            
            logger.info(f"Alert processing complete. Processed {alerts_processed} alerts")
            
            return {
                "status": "success",
                "alerts_processed": alerts_processed,
                "total_active_alerts": db.query(Alert).filter(
                    Alert.is_resolved == False
                ).count()
            }
            
        except Exception as e:
            logger.error(f"Error processing alerts: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_alert_summary(self, db: Session) -> Dict[str, Any]:
        """Get summary of all alerts"""
        try:
            active_alerts = db.query(Alert).filter(Alert.is_resolved == False).all()
            
            critical_count = len([a for a in active_alerts if a.severity == "critical"])
            warning_count = len([a for a in active_alerts if a.severity == "warning"])
            info_count = len([a for a in active_alerts if a.severity == "info"])
            
            return {
                "total_active": len(active_alerts),
                "critical": critical_count,
                "warning": warning_count,
                "info": info_count,
                "alerts": [
                    {
                        "id": a.id,
                        "title": a.title,
                        "machine": a.machine_name,
                        "severity": a.severity,
                        "description": a.description,
                        "root_cause": a.root_cause,
                        "suggested_fix": a.suggested_fix,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in sorted(active_alerts, key=lambda x: x.created_at, reverse=True)
                ]
            }
        except Exception as e:
            logger.error(f"Error getting alert summary: {e}")
            return {
                "total_active": 0,
                "critical": 0,
                "warning": 0,
                "info": 0,
                "alerts": []
            }
