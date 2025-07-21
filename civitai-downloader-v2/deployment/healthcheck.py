#!/usr/bin/env python3
"""
Health check script for Docker container.
Returns exit code 0 if healthy, 1 if unhealthy.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.core.reliability.health_check import HealthChecker, HealthStatus
    from src.core.config.manager import ConfigManager
except ImportError as e:
    print(f"Failed to import health check modules: {e}")
    sys.exit(1)

async def main():
    """Run health check."""
    try:
        # Initialize basic configuration
        config_manager = ConfigManager()
        
        # Create health checker
        health_checker = HealthChecker()
        
        # Perform health check
        health = await health_checker.check_system_health()
        
        # Determine if system is healthy
        if health.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]:
            print(f"Health check PASSED - Status: {health.status.value}")
            print(f"CPU: {health.metrics.get('cpu_usage', 'N/A')}%")
            print(f"Memory: {health.metrics.get('memory_usage', 'N/A')}%")
            sys.exit(0)
        else:
            print(f"Health check FAILED - Status: {health.status.value}")
            for issue in health.issues:
                print(f"Issue: {issue}")
            sys.exit(1)
            
    except Exception as e:
        print(f"Health check ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())