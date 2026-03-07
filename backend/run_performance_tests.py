#!/usr/bin/env python3
"""
Safe Passage Performance Test Suite Runner

Measures algorithm efficiency and code execution speed for heartbeat monitoring
and emergency escalation systems.

WHAT THIS MEASURES:
  ✓ Code correctness and logic flow
  ✓ Algorithm efficiency (without I/O overhead)
  ✓ Memory usage patterns
  ✓ Error handling robustness
  ✓ Concurrent execution behavior

WHAT THIS DOES NOT MEASURE:
  ✗ Real database query latency (uses in-memory mocks)
  ✗ Actual HTTP request/response times (mocked instantly)
  ✗ Production infrastructure constraints
  ✗ Real-world connection pooling and network I/O

IMPORTANT: These tests use synthetic data and mocked I/O to validate
code quality. Production performance will be 10-100x slower due to
real database queries, network calls, and infrastructure overhead.

For realistic production estimates, see backend/README.md.

Usage:
    python run_performance_tests.py --all
    python run_performance_tests.py --connectivity --load
    python run_performance_tests.py --help
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.performance.config import PerformanceConfig
from tests.performance.metrics_collector import MetricsCollector
from tests.performance.console_reporter import ConsoleReporter
from tests.performance.html_generator import generate_html_report
from tests.performance.demo_tests import (
    run_demo_connectivity_tests,
    run_demo_load_tests,
    run_demo_watchdog_tests,
    run_demo_escalation_tests,
    run_demo_alert_tests
)


class PerformanceTestRunner:
    """
    Main test runner orchestrator.
    
    Executes performance tests that measure code execution efficiency
    with mocked I/O. Results validate algorithm correctness and memory
    usage, but do not represent production performance with real database
    and network operations.
    """
    
    def __init__(self, args):
        self.args = args
        self.config = PerformanceConfig()
        self.metrics = MetricsCollector()
        self.reporter = ConsoleReporter(use_rich=not args.no_color)
        self.test_results_dir = Path(__file__).parent / 'test_results'
        
    def run(self) -> int:
        """Execute selected tests and generate reports."""
        self.reporter.print_header()
        
        # Determine which test categories to run
        categories = self._get_test_categories()
        
        if not categories:
            print("Error: No test categories selected. Use --all or specify categories.")
            print("Run with --help to see available options.")
            return 1
        
        # Run tests
        category_num = 0
        total_categories = len(categories)
        
        for category_name, test_func in categories:
            category_num += 1
            self.reporter.start_category(category_name, category_num, total_categories)
            
            try:
                test_func()
            except Exception as e:
                self.metrics.add_error(category_name, str(e))
                self.reporter.print_error(category_name, str(e))
        
        # Generate reports
        self.reporter.print_progress("Generating reports...")
        
        json_path = self.metrics.save_json(self.test_results_dir)
        html_path = self.test_results_dir / 'performance_report.html'
        generate_html_report(self.metrics.to_dict(), self.config, html_path)
        
        # Print summary
        summary = self.metrics.get_summary()
        self.reporter.print_summary(summary, str(json_path), str(html_path))
        
        # Return exit code
        if summary['failed'] > 0:
            return 1  # Red failures
        elif summary['warnings'] > 0:
            return 2  # Yellow warnings
        else:
            return 0  # All pass
    
    def _get_test_categories(self):
        """Determine which test categories to run based on args."""
        categories = []
        
        if self.args.all or self.args.connectivity:
            categories.append(("Connectivity Predictor Tests", self._run_connectivity_tests))
        
        if self.args.all or self.args.load:
            categories.append(("Heartbeat Ingestion Load Tests", self._run_load_tests))
        
        if self.args.all or self.args.watchdog:
            categories.append(("Watchdog Scalability Tests", self._run_watchdog_tests))
        
        if self.args.all or self.args.escalation:
            categories.append(("Emergency Escalation Tests", self._run_escalation_tests))
        
        if self.args.all or self.args.alerts:
            categories.append(("Alert Delivery Tests", self._run_alert_tests))
        
        if self.args.all or self.args.e2e:
            categories.append(("End-to-End Smoke Tests", self._run_e2e_tests))
        
        return categories
    
    def _run_connectivity_tests(self):
        """Run connectivity predictor tests (Phase 2)."""
        # Using demo tests for now - will be replaced with real implementation in Phase 2
        run_demo_connectivity_tests(self.metrics, self.reporter)
    
    def _run_load_tests(self):
        """Run heartbeat load tests (Phase 3)."""
        # Using demo tests for now - will be replaced with real implementation in Phase 3
        run_demo_load_tests(self.metrics, self.reporter)
    
    def _run_watchdog_tests(self):
        """Run watchdog scalability tests (Phase 4)."""
        # Using demo tests for now - will be replaced with real implementation in Phase 4
        run_demo_watchdog_tests(self.metrics, self.reporter)
    
    def _run_escalation_tests(self):
        """Run escalation workflow tests (Phase 5)."""
        # Using demo tests for now - will be replaced with real implementation in Phase 5
        run_demo_escalation_tests(self.metrics, self.reporter)
    
    def _run_alert_tests(self):
        """Run alert delivery tests (Phase 6)."""
        # Using demo tests for now - will be replaced with real implementation in Phase 6
        run_demo_alert_tests(self.metrics, self.reporter)
    
    def _run_e2e_tests(self):
        """Run end-to-end smoke tests (Phase 7)."""
        self.reporter.print_progress("End-to-end tests not yet implemented")
        self.metrics.add_metric('e2e', 'status', 'pending')
        # TODO: Import and run test_e2e_smoke


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description='Safe Passage Performance Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_performance_tests.py --all
  python run_performance_tests.py --connectivity --load
  python run_performance_tests.py --watchdog --no-color
  
Test Categories:
  --connectivity    Connectivity predictor accuracy and latency
  --load           Heartbeat ingestion load and throughput
  --watchdog       Watchdog cycle scalability 
  --escalation     Emergency escalation workflow correctness
  --alerts         Alert delivery reliability
  --e2e            End-to-end smoke tests
  --all            Run all test categories (default if none specified)

What These Tests Measure:
  These tests execute real production code with synthetic data and
  mocked I/O (in-memory database, intercepted HTTP calls). They
  validate:
  
  ✓ Code correctness and algorithm logic
  ✓ Memory usage patterns
  ✓ Error handling robustness
  ✓ Concurrent execution behavior
  
  ⚠️  IMPORTANT: Results do NOT represent production performance.
      Real database queries and network I/O will be 10-100x slower.
      See backend/README.md for realistic production estimates.

Output:
  JSON results saved to: backend/test_results/performance_YYYYMMDD_HHMMSS.json
  HTML report saved to: backend/test_results/performance_report.html
  
Exit Codes:
  0 = All tests passed
  1 = One or more tests failed (red)
  2 = Tests passed with warnings (yellow)
        """
    )
    
    # Test category selection
    parser.add_argument('--all', action='store_true',
                       help='Run all test categories')
    parser.add_argument('--connectivity', action='store_true',
                       help='Run connectivity predictor tests')
    parser.add_argument('--load', action='store_true',
                       help='Run heartbeat ingestion load tests')
    parser.add_argument('--watchdog', action='store_true',
                       help='Run watchdog scalability tests')
    parser.add_argument('--escalation', action='store_true',
                       help='Run emergency escalation tests')
    parser.add_argument('--alerts', action='store_true',
                       help='Run alert delivery tests')
    parser.add_argument('--e2e', action='store_true',
                       help='Run end-to-end smoke tests')
    
    # Output options
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored console output')
    parser.add_argument('--output-dir', type=str,
                       help='Custom output directory for results')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # If no categories specified, default to --all
    if not any([args.all, args.connectivity, args.load, args.watchdog,
                args.escalation, args.alerts, args.e2e]):
        args.all = True
    
    try:
        runner = PerformanceTestRunner(args)
        exit_code = runner.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
