"""Centralized metrics collection and aggregation."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics
import json
from pathlib import Path


class MetricsCollector:
    """Collects and aggregates performance metrics across all tests."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.metrics: Dict[str, Dict[str, Any]] = {
            'connectivity': {},
            'heartbeat_load': {},
            'watchdog': {},
            'escalation': {},
            'alert_delivery': {},
            'e2e': {}
        }
        self.test_results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, str]] = []
    
    def add_metric(self, category: str, name: str, value: Any, passed: Optional[bool] = None):
        """Add a single metric to a category."""
        if category not in self.metrics:
            self.metrics[category] = {}
        
        self.metrics[category][name] = {
            'value': value,
            'passed': passed,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def add_latency_metrics(self, category: str, name: str, latencies_ms: List[float]):
        """Calculate and store latency percentiles."""
        if not latencies_ms:
            return
        
        sorted_latencies = sorted(latencies_ms)
        metrics = {
            f'{name}_p50_ms': self._percentile(sorted_latencies, 50),
            f'{name}_p95_ms': self._percentile(sorted_latencies, 95),
            f'{name}_p99_ms': self._percentile(sorted_latencies, 99),
            f'{name}_mean_ms': statistics.mean(latencies_ms),
            f'{name}_min_ms': min(latencies_ms),
            f'{name}_max_ms': max(latencies_ms),
            f'{name}_count': len(latencies_ms)
        }
        
        for metric_name, value in metrics.items():
            self.add_metric(category, metric_name, value)
        
        return metrics
    
    def add_test_result(self, test_name: str, passed: bool, duration_sec: float, 
                       details: Optional[str] = None):
        """Record individual test result."""
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'duration_sec': duration_sec,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def add_error(self, category: str, error: str, details: Optional[str] = None):
        """Record an error that occurred during testing."""
        self.errors.append({
            'category': category,
            'error': error,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for t in self.test_results if t['passed'])
        failed_tests = total_tests - passed_tests
        
        # Count warnings (tests that passed but with warnings)
        warning_tests = 0
        for category, metrics in self.metrics.items():
            for name, data in metrics.items():
                if isinstance(data, dict) and data.get('passed') is False:
                    warning_tests += 1
        
        return {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': failed_tests,
            'warnings': warning_tests,
            'errors': len(self.errors),
            'duration_seconds': (datetime.utcnow() - self.start_time).total_seconds()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all metrics as dictionary."""
        return {
            'timestamp': self.start_time.isoformat(),
            'duration_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
            'summary': self.get_summary(),
            'metrics': self.metrics,
            'test_results': self.test_results,
            'errors': self.errors
        }
    
    def save_json(self, output_dir: Path) -> Path:
        """Save metrics to timestamped JSON file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
        filename = f'performance_{timestamp}.json'
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return filepath
    
    @staticmethod
    def _percentile(sorted_data: List[float], percentile: float) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_data):
            return sorted_data[-1]
        
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def calculate_confusion_matrix(self, predictions: List[bool], 
                                   actuals: List[bool]) -> Dict[str, int]:
        """Calculate confusion matrix for accuracy tests."""
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")
        
        tp = sum(1 for p, a in zip(predictions, actuals) if p and a)
        tn = sum(1 for p, a in zip(predictions, actuals) if not p and not a)
        fp = sum(1 for p, a in zip(predictions, actuals) if p and not a)
        fn = sum(1 for p, a in zip(predictions, actuals) if not p and not a)
        
        total = len(predictions)
        accuracy = (tp + tn) / total if total > 0 else 0.0
        
        return {
            'true_positive': tp,
            'true_negative': tn,
            'false_positive': fp,
            'false_negative': fn,
            'accuracy': accuracy,
            'precision': tp / (tp + fp) if (tp + fp) > 0 else 0.0,
            'recall': tp / (tp + fn) if (tp + fn) > 0 else 0.0
        }
