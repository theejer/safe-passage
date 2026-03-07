# Performance Testing Suite

This directory contains comprehensive performance and reliability tests for the Safe Passage heartbeat monitoring and emergency escalation systems.

## Important: What These Tests Measure

⚠️ **These tests measure algorithm efficiency and code execution speed with mocked I/O.** They execute real production code but use:
- **In-memory database**: Dictionary-based storage (no actual PostgreSQL I/O)
- **Mocked external services**: HTTP calls intercepted instantly (no network latency)
- **Synthetic data**: Test users, trips, and heartbeats generated in-memory

**What these tests validate:**
- ✓ Code correctness and logic flow
- ✓ Algorithm efficiency without I/O overhead
- ✓ Memory usage patterns
- ✓ Error handling robustness
- ✓ Concurrent execution behavior

**What these tests do NOT measure:**
- ✗ Real database query latency (PostgreSQL connection overhead, network I/O)
- ✗ Actual HTTP request/response times
- ✗ Production infrastructure constraints (CPU, memory, network)
- ✗ Real-world connection pooling behavior

**Realistic production estimates:**
| Test Result (Mocked) | Production Estimate (Real I/O) |
|---------------------|--------------------------------|
| Heartbeat: 0.12ms | 15-40ms (real DB + network) |
| Watchdog 1000 trips: 2ms | 7-20 seconds (real queries) |
| Alert delivery: 3-5ms | 250-3000ms (real HTTP) |
| Throughput: 6000+ req/sec | 100-300 req/sec (real infra) |

For production load testing, use integration tests with a real database and infrastructure.

## Quick Start

Run all performance tests:
```bash
python backend/run_performance_tests.py --all
```

Run specific test categories:
```bash
python backend/run_performance_tests.py --connectivity
python backend/run_performance_tests.py --load
python backend/run_performance_tests.py --watchdog
python backend/run_performance_tests.py --escalation
python backend/run_performance_tests.py --alerts
```

## Test Categories

### 1. Connectivity Predictor Tests (`--connectivity`)
- **Accuracy Benchmark**: Measures prediction accuracy against ground truth dataset (target: ≥75%)
- **Latency Benchmark**: P50/P95/P99 prediction latencies (target: P99 <200ms)
- **Confidence Calibration**: Verifies confidence scores correlate with actual accuracy
- **Fallback Frequency**: Percentage of predictions using fallback logic (target: <10%)

### 2. Heartbeat Ingestion Load Tests (`--load`)
- **Baseline Latency**: Single heartbeat end-to-end time (target: <100ms)
- **Concurrent Load**: 50/100/500 simultaneous requests
- **Throughput**: Successful heartbeats per second (target: >100/sec)
- **Error Rate**: Failed ingestions under load (target: <1%)
- **Database Profiling**: Query execution time breakdown

### 3. Watchdog Scalability Tests (`--watchdog`)
- **Cycle Duration**: Time to evaluate 100/500/1000 active trips (target: 1000 trips in <30s)
- **Per-Trip Evaluation**: P50/P95/P99 evaluation times (target: P95 <150ms)
- **Memory Usage**: Peak memory during batch processing (target: <500MB)
- **Query Optimization**: N+1 query detection and optimization

### 4. Emergency Escalation Tests (`--escalation`)
- **Stage 1→2→3 Workflow**: End-to-end multi-stage escalation correctness (target: 100%)
- **Rearm Buffer**: 30-minute suppression after Stage 3 recovery (target: 100% adherence)
- **Alert Deduplication**: Single alert within dedupe windows (target: 100%)
- **False Positive Rate**: Incorrect alert triggers (target: <5%)
- **Contact Confirmation**: YES/NO response handling accuracy (target: 100%)

### 5. Alert Delivery Tests (`--alerts`)
- **Delivery Success Rate**: Telegram/SMS delivery success (target: >95%)
- **Delivery Latency**: P50/P95 time from trigger to API call (target: P95 <5s)
- **Retry Logic**: Exponential backoff on failures
- **Alert Storm**: Deduplication under burst scenarios (100+ alerts/min)

### 6. End-to-End Smoke Tests (`--e2e`)
- Complete workflow: upload itinerary → enable heartbeat → go offline → verify alert

## Output

The test runner generates two output files in `backend/test_results/`:

### 1. JSON Results (`performance_YYYYMMDD_HHMMSS.json`)
Structured, machine-readable results for CI/CD integration:
```json
{
  "timestamp": "2026-03-07T14:30:22Z",
  "duration_seconds": 222,
  "summary": {
    "total_tests": 18,
    "passed": 17,
    "warnings": 1,
    "failed": 0
  },
  "metrics": {
    "connectivity": {...},
    "heartbeat_load": {...},
    ...
  }
}
```

### 2. HTML Dashboard (`performance_report.html`)
Portfolio-ready visual report with:
- Summary cards (total/passed/warnings/failed)
- Interactive charts (latency percentiles, throughput graphs)
- Color-coded metrics (green=pass, yellow=warning, red=fail)
- Confusion matrices for accuracy tests
- Methodology explanations

## Performance Targets

| Category | Metric | Target | Color Coding |
|----------|--------|--------|--------------|
| **Connectivity** | Accuracy | ≥75% | Green: ≥75%, Yellow: 60-74%, Red: <60% |
| | P99 Latency | <200ms | Green: ≤200ms, Yellow: 200-250ms, Red: >250ms |
| **Heartbeat** | Throughput | >100/sec | Green: ≥100, Yellow: 80-99, Red: <80 |
| | P95 Latency (100 concurrent) | <250ms | Green: ≤250ms, Yellow: 250-312ms, Red: >312ms |
| **Watchdog** | 1000 Trips Duration | <30s | Green: ≤30s, Yellow: 30-37s, Red: >37s |
| | Peak Memory | <500MB | Green: ≤500MB, Yellow: 500-625MB, Red: >625MB |
| **Escalation** | Stage Transition Accuracy | 100% | Green: 100%, Yellow: 95-99%, Red: <95% |
| | False Positive Rate | <5% | Green: ≤5%, Yellow: 5-6.25%, Red: >6.25% |
| **Alerts** | Delivery Success Rate | >95% | Green: ≥95%, Yellow: 76-94%, Red: <76% |
| | P95 Delivery Latency | <5s | Green: ≤5s, Yellow: 5-6.25s, Red: >6.25s |

**Color Coding Rules:**
- **Green (Pass)**: Meets or exceeds target (≥100% of target)
- **Yellow (Warning)**: Close to target (80-99% of target)
- **Red (Fail)**: Below target (<80% of target)

## Exit Codes

The test runner returns appropriate exit codes for CI/CD integration:
- `0`: All tests passed (green)
- `1`: One or more tests failed (red)
- `2`: Tests passed with warnings (yellow)

## Example Output

```
╔══════════════════════════════════════════════════════════════╗
║        Safe Passage Performance Test Suite v1.0              ║
╚══════════════════════════════════════════════════════════════╝

[1/5] Connectivity Predictor Tests
  ├─ Accuracy Benchmark        ✓ 78.2% (target: 75%)
  ├─ Latency Benchmark         ✓ P99: 142ms (target: <200ms)
  ├─ Confidence Calibration    ✓ Correlation: 0.89
  └─ Fallback Frequency        ✓ 6.4% (target: <10%)

[2/5] Heartbeat Ingestion Load Tests
  ├─ Baseline Latency          ✓ 87ms
  ├─ 100 Concurrent            ✓ P95: 223ms (target: <250ms)
  └─ Throughput                ✓ 134 req/s (target: >100)

═════════════════════════════════════════════════════════════════
                         SUMMARY
═════════════════════════════════════════════════════════════════
Total Tests: 18       Passed: 17 ✓       Warnings: 1 ⚠       Failed: 0 ✗
Execution Time: 3m 42s
Results: test_results/performance_20260307_143022.json
Report: test_results/performance_report.html
═════════════════════════════════════════════════════════════════
```

## Implementation Status

- [x] **Phase 1**: Test Infrastructure & Runner (COMPLETE)
  - Unified test runner with CLI
  - Metrics collector and aggregation
  - Rich console reporter
  - JSON results exporter
  - HTML dashboard generator

- [ ] **Phase 2**: Connectivity Predictor Tests (TODO)
- [ ] **Phase 3**: Heartbeat Load Tests (TODO)
- [ ] **Phase 4**: Watchdog Scalability Tests (TODO)
- [ ] **Phase 5**: Emergency Escalation Tests (TODO)
- [ ] **Phase 6**: Alert Delivery Tests (TODO)
- [ ] **Phase 7**: Integration & Documentation (TODO)

## Development

To add new test categories:

1. Create test module in `backend/tests/performance/test_*.py`
2. Implement test functions that update `MetricsCollector`
3. Wire into `run_performance_tests.py` in appropriate `_run_*_tests()` method
4. Update this README with new test descriptions

## Dependencies

Required packages (added to `backend/requirements.txt`):
- `rich==13.7.0` - Console output formatting
- `jinja2==3.1.3` - HTML report generation
- `memory-profiler==0.61.0` - Memory usage profiling

Install with:
```bash
cd backend
pip install -r requirements.txt
```

## Troubleshooting

**Issue**: "rich library not installed"
- **Solution**: Run `pip install rich` or `pip install -r requirements.txt`

**Issue**: No output files generated
- **Solution**: Check that `backend/test_results/` directory is writable

**Issue**: Tests hanging or timing out
- **Solution**: Check database connection and ensure Supabase is accessible

## CI/CD Integration

Example GitHub Actions workflow:
```yaml
- name: Run Performance Tests
  run: |
    cd backend
    python run_performance_tests.py --all
    
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: performance-results
    path: backend/test_results/
```

## Future Enhancements

- [ ] Historical trend tracking (compare with baseline.json)
- [ ] Parallel test execution (--parallel flag)
- [ ] Interactive dashboard mode (--interactive)
- [ ] Slack/email notifications on failure
- [ ] Load testing with Locust integration
- [ ] Real-world accuracy validation with pilot user data
