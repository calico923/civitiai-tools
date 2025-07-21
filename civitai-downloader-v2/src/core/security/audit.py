#!/usr/bin/env python3
"""
Security Auditing System.
Implements requirement 18.1: Comprehensive security auditing and event logging.
"""

import logging
import time
import sqlite3
import json
import hashlib
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from datetime import datetime
import asyncio
import threading

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """Security audit event levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class AuditCategory(Enum):
    """Audit event categories."""
    ACCESS = "access"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_MODIFICATION = "data_modification"
    SECURITY_SCAN = "security_scan"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    SYSTEM = "system"
    COMPLIANCE = "compliance"


@dataclass
class AuditEvent:
    """Security audit event."""
    timestamp: float
    level: AuditLevel
    category: AuditCategory
    event_type: str
    source: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    risk_score: int = 0  # 0-100
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Calculate event hash for integrity."""
        self.event_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """Calculate hash of event data for integrity verification."""
        data = {
            'timestamp': self.timestamp,
            'level': self.level.value,
            'category': self.category.value,
            'event_type': self.event_type,
            'source': self.source,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'resource': self.resource,
            'action': self.action,
            'result': self.result,
            'details': json.dumps(self.details, sort_keys=True),
            'risk_score': self.risk_score
        }
        
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class SecurityAuditor:
    """
    Comprehensive security auditing system.
    Implements requirement 18.1: Security event logging and monitoring.
    """
    
    def __init__(self, data_dir: Path, max_log_size_mb: int = 100):
        """
        Initialize security auditor.
        
        Args:
            data_dir: Data directory for audit logs
            max_log_size_mb: Maximum size of audit log in MB
        """
        self.data_dir = data_dir
        self.audit_db = data_dir / "security_audit.db"
        self.max_log_size = max_log_size_mb * 1024 * 1024
        
        # Event handlers for real-time processing
        self.event_handlers: Dict[AuditLevel, List[Callable]] = {
            level: [] for level in AuditLevel
        }
        
        # Risk threshold settings
        self.risk_thresholds = {
            AuditLevel.INFO: 20,
            AuditLevel.WARNING: 50,
            AuditLevel.CRITICAL: 80,
            AuditLevel.SECURITY: 90
        }
        
        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize database
        self._initialize_audit_db()
        
        # Start background processing
        self._start_background_tasks()
    
    def _initialize_audit_db(self) -> None:
        """Initialize audit database."""
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                
                # Main audit events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        level TEXT NOT NULL,
                        category TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        source TEXT NOT NULL,
                        user_id TEXT,
                        ip_address TEXT,
                        resource TEXT,
                        action TEXT,
                        result TEXT,
                        details TEXT,
                        risk_score INTEGER DEFAULT 0,
                        correlation_id TEXT,
                        session_id TEXT,
                        event_hash TEXT NOT NULL,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Security alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS security_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        audit_event_id INTEGER,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        remediation TEXT,
                        acknowledged BOOLEAN DEFAULT FALSE,
                        acknowledged_by TEXT,
                        acknowledged_at REAL,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        FOREIGN KEY (audit_event_id) REFERENCES audit_events(id)
                    )
                """)
                
                # User sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        ip_address TEXT,
                        start_time REAL NOT NULL,
                        last_activity REAL NOT NULL,
                        end_time REAL,
                        session_data TEXT,
                        risk_score INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'active'
                    )
                """)
                
                # Compliance reports table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS compliance_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_type TEXT NOT NULL,
                        period_start REAL NOT NULL,
                        period_end REAL NOT NULL,
                        total_events INTEGER,
                        critical_events INTEGER,
                        security_events INTEGER,
                        compliance_score REAL,
                        findings TEXT,
                        recommendations TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_level ON audit_events(level)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_category ON audit_events(category)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_events(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON security_alerts(severity)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
    
    def _start_background_tasks(self) -> None:
        """Start background processing tasks."""
        # Start session cleanup task
        def session_cleanup():
            while True:
                try:
                    self._cleanup_expired_sessions()
                    time.sleep(300)  # Run every 5 minutes
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=session_cleanup, daemon=True)
        cleanup_thread.start()
    
    async def log_event(self, event: AuditEvent) -> None:
        """
        Log a security audit event.
        
        Args:
            event: AuditEvent to log
        """
        with self._lock:
            try:
                # Store in database
                with sqlite3.connect(self.audit_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO audit_events (
                            timestamp, level, category, event_type, source,
                            user_id, ip_address, resource, action, result,
                            details, risk_score, correlation_id, session_id, event_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.timestamp, event.level.value, event.category.value,
                        event.event_type, event.source, event.user_id,
                        event.ip_address, event.resource, event.action, event.result,
                        json.dumps(event.details), event.risk_score,
                        event.correlation_id, event.session_id, event.event_hash
                    ))
                    
                    event_id = cursor.lastrowid
                    conn.commit()
                
                # Process event for alerts
                await self._process_event_for_alerts(event, event_id)
                
                # Call event handlers
                for handler in self.event_handlers.get(event.level, []):
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Event handler error: {e}")
                
                # Log to standard logger for immediate visibility
                log_message = (f"AUDIT [{event.level.value.upper()}] "
                             f"{event.category.value}:{event.event_type} "
                             f"from {event.source}")
                
                if event.level == AuditLevel.CRITICAL:
                    logger.critical(log_message)
                elif event.level == AuditLevel.WARNING:
                    logger.warning(log_message)
                elif event.level == AuditLevel.SECURITY:
                    logger.error(f"SECURITY: {log_message}")
                else:
                    logger.info(log_message)
                
            except Exception as e:
                logger.error(f"Failed to log audit event: {e}")
    
    async def _process_event_for_alerts(self, event: AuditEvent, event_id: int) -> None:
        """Process event to generate security alerts if needed."""
        alerts_to_create = []
        
        # High risk score alert
        if event.risk_score >= 80:
            alerts_to_create.append({
                'alert_type': 'high_risk_event',
                'severity': 'critical' if event.risk_score >= 90 else 'warning',
                'title': f'High Risk Security Event (Score: {event.risk_score})',
                'description': f'{event.category.value} event with high risk score',
                'remediation': 'Investigate event details and take appropriate action'
            })
        
        # Multiple failed access attempts
        if (event.category == AuditCategory.AUTHENTICATION and 
            event.result == 'failed' and event.user_id):
            
            # Count recent failures for this user
            recent_failures = await self._count_recent_events(
                category=AuditCategory.AUTHENTICATION,
                result='failed',
                user_id=event.user_id,
                hours=1
            )
            
            if recent_failures >= 5:
                alerts_to_create.append({
                    'alert_type': 'brute_force_attempt',
                    'severity': 'critical',
                    'title': f'Possible Brute Force Attack on {event.user_id}',
                    'description': f'{recent_failures} failed authentication attempts in the last hour',
                    'remediation': 'Consider temporarily locking account and investigating source IP'
                })
        
        # Suspicious IP activity
        if event.ip_address and event.risk_score >= 60:
            recent_events = await self._count_recent_events(
                ip_address=event.ip_address,
                hours=1
            )
            
            if recent_events >= 20:
                alerts_to_create.append({
                    'alert_type': 'suspicious_ip',
                    'severity': 'warning',
                    'title': f'High Activity from IP {event.ip_address}',
                    'description': f'{recent_events} events from this IP in the last hour',
                    'remediation': 'Review IP reputation and consider rate limiting'
                })
        
        # Critical system events
        if event.level == AuditLevel.CRITICAL:
            alerts_to_create.append({
                'alert_type': 'critical_system_event',
                'severity': 'critical',
                'title': f'Critical System Event: {event.event_type}',
                'description': event.details.get('message', 'Critical system event occurred'),
                'remediation': 'Immediate investigation required'
            })
        
        # Create alerts
        for alert_data in alerts_to_create:
            await self._create_security_alert(event_id, alert_data)
    
    async def _create_security_alert(self, event_id: int, alert_data: Dict[str, Any]) -> None:
        """Create a security alert."""
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO security_alerts (
                        audit_event_id, alert_type, severity, title, description, remediation
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_id, alert_data['alert_type'], alert_data['severity'],
                    alert_data['title'], alert_data['description'], alert_data['remediation']
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create security alert: {e}")
    
    async def _count_recent_events(self, hours: int = 1, **filters) -> int:
        """Count recent events matching filters."""
        cutoff_time = time.time() - (hours * 3600)
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                
                # Build query dynamically based on filters
                conditions = ["timestamp >= ?"]
                params = [cutoff_time]
                
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                
                query = f"SELECT COUNT(*) FROM audit_events WHERE {' AND '.join(conditions)}"
                cursor.execute(query, params)
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Failed to count recent events: {e}")
            return 0
    
    def register_event_handler(self, level: AuditLevel, handler: Callable) -> None:
        """Register an event handler for specific audit level."""
        self.event_handlers[level].append(handler)
    
    async def create_session(self, session_id: str, user_id: str, 
                           ip_address: str, session_data: Dict[str, Any] = None) -> None:
        """Create a new user session."""
        current_time = time.time()
        
        self.active_sessions[session_id] = {
            'user_id': user_id,
            'ip_address': ip_address,
            'start_time': current_time,
            'last_activity': current_time,
            'session_data': session_data or {},
            'risk_score': 0
        }
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_sessions (
                        session_id, user_id, ip_address, start_time, last_activity, session_data
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    session_id, user_id, ip_address, current_time, current_time,
                    json.dumps(session_data or {})
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
        
        # Log session creation
        await self.log_event(AuditEvent(
            timestamp=current_time,
            level=AuditLevel.INFO,
            category=AuditCategory.AUTHENTICATION,
            event_type="session_created",
            source="session_manager",
            user_id=user_id,
            ip_address=ip_address,
            session_id=session_id,
            action="create_session",
            result="success"
        ))
    
    async def end_session(self, session_id: str, reason: str = "logout") -> None:
        """End a user session."""
        current_time = time.time()
        
        session = self.active_sessions.pop(session_id, None)
        if not session:
            return
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE user_sessions 
                    SET end_time = ?, status = 'ended'
                    WHERE session_id = ?
                """, (current_time, session_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
        
        # Log session end
        await self.log_event(AuditEvent(
            timestamp=current_time,
            level=AuditLevel.INFO,
            category=AuditCategory.AUTHENTICATION,
            event_type="session_ended",
            source="session_manager",
            user_id=session.get('user_id'),
            ip_address=session.get('ip_address'),
            session_id=session_id,
            action="end_session",
            result="success",
            details={"reason": reason, "duration": current_time - session['start_time']}
        ))
    
    def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        current_time = time.time()
        session_timeout = 3600  # 1 hour
        
        expired_sessions = []
        for session_id, session_data in list(self.active_sessions.items()):
            if current_time - session_data['last_activity'] > session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            asyncio.create_task(self.end_session(session_id, "timeout"))
    
    async def get_security_alerts(self, hours: int = 24, 
                                acknowledged: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get recent security alerts."""
        cutoff_time = time.time() - (hours * 3600)
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT sa.*, ae.timestamp, ae.user_id, ae.ip_address
                    FROM security_alerts sa
                    JOIN audit_events ae ON sa.audit_event_id = ae.id
                    WHERE ae.timestamp >= ?
                """
                params = [cutoff_time]
                
                if acknowledged is not None:
                    query += " AND sa.acknowledged = ?"
                    params.append(acknowledged)
                
                query += " ORDER BY sa.created_at DESC"
                
                cursor.execute(query, params)
                
                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'id': row[0],
                        'audit_event_id': row[1],
                        'alert_type': row[2],
                        'severity': row[3],
                        'title': row[4],
                        'description': row[5],
                        'remediation': row[6],
                        'acknowledged': bool(row[7]),
                        'acknowledged_by': row[8],
                        'acknowledged_at': row[9],
                        'created_at': row[10],
                        'event_timestamp': row[11],
                        'user_id': row[12],
                        'ip_address': row[13]
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get security alerts: {e}")
            return []
    
    async def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> bool:
        """Acknowledge a security alert."""
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE security_alerts 
                    SET acknowledged = TRUE, acknowledged_by = ?, acknowledged_at = ?
                    WHERE id = ?
                """, (acknowledged_by, time.time(), alert_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                
                if success:
                    await self.log_event(AuditEvent(
                        timestamp=time.time(),
                        level=AuditLevel.INFO,
                        category=AuditCategory.SYSTEM,
                        event_type="alert_acknowledged",
                        source="security_auditor",
                        user_id=acknowledged_by,
                        action="acknowledge_alert",
                        result="success",
                        details={"alert_id": alert_id}
                    ))
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def generate_compliance_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate compliance report."""
        end_time = time.time()
        start_time = end_time - (period_days * 86400)
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                
                # Event counts by level
                cursor.execute("""
                    SELECT level, COUNT(*) 
                    FROM audit_events 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY level
                """, (start_time, end_time))
                
                event_counts = dict(cursor.fetchall())
                
                # Event counts by category
                cursor.execute("""
                    SELECT category, COUNT(*) 
                    FROM audit_events 
                    WHERE timestamp BETWEEN ? AND ?
                    GROUP BY category
                """, (start_time, end_time))
                
                category_counts = dict(cursor.fetchall())
                
                # Security alerts
                cursor.execute("""
                    SELECT severity, COUNT(*) 
                    FROM security_alerts sa
                    JOIN audit_events ae ON sa.audit_event_id = ae.id
                    WHERE ae.timestamp BETWEEN ? AND ?
                    GROUP BY severity
                """, (start_time, end_time))
                
                alert_counts = dict(cursor.fetchall())
                
                # Calculate compliance score
                total_events = sum(event_counts.values())
                critical_events = event_counts.get('critical', 0)
                security_events = event_counts.get('security', 0)
                
                if total_events > 0:
                    compliance_score = max(0, 100 - ((critical_events + security_events) / total_events * 100))
                else:
                    compliance_score = 100
                
                report = {
                    'period': {
                        'start_time': start_time,
                        'end_time': end_time,
                        'days': period_days
                    },
                    'summary': {
                        'total_events': total_events,
                        'critical_events': critical_events,
                        'security_events': security_events,
                        'compliance_score': compliance_score
                    },
                    'event_breakdown': {
                        'by_level': event_counts,
                        'by_category': category_counts
                    },
                    'security_alerts': {
                        'by_severity': alert_counts,
                        'total_alerts': sum(alert_counts.values())
                    },
                    'findings': self._generate_compliance_findings(event_counts, alert_counts),
                    'recommendations': self._generate_compliance_recommendations(compliance_score, event_counts, alert_counts)
                }
                
                # Store report
                cursor.execute("""
                    INSERT INTO compliance_reports (
                        report_type, period_start, period_end, total_events,
                        critical_events, security_events, compliance_score,
                        findings, recommendations
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'security_audit', start_time, end_time, total_events,
                    critical_events, security_events, compliance_score,
                    json.dumps(report['findings']), json.dumps(report['recommendations'])
                ))
                conn.commit()
                
                return report
                
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {}
    
    def _generate_compliance_findings(self, event_counts: Dict[str, int], 
                                    alert_counts: Dict[str, int]) -> List[str]:
        """Generate compliance findings."""
        findings = []
        
        critical_count = event_counts.get('critical', 0)
        if critical_count > 10:
            findings.append(f"High number of critical events: {critical_count}")
        
        critical_alerts = alert_counts.get('critical', 0)
        if critical_alerts > 5:
            findings.append(f"Multiple critical security alerts: {critical_alerts}")
        
        if event_counts.get('security', 0) > 0:
            findings.append("Security-level events detected requiring attention")
        
        return findings
    
    def _generate_compliance_recommendations(self, compliance_score: float,
                                           event_counts: Dict[str, int],
                                           alert_counts: Dict[str, int]) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        if compliance_score < 95:
            recommendations.append("Improve security monitoring to achieve >95% compliance score")
        
        if event_counts.get('critical', 0) > 5:
            recommendations.append("Investigate root causes of critical events")
        
        if alert_counts.get('critical', 0) > 2:
            recommendations.append("Implement automated response for critical security alerts")
        
        if not recommendations:
            recommendations.append("Maintain current security posture and monitoring practices")
        
        return recommendations
    
    async def get_audit_statistics(self, period_hours: int = 24) -> Dict[str, Any]:
        """Get audit statistics for dashboard."""
        cutoff_time = time.time() - (period_hours * 3600)
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                
                # Total events
                cursor.execute("SELECT COUNT(*) FROM audit_events WHERE timestamp >= ?", (cutoff_time,))
                total_events = cursor.fetchone()[0]
                
                # Events by level
                cursor.execute("""
                    SELECT level, COUNT(*) 
                    FROM audit_events 
                    WHERE timestamp >= ?
                    GROUP BY level
                """, (cutoff_time,))
                events_by_level = dict(cursor.fetchall())
                
                # Active sessions
                active_sessions = len(self.active_sessions)
                
                # Unacknowledged alerts
                cursor.execute("""
                    SELECT COUNT(*) FROM security_alerts sa
                    JOIN audit_events ae ON sa.audit_event_id = ae.id
                    WHERE ae.timestamp >= ? AND sa.acknowledged = FALSE
                """, (cutoff_time,))
                unacknowledged_alerts = cursor.fetchone()[0]
                
                return {
                    'period_hours': period_hours,
                    'total_events': total_events,
                    'events_by_level': events_by_level,
                    'active_sessions': active_sessions,
                    'unacknowledged_alerts': unacknowledged_alerts,
                    'events_per_hour': total_events / period_hours if period_hours > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {}
    
    def cleanup_old_events(self, max_age_days: int = 90) -> int:
        """Clean up old audit events."""
        cutoff_time = time.time() - (max_age_days * 86400)
        
        try:
            with sqlite3.connect(self.audit_db) as conn:
                cursor = conn.cursor()
                
                # Delete old events
                cursor.execute("DELETE FROM audit_events WHERE timestamp < ?", (cutoff_time,))
                deleted_events = cursor.rowcount
                
                # Delete orphaned alerts
                cursor.execute("""
                    DELETE FROM security_alerts 
                    WHERE audit_event_id NOT IN (SELECT id FROM audit_events)
                """)
                deleted_alerts = cursor.rowcount
                
                conn.commit()
                
                if deleted_events > 0 or deleted_alerts > 0:
                    logger.info(f"Cleaned up {deleted_events} old audit events and {deleted_alerts} orphaned alerts")
                
                return deleted_events
                
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return 0