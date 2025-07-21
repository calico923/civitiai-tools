#!/usr/bin/env python3
"""
Uptime and Availability Monitoring.
Implements requirement 17.1: 99.5% uptime target with availability tracking.
"""

import logging
import time
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status levels."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    MAINTENANCE = "maintenance"


@dataclass
class UptimeRecord:
    """Individual uptime measurement record."""
    timestamp: float
    status: ServiceStatus
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    component: str = "system"


@dataclass
class AvailabilityMetrics:
    """Availability calculation results."""
    uptime_percentage: float
    total_uptime: float
    total_downtime: float
    total_period: float
    incident_count: int
    average_response_time: float
    mttr: float  # Mean Time To Recovery
    mtbf: float  # Mean Time Between Failures


class UptimeMonitor:
    """
    Monitors system uptime and availability.
    Implements requirement 17.1: 99.5% uptime monitoring.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize uptime monitor.
        
        Args:
            data_dir: Application data directory
        """
        self.data_dir = data_dir
        self.monitor_db = data_dir / "uptime.db"
        self.start_time = time.time()
        self.current_status = ServiceStatus.OPERATIONAL
        self.last_status_change = self.start_time
        
        # Components to monitor
        self.components = {
            "api": "CivitAI API connectivity",
            "database": "Local database operations", 
            "filesystem": "File system operations",
            "network": "Network connectivity",
            "system": "Overall system health"
        }
        
        # Status tracking
        self.status_history: List[UptimeRecord] = []
        self.current_incident_start: Optional[float] = None
        
        # Initialize database
        self._initialize_uptime_db()
    
    def _initialize_uptime_db(self) -> None:
        """Initialize uptime tracking database."""
        try:
            with sqlite3.connect(self.monitor_db) as conn:
                cursor = conn.cursor()
                
                # Uptime records table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS uptime_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        component TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_time REAL,
                        error_message TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Incidents table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS incidents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        component TEXT NOT NULL,
                        start_time REAL NOT NULL,
                        end_time REAL,
                        duration REAL,
                        severity TEXT NOT NULL,
                        description TEXT,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Availability summaries table (daily/hourly rollups)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS availability_summary (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        component TEXT NOT NULL,
                        period_start REAL NOT NULL,
                        period_end REAL NOT NULL,
                        period_type TEXT NOT NULL,  -- 'hour', 'day', 'month'
                        uptime_seconds REAL NOT NULL,
                        downtime_seconds REAL NOT NULL,
                        availability_percentage REAL NOT NULL,
                        incident_count INTEGER DEFAULT 0,
                        average_response_time REAL,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_uptime_timestamp ON uptime_records(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_uptime_component ON uptime_records(component)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_component ON incidents(component)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_period ON availability_summary(period_start, period_end)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize uptime database: {e}")
    
    async def record_status(self, component: str, status: ServiceStatus, 
                          response_time: Optional[float] = None,
                          error_message: Optional[str] = None) -> None:
        """
        Record system status for a component.
        
        Args:
            component: Component name
            status: Current status
            response_time: Response time if applicable
            error_message: Error message if status is not operational
        """
        current_time = time.time()
        
        record = UptimeRecord(
            timestamp=current_time,
            status=status,
            response_time=response_time,
            error_message=error_message,
            component=component
        )
        
        self.status_history.append(record)
        
        # Keep only recent history in memory (last 1000 records)
        if len(self.status_history) > 1000:
            self.status_history = self.status_history[-1000:]
        
        # Store in database
        try:
            with sqlite3.connect(self.monitor_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO uptime_records 
                    (timestamp, component, status, response_time, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, (current_time, component, status.value, response_time, error_message))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to record uptime status: {e}")
        
        # Handle status changes for incidents
        if component == "system":
            await self._handle_system_status_change(status, current_time, error_message)
    
    async def _handle_system_status_change(self, new_status: ServiceStatus, 
                                         timestamp: float, error_message: Optional[str]) -> None:
        """Handle system-wide status changes and incident tracking."""
        if new_status == self.current_status:
            return  # No change
        
        previous_status = self.current_status
        self.current_status = new_status
        
        # If transitioning from operational to non-operational, start incident
        if (previous_status == ServiceStatus.OPERATIONAL and 
            new_status != ServiceStatus.OPERATIONAL):
            self.current_incident_start = timestamp
            
            await self._create_incident("system", timestamp, new_status, error_message)
            logger.warning(f"System incident started: {new_status.value}")
        
        # If transitioning back to operational, end incident
        elif (previous_status != ServiceStatus.OPERATIONAL and 
              new_status == ServiceStatus.OPERATIONAL):
            if self.current_incident_start:
                duration = timestamp - self.current_incident_start
                await self._resolve_incident("system", timestamp, duration)
                logger.info(f"System incident resolved after {duration:.1f} seconds")
                self.current_incident_start = None
        
        self.last_status_change = timestamp
    
    async def _create_incident(self, component: str, start_time: float,
                             severity: ServiceStatus, description: Optional[str]) -> None:
        """Create a new incident record."""
        try:
            with sqlite3.connect(self.monitor_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO incidents 
                    (component, start_time, severity, description)
                    VALUES (?, ?, ?, ?)
                """, (component, start_time, severity.value, description))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create incident record: {e}")
    
    async def _resolve_incident(self, component: str, end_time: float, duration: float) -> None:
        """Resolve the most recent open incident for a component."""
        try:
            with sqlite3.connect(self.monitor_db) as conn:
                cursor = conn.cursor()
                
                # Find the most recent unresolved incident
                cursor.execute("""
                    SELECT id FROM incidents 
                    WHERE component = ? AND resolved = FALSE 
                    ORDER BY start_time DESC LIMIT 1
                """, (component,))
                
                result = cursor.fetchone()
                if result:
                    incident_id = result[0]
                    cursor.execute("""
                        UPDATE incidents 
                        SET end_time = ?, duration = ?, resolved = TRUE 
                        WHERE id = ?
                    """, (end_time, duration, incident_id))
                    conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to resolve incident: {e}")
    
    async def calculate_availability(self, component: str = "system",
                                   period_hours: int = 24) -> AvailabilityMetrics:
        """
        Calculate availability metrics for a given period.
        
        Args:
            component: Component to analyze
            period_hours: Period in hours to analyze
            
        Returns:
            AvailabilityMetrics with calculated values
        """
        end_time = time.time()
        start_time = end_time - (period_hours * 3600)
        
        try:
            with sqlite3.connect(self.monitor_db) as conn:
                cursor = conn.cursor()
                
                # Get all status records in period
                cursor.execute("""
                    SELECT timestamp, status, response_time 
                    FROM uptime_records 
                    WHERE component = ? AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp
                """, (component, start_time, end_time))
                
                records = cursor.fetchall()
                
                if not records:
                    # No data available
                    return AvailabilityMetrics(
                        uptime_percentage=0.0,
                        total_uptime=0.0,
                        total_downtime=period_hours * 3600,
                        total_period=period_hours * 3600,
                        incident_count=0,
                        average_response_time=0.0,
                        mttr=0.0,
                        mtbf=0.0
                    )
                
                # Calculate uptime/downtime
                total_uptime = 0.0
                total_downtime = 0.0
                response_times = []
                
                # Process records to calculate availability
                for i, (timestamp, status, response_time) in enumerate(records):
                    # Duration until next record (or end of period)
                    if i < len(records) - 1:
                        duration = records[i + 1][0] - timestamp
                    else:
                        duration = end_time - timestamp
                    
                    if status == ServiceStatus.OPERATIONAL.value:
                        total_uptime += duration
                    else:
                        total_downtime += duration
                    
                    if response_time is not None:
                        response_times.append(response_time)
                
                # Get incident data
                cursor.execute("""
                    SELECT COUNT(*), AVG(duration) 
                    FROM incidents 
                    WHERE component = ? AND start_time BETWEEN ? AND ? AND resolved = TRUE
                """, (component, start_time, end_time))
                
                incident_result = cursor.fetchone()
                incident_count = incident_result[0] if incident_result else 0
                avg_incident_duration = incident_result[1] if incident_result and incident_result[1] else 0.0
                
                # Calculate metrics
                total_period = period_hours * 3600
                uptime_percentage = (total_uptime / total_period) * 100 if total_period > 0 else 0.0
                average_response_time = sum(response_times) / len(response_times) if response_times else 0.0
                
                # MTTR (Mean Time To Recovery) - average incident duration
                mttr = avg_incident_duration
                
                # MTBF (Mean Time Between Failures)
                if incident_count > 1:
                    mtbf = total_period / incident_count
                else:
                    mtbf = total_period  # No failures or only one failure
                
                return AvailabilityMetrics(
                    uptime_percentage=uptime_percentage,
                    total_uptime=total_uptime,
                    total_downtime=total_downtime,
                    total_period=total_period,
                    incident_count=incident_count,
                    average_response_time=average_response_time,
                    mttr=mttr,
                    mtbf=mtbf
                )
                
        except Exception as e:
            logger.error(f"Failed to calculate availability metrics: {e}")
            return AvailabilityMetrics(0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, 0.0)
    
    async def get_uptime_summary(self, period_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive uptime summary for all components."""
        summary = {
            "period_hours": period_hours,
            "components": {},
            "overall": None,
            "sla_compliance": {},
            "current_status": self.current_status.value,
            "system_uptime": time.time() - self.start_time
        }
        
        # Calculate metrics for each component
        for component in list(self.components.keys()) + ["system"]:
            metrics = await self.calculate_availability(component, period_hours)
            
            summary["components"][component] = {
                "availability": metrics.uptime_percentage,
                "uptime_seconds": metrics.total_uptime,
                "downtime_seconds": metrics.total_downtime,
                "incident_count": metrics.incident_count,
                "average_response_time": metrics.average_response_time,
                "mttr": metrics.mttr,
                "mtbf": metrics.mtbf
            }
            
            # SLA compliance check (99.5% target)
            sla_target = 99.5
            summary["sla_compliance"][component] = {
                "target": sla_target,
                "actual": metrics.uptime_percentage,
                "compliant": metrics.uptime_percentage >= sla_target,
                "shortfall": max(0, sla_target - metrics.uptime_percentage)
            }
        
        # Overall system metrics
        if "system" in summary["components"]:
            summary["overall"] = summary["components"]["system"]
        
        return summary
    
    async def get_recent_incidents(self, hours: int = 24, 
                                 component: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent incidents within the specified period."""
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        try:
            with sqlite3.connect(self.monitor_db) as conn:
                cursor = conn.cursor()
                
                if component:
                    cursor.execute("""
                        SELECT component, start_time, end_time, duration, severity, description, resolved
                        FROM incidents 
                        WHERE component = ? AND start_time >= ?
                        ORDER BY start_time DESC
                    """, (component, start_time))
                else:
                    cursor.execute("""
                        SELECT component, start_time, end_time, duration, severity, description, resolved
                        FROM incidents 
                        WHERE start_time >= ?
                        ORDER BY start_time DESC
                    """, (start_time,))
                
                incidents = []
                for row in cursor.fetchall():
                    incidents.append({
                        "component": row[0],
                        "start_time": row[1],
                        "end_time": row[2],
                        "duration": row[3],
                        "severity": row[4],
                        "description": row[5],
                        "resolved": bool(row[6]),
                        "start_datetime": datetime.fromtimestamp(row[1]).isoformat(),
                        "end_datetime": datetime.fromtimestamp(row[2]).isoformat() if row[2] else None
                    })
                
                return incidents
                
        except Exception as e:
            logger.error(f"Failed to get recent incidents: {e}")
            return []
    
    async def generate_availability_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive availability report."""
        report = {
            "period_days": period_days,
            "report_generated": datetime.now().isoformat(),
            "summary": {},
            "daily_breakdown": [],
            "incidents": [],
            "trends": {},
            "recommendations": []
        }
        
        # Get overall summary
        report["summary"] = await self.get_uptime_summary(period_days * 24)
        
        # Get daily breakdown
        for day in range(period_days):
            day_start = time.time() - ((day + 1) * 86400)
            day_metrics = await self.calculate_availability("system", 24)
            
            report["daily_breakdown"].append({
                "date": datetime.fromtimestamp(day_start).strftime("%Y-%m-%d"),
                "availability": day_metrics.uptime_percentage,
                "incidents": day_metrics.incident_count,
                "average_response_time": day_metrics.average_response_time
            })
        
        # Get all incidents in period
        report["incidents"] = await self.get_recent_incidents(period_days * 24)
        
        # Calculate trends
        if len(report["daily_breakdown"]) >= 7:
            recent_week = report["daily_breakdown"][:7]
            previous_week = report["daily_breakdown"][7:14] if len(report["daily_breakdown"]) >= 14 else []
            
            recent_avg = sum(d["availability"] for d in recent_week) / len(recent_week)
            
            if previous_week:
                previous_avg = sum(d["availability"] for d in previous_week) / len(previous_week)
                trend = "improving" if recent_avg > previous_avg else "degrading" if recent_avg < previous_avg else "stable"
            else:
                trend = "stable"
            
            report["trends"] = {
                "availability_trend": trend,
                "recent_week_average": recent_avg,
                "previous_week_average": sum(d["availability"] for d in previous_week) / len(previous_week) if previous_week else None
            }
        
        # Generate recommendations
        overall_availability = report["summary"]["overall"]["availability"] if report["summary"]["overall"] else 0
        
        if overall_availability < 99.5:
            report["recommendations"].append("System availability is below SLA target of 99.5%")
        
        if len(report["incidents"]) > 5:
            report["recommendations"].append("High incident frequency detected - review system stability")
        
        high_mttr = any(
            comp["mttr"] > 300  # 5 minutes
            for comp in report["summary"]["components"].values()
            if comp["mttr"] > 0
        )
        
        if high_mttr:
            report["recommendations"].append("Mean Time To Recovery is high - improve incident response")
        
        return report


class AvailabilityTracker:
    """
    High-level availability tracking and SLA monitoring.
    Implements requirement 17.1: SLA tracking and alerting.
    """
    
    def __init__(self, uptime_monitor: UptimeMonitor):
        """Initialize with an uptime monitor instance."""
        self.uptime_monitor = uptime_monitor
        self.sla_targets = {
            "system": 99.5,      # 99.5% overall system availability
            "api": 99.0,         # 99.0% API availability
            "database": 99.8,    # 99.8% database availability
            "filesystem": 99.9   # 99.9% filesystem availability
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "availability_warning": 99.0,   # Warn if below 99%
            "availability_critical": 98.0,  # Critical if below 98%
            "incident_count_daily": 5,      # Alert if >5 incidents per day
            "mttr_threshold": 600           # Alert if MTTR > 10 minutes
        }
    
    async def check_sla_compliance(self, period_hours: int = 24) -> Dict[str, Any]:
        """Check SLA compliance for all components."""
        compliance_report = {
            "period_hours": period_hours,
            "overall_compliant": True,
            "components": {},
            "violations": [],
            "alerts": []
        }
        
        for component, target in self.sla_targets.items():
            metrics = await self.uptime_monitor.calculate_availability(component, period_hours)
            
            is_compliant = metrics.uptime_percentage >= target
            shortfall = max(0, target - metrics.uptime_percentage)
            
            compliance_report["components"][component] = {
                "target": target,
                "actual": metrics.uptime_percentage,
                "compliant": is_compliant,
                "shortfall": shortfall
            }
            
            if not is_compliant:
                compliance_report["overall_compliant"] = False
                compliance_report["violations"].append({
                    "component": component,
                    "target": target,
                    "actual": metrics.uptime_percentage,
                    "shortfall": shortfall
                })
            
            # Generate alerts
            if metrics.uptime_percentage < self.alert_thresholds["availability_critical"]:
                compliance_report["alerts"].append({
                    "severity": "critical",
                    "component": component,
                    "message": f"Critical: {component} availability at {metrics.uptime_percentage:.2f}%"
                })
            elif metrics.uptime_percentage < self.alert_thresholds["availability_warning"]:
                compliance_report["alerts"].append({
                    "severity": "warning", 
                    "component": component,
                    "message": f"Warning: {component} availability at {metrics.uptime_percentage:.2f}%"
                })
            
            if metrics.incident_count > self.alert_thresholds["incident_count_daily"] and period_hours <= 24:
                compliance_report["alerts"].append({
                    "severity": "warning",
                    "component": component,
                    "message": f"High incident count: {metrics.incident_count} incidents in {period_hours}h"
                })
            
            if metrics.mttr > self.alert_thresholds["mttr_threshold"]:
                compliance_report["alerts"].append({
                    "severity": "warning",
                    "component": component,
                    "message": f"High MTTR: {metrics.mttr:.1f}s for {component}"
                })
        
        return compliance_report
    
    async def get_availability_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data for availability monitoring."""
        dashboard = {
            "current_time": datetime.now().isoformat(),
            "system_status": self.uptime_monitor.current_status.value,
            "system_uptime": time.time() - self.uptime_monitor.start_time,
            "last_24h": {},
            "last_7d": {},
            "last_30d": {},
            "sla_compliance": {},
            "active_incidents": []
        }
        
        # Get metrics for different periods
        for period_key, period_hours in [("last_24h", 24), ("last_7d", 168), ("last_30d", 720)]:
            summary = await self.uptime_monitor.get_uptime_summary(period_hours)
            dashboard[period_key] = summary
        
        # SLA compliance check
        dashboard["sla_compliance"] = await self.check_sla_compliance(24)
        
        # Active incidents (unresolved)
        all_incidents = await self.uptime_monitor.get_recent_incidents(168)  # Last week
        dashboard["active_incidents"] = [
            incident for incident in all_incidents
            if not incident["resolved"]
        ]
        
        return dashboard