"""
AI Agent - Responsible for explaining alerts and suggesting fixes using Ollama
"""

import logging
import os
from typing import Dict, Any
from sqlalchemy.orm import Session

from models.schemas import Alert

logger = logging.getLogger(__name__)

# Try to import ollama, but don't fail if not available
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama library not available, will use fallback explanations")


class AIAgent:
    """Uses Ollama for AI-powered explanations and suggestions"""
    
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "mistral")
        self.timeout = 30  # seconds
    
    def explain_alert(self, alert: Alert) -> Dict[str, Any]:
        """
        Use AI to explain alert root cause and suggest fixes
        
        Args:
            alert: Alert object to explain
            
        Returns:
            Dictionary with root_cause and suggested_fix
        """
        logger.info(f"Generating AI explanation for alert: {alert.title}")
        
        try:
            prompt = self._build_prompt(alert)
            
            if OLLAMA_AVAILABLE:
                response = self._call_ollama(prompt)
            else:
                logger.warning("Using fallback explanation (Ollama not available)")
                response = self._get_fallback_explanation(alert)
            
            return {
                "root_cause": response.get("root_cause", ""),
                "suggested_fix": response.get("suggested_fix", ""),
                "generated_by_ai": response.get("generated_by_ai", False)
            }
            
        except Exception as e:
            logger.error(f"Error explaining alert: {e}")
            return {
                "root_cause": "Unable to generate explanation",
                "suggested_fix": "Please check logs for details",
                "generated_by_ai": False
            }
    
    def _build_prompt(self, alert: Alert) -> str:
        """Build prompt for Ollama"""
        return f"""Analyze this Citrix DaaS alert and provide technical explanation:

Alert Type: {alert.alert_type}
Machine: {alert.machine_name}
Title: {alert.title}
Description: {alert.description}

Provide response in this exact format:
ROOT_CAUSE: [Technical explanation of why this happened]
SUGGESTED_FIX: [Practical steps to resolve the issue]

Keep responses concise and technical."""
    
    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API"""
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=False,
                options={
                    "temperature": 0.3,  # Lower temperature for more deterministic output
                    "top_p": 0.9,
                    "top_k": 40,
                }
            )
            
            text = response.get("response", "")
            return self._parse_ollama_response(text)
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            raise
    
    def _parse_ollama_response(self, text: str) -> Dict[str, Any]:
        """Parse Ollama response"""
        root_cause = "Unknown"
        suggested_fix = "Unknown"
        
        try:
            lines = text.split("\n")
            for line in lines:
                if line.startswith("ROOT_CAUSE:"):
                    root_cause = line.replace("ROOT_CAUSE:", "").strip()
                elif line.startswith("SUGGESTED_FIX:"):
                    suggested_fix = line.replace("SUGGESTED_FIX:", "").strip()
            
            return {
                "root_cause": root_cause,
                "suggested_fix": suggested_fix,
                "generated_by_ai": True
            }
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {e}")
            return {
                "root_cause": "Unable to parse response",
                "suggested_fix": "Please check system logs",
                "generated_by_ai": False
            }
    
    def _get_fallback_explanation(self, alert: Alert) -> Dict[str, Any]:
        """Provide fallback explanations when Ollama is not available"""
        
        explanations = {
            "vda_unregistered": {
                "root_cause": "The VDA has lost connection to the Citrix Broker or Delivery Controller. "
                             "This could be due to network issues, broker unavailability, or VDA service failure.",
                "suggested_fix": "1. Check network connectivity between VDA and Delivery Controller. "
                                "2. Verify Citrix Broker/Controller services are running and accessible. "
                                "3. Check VDA event logs for errors. "
                                "4. Restart the Citrix Desktop Service on the affected VDA if needed."
            },
            "high_disconnect_rate": {
                "root_cause": "Users are experiencing frequent session disconnections. This indicates instability "
                             "in user sessions, possibly due to network latency, resource constraints, or service issues.",
                "suggested_fix": "1. Review network latency and packet loss between clients and VDA. "
                                "2. Check system resources (CPU, Memory, Disk) on the VDA. "
                                "3. Review event logs for session/protocol errors. "
                                "4. Consider load balancing across multiple VDAs if available."
            },
            "session_unavailable": {
                "root_cause": "Multiple user sessions on this VDA are in an unavailable state. "
                             "This typically indicates a resource constraint or service degradation.",
                "suggested_fix": "1. Check CPU, memory, and disk usage on the VDA. "
                                "2. Review Session Manager logs for session creation errors. "
                                "3. Verify user account permissions and licenses. "
                                "4. Consider rebooting the VDA during a maintenance window if necessary."
            },
            "high_cpu": {
                "root_cause": "CPU utilization exceeds safe operating thresholds. This could be caused by "
                             "heavy user workloads, rogue processes, or inadequate resource allocation.",
                "suggested_fix": "1. Identify processes consuming high CPU using Task Manager. "
                                "2. Check for runaway or unnecessary services. "
                                "3. Consider enabling load-based session limits. "
                                "4. Plan for additional VDAs if this is normal workload."
            },
            "high_memory": {
                "root_cause": "Memory utilization exceeds safe operating thresholds. This may indicate memory leaks, "
                             "excessive user sessions, or resource-intensive applications.",
                "suggested_fix": "1. Review memory usage per process in Task Manager. "
                                "2. Check for known memory leak issues in installed applications. "
                                "3. Configure memory-based session limits if available. "
                                "4. Consider upgrading VDA RAM or adding more VDAs."
            },
            "power_off": {
                "root_cause": "The VDA machine is currently powered off, making it unavailable to serve user sessions.",
                "suggested_fix": "1. Power on the VDA machine. "
                                "2. Verify it boots successfully and services initialize. "
                                "3. Confirm it re-registers with the Delivery Controller. "
                                "4. Check why it was powered off if this was not scheduled."
            },
        }
        
        # Return explanation if available, otherwise generic response
        if alert.alert_type in explanations:
            return {
                "root_cause": explanations[alert.alert_type]["root_cause"],
                "suggested_fix": explanations[alert.alert_type]["suggested_fix"],
                "generated_by_ai": False
            }
        else:
            return {
                "root_cause": "Alert type not recognized in knowledge base",
                "suggested_fix": "Please review the alert details and Citrix documentation",
                "generated_by_ai": False
            }
