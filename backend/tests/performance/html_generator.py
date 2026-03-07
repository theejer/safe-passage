"""HTML report generator with charts and visualizations."""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime


class HTMLGenerator:
    """Generate portfolio-ready HTML performance report."""
    
    def __init__(self, metrics: Dict[str, Any], config: Any):
        self.metrics = metrics
        self.config = config
    
    def generate(self, output_path: Path) -> Path:
        """Generate HTML report and save to file."""
        html_content = self._build_html()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def _build_html(self) -> str:
        """Build complete HTML document."""
        summary = self.metrics.get('summary', {})
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Safe Passage Performance Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛡️ Safe Passage Performance Report</h1>
            <p class="subtitle">Heartbeat Monitoring & Emergency Escalation Test Results</p>
            <div class="metadata">
                <span>Generated: {self.metrics.get('timestamp', 'N/A')}</span>
                <span>Duration: {summary.get('duration_seconds', 0):.1f}s</span>
            </div>
        </header>
        
        <section class="summary">
            {self._build_summary_section(summary)}
        </section>
        
        <section class="metrics">
            {self._build_connectivity_section()}
            {self._build_heartbeat_section()}
            {self._build_watchdog_section()}
            {self._build_escalation_section()}
            {self._build_alert_section()}
        </section>
        
        <footer>
            <p>Safe Passage Performance Testing Suite v1.0</p>
            <p>Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </footer>
    </div>
    
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>"""
    
    def _build_summary_section(self, summary: Dict[str, Any]) -> str:
        """Build summary cards."""
        total = summary.get('total_tests', 0)
        passed = summary.get('passed', 0)
        warnings = summary.get('warnings', 0)
        failed = summary.get('failed', 0)
        
        return f"""
        <div class="summary-cards">
            <div class="card">
                <div class="card-value">{total}</div>
                <div class="card-label">Total Tests</div>
            </div>
            <div class="card success">
                <div class="card-value">{passed}</div>
                <div class="card-label">Passed ✓</div>
            </div>
            <div class="card warning">
                <div class="card-value">{warnings}</div>
                <div class="card-label">Warnings ⚠</div>
            </div>
            <div class="card error">
                <div class="card-value">{failed}</div>
                <div class="card-label">Failed ✗</div>
            </div>
        </div>"""
    
    def _build_connectivity_section(self) -> str:
        """Build connectivity predictor metrics section."""
        metrics = self.metrics.get('metrics', {}).get('connectivity', {})
        if not metrics:
            return ""
        
        return f"""
        <div class="section">
            <h2>📡 Connectivity Predictor</h2>
            <div class="metrics-grid">
                {self._build_metric_card('Accuracy', metrics.get('accuracy', {}))}
                {self._build_metric_card('P99 Latency', metrics.get('latency_p99_ms', {}))}
                {self._build_metric_card('Confidence', metrics.get('confidence_correlation', {}))}
                {self._build_metric_card('Fallback Rate', metrics.get('fallback_frequency', {}))}
            </div>
        </div>"""
    
    def _build_heartbeat_section(self) -> str:
        """Build heartbeat load test metrics section."""
        metrics = self.metrics.get('metrics', {}).get('heartbeat_load', {})
        if not metrics:
            return ""
        
        return f"""
        <div class="section">
            <h2>💓 Heartbeat Ingestion</h2>
            <div class="metrics-grid">
                {self._build_metric_card('Throughput', metrics.get('throughput_per_sec', {}))}
                {self._build_metric_card('P95 Latency (100 concurrent)', metrics.get('latency_100_concurrent_p95_ms', {}))}
                {self._build_metric_card('Error Rate', metrics.get('error_rate', {}))}
            </div>
            <div class="chart-container">
                <canvas id="heartbeatLatencyChart"></canvas>
            </div>
        </div>"""
    
    def _build_watchdog_section(self) -> str:
        """Build watchdog scalability metrics section."""
        metrics = self.metrics.get('metrics', {}).get('watchdog', {})
        if not metrics:
            return ""
        
        return f"""
        <div class="section">
            <h2>⏰ Watchdog Scalability</h2>
            <div class="metrics-grid">
                {self._build_metric_card('1000 Trips Duration', metrics.get('duration_1000_trips_sec', {}))}
                {self._build_metric_card('Per-Trip P95', metrics.get('per_trip_p95_ms', {}))}
                {self._build_metric_card('Peak Memory', metrics.get('peak_memory_mb', {}))}
            </div>
        </div>"""
    
    def _build_escalation_section(self) -> str:
        """Build escalation workflow metrics section."""
        metrics = self.metrics.get('metrics', {}).get('escalation', {})
        if not metrics:
            return ""
        
        return f"""
        <div class="section">
            <h2>🚨 Emergency Escalation</h2>
            <div class="metrics-grid">
                {self._build_metric_card('Stage Transition Accuracy', metrics.get('stage_transition_accuracy', {}))}
                {self._build_metric_card('False Positive Rate', metrics.get('false_positive_rate', {}))}
                {self._build_metric_card('Rearm Enforcement', metrics.get('rearm_enforcement', {}))}
            </div>
        </div>"""
    
    def _build_alert_section(self) -> str:
        """Build alert delivery metrics section."""
        metrics = self.metrics.get('metrics', {}).get('alert_delivery', {})
        if not metrics:
            return ""
        
        return f"""
        <div class="section">
            <h2>📱 Alert Delivery</h2>
            <div class="metrics-grid">
                {self._build_metric_card('Delivery Success Rate', metrics.get('delivery_success_rate', {}))}
                {self._build_metric_card('P95 Delivery Latency', metrics.get('delivery_p95_sec', {}))}
            </div>
        </div>"""
    
    def _build_metric_card(self, name: str, metric_data: Dict[str, Any]) -> str:
        """Build individual metric card."""
        if not metric_data or not isinstance(metric_data, dict):
            return ""
        
        value = metric_data.get('value', 'N/A')
        passed = metric_data.get('passed')
        
        if passed is True:
            status_class = 'success'
            status_icon = '✓'
        elif passed is False:
            status_class = 'warning'
            status_icon = '⚠'
        else:
            status_class = ''
            status_icon = ''
        
        return f"""
        <div class="metric-card {status_class}">
            <div class="metric-name">{name}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-status">{status_icon}</div>
        </div>"""
    
    def _get_css(self) -> str:
        """Get CSS styles."""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; opacity: 0.9; margin-bottom: 20px; }
        .metadata { font-size: 0.9em; opacity: 0.8; }
        .metadata span { margin: 0 15px; }
        .summary { padding: 30px; background: #f8f9fa; }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .card-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .card.success .card-value { color: #28a745; }
        .card.warning .card-value { color: #ffc107; }
        .card.error .card-value { color: #dc3545; }
        .section {
            padding: 30px;
            border-bottom: 1px solid #e0e0e0;
        }
        .section h2 {
            margin-bottom: 20px;
            color: #333;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #ccc;
            position: relative;
        }
        .metric-card.success { border-left-color: #28a745; }
        .metric-card.warning { border-left-color: #ffc107; }
        .metric-name {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        .metric-status {
            position: absolute;
            top: 15px;
            right: 15px;
            font-size: 1.2em;
        }
        .chart-container {
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
        }
        footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }
        """
    
    def _get_javascript(self) -> str:
        """Get JavaScript for charts."""
        return """
        // Placeholder for Chart.js initialization
        // Charts will be populated with actual data in future phases
        console.log('Safe Passage Performance Report loaded');
        """


def generate_html_report(metrics_dict: Dict[str, Any], config: Any, 
                        output_path: Path) -> Path:
    """Convenience function to generate HTML report."""
    generator = HTMLGenerator(metrics_dict, config)
    return generator.generate(output_path)
