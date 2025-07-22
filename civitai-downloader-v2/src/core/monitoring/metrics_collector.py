# src/core/monitoring/metrics_collector.py
from typing import Dict, Any, Optional, DefaultDict
from collections import defaultdict
from datetime import datetime
import threading
from ..interfaces.monitoring import IMetricsCollector

class MetricsCollector(IMetricsCollector):
    """メトリクス収集実装"""
    
    def __init__(self):
        self._metrics: DefaultDict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_metric(self, name: str, value: float,
                     tags: Optional[Dict[str, str]] = None) -> None:
        """メトリクスの記録"""
        with self._lock:
            metric_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "value": value,
                "tags": tags or {}
            }
            self._metrics[name].append(metric_data)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """メトリクスサマリーの取得"""
        with self._lock:
            summary = {}
            for name, values in self._metrics.items():
                if values:
                    numeric_values = [v["value"] for v in values]
                    summary[name] = {
                        "count": len(values),
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "avg": sum(numeric_values) / len(numeric_values),
                        "latest": values[-1]["value"]
                    }
            return summary
