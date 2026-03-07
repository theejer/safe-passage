"""Configuration and thresholds for performance tests."""

from typing import Dict, Any


class PerformanceConfig:
    """Performance test thresholds and configuration."""
    
    # Connectivity Predictor Thresholds
    CONNECTIVITY_ACCURACY_TARGET = 0.75  # 75% accuracy
    CONNECTIVITY_P99_LATENCY_MS = 200
    CONNECTIVITY_P95_LATENCY_MS = 100
    CONNECTIVITY_P50_LATENCY_MS = 50
    CONNECTIVITY_FALLBACK_MAX_PERCENT = 0.10  # 10% max fallback usage
    CONNECTIVITY_MIN_CONFIDENCE_CORRELATION = 0.70  # Confidence calibration
    
    # Heartbeat Ingestion Thresholds
    HEARTBEAT_BASELINE_LATENCY_MS = 100
    HEARTBEAT_P95_LATENCY_50_CONCURRENT_MS = 200
    HEARTBEAT_P95_LATENCY_100_CONCURRENT_MS = 250
    HEARTBEAT_P95_LATENCY_500_CONCURRENT_MS = 500
    HEARTBEAT_MIN_THROUGHPUT_PER_SEC = 100
    HEARTBEAT_MAX_ERROR_RATE = 0.01  # 1% max error rate
    
    # Watchdog Cycle Thresholds
    WATCHDOG_MAX_DURATION_100_TRIPS_SEC = 10
    WATCHDOG_MAX_DURATION_500_TRIPS_SEC = 20
    WATCHDOG_MAX_DURATION_1000_TRIPS_SEC = 30
    WATCHDOG_PER_TRIP_P95_MS = 150
    WATCHDOG_PER_TRIP_P50_MS = 50
    WATCHDOG_MAX_MEMORY_MB = 500
    
    # Emergency Escalation Thresholds
    ESCALATION_STAGE_TRANSITION_ACCURACY = 1.0  # 100%
    ESCALATION_MAX_FALSE_POSITIVE_RATE = 0.05  # 5%
    ESCALATION_REARM_ENFORCEMENT = 1.0  # 100%
    ESCALATION_DEDUP_ACCURACY = 1.0  # 100%
    
    # Alert Delivery Thresholds
    ALERT_MIN_DELIVERY_SUCCESS_RATE = 0.95  # 95%
    ALERT_P95_DELIVERY_LATENCY_SEC = 5.0
    ALERT_P50_DELIVERY_LATENCY_SEC = 2.0
    ALERT_STORM_DEDUP_ACCURACY = 0.95  # 95%
    
    # Test Execution Config
    TEST_TIMEOUT_SECONDS = 600  # 10 minutes per test category
    DATABASE_CLEANUP = True  # Clean up test data after each run
    
    # Color Coding Thresholds
    PASS_THRESHOLD = 1.0  # 100% of target = green
    WARN_THRESHOLD = 0.80  # 80-99% of target = yellow
    # Below 80% = red (fail)
    
    @classmethod
    def get_threshold_color(cls, actual: float, target: float, inverse: bool = False) -> str:
        """
        Determine color based on actual vs target.
        
        Args:
            actual: Actual measured value
            target: Target threshold value
            inverse: If True, lower is better (e.g., latency)
        
        Returns:
            'green', 'yellow', or 'red'
        """
        if inverse:
            # Lower is better (e.g., latency, error rate)
            ratio = target / actual if actual > 0 else float('inf')
        else:
            # Higher is better (e.g., accuracy, throughput)
            ratio = actual / target if target > 0 else 0
        
        if ratio >= cls.PASS_THRESHOLD:
            return 'green'
        elif ratio >= cls.WARN_THRESHOLD:
            return 'yellow'
        else:
            return 'red'
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Export all thresholds as dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and key.isupper()
        }
