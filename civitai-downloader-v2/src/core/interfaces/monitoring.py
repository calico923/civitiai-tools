# src/core/interfaces/monitoring.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class IStructuredLogger(ABC):
    """構造化ログインターフェース（仕様書準拠）"""
    
    @abstractmethod
    def log_structured(self, level: LogLevel, message: str, 
                      context: Dict[str, Any]) -> None:
        """構造化ログの記録"""
        pass
    
    @abstractmethod
    def log_performance(self, operation: str, duration: float,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """パフォーマンスログの記録"""
        pass
    
    @abstractmethod
    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """エラーログの記録"""
        pass
    
    @abstractmethod
    def configure_rotation(self, max_size: int, backup_count: int) -> None:
        """ログローテーション設定"""
        pass

class IMetricsCollector(ABC):
    """メトリクス収集インターフェース"""
    
    @abstractmethod
    def record_metric(self, name: str, value: float, 
                     tags: Optional[Dict[str, str]] = None) -> None:
        """メトリクスの記録"""
        pass
    
    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """メトリクスサマリーの取得"""
        pass
