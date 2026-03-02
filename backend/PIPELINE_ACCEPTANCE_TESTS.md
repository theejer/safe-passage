# Acceptance Test Plan

## Goal
Validate correctness, stability, and score behavior after integration.

## Endpoint Under Test
- `POST /itinerary/analyze-pipeline`

## Test 1: Empty Input
- Input: empty itinerary
- Expected:
  - `status == "failed"`
  - `stage == "input"`

## Test 2: Typical Safe Japan Trip
- Input: city tourism + train transfers
- Expected:
  - `status == "ok"`
  - `final_report.SCORE.value` in a healthy range (not near zero)
  - `judge.before >= judge.after`

## Test 3: High-Risk Scenario
- Input: itinerary entering active conflict/unrest region
- Expected:
  - at least one `High` risk
  - score materially lower than safe test

## Test 4: Duplicate Risk Noise
- Input: analyzer output with repetitive low-risk items (simulate or inspect raw)
- Expected:
  - judged output removes some noise
  - score reflects reduced low-value clutter

## Test 5: Cross-Run Isolation
- Run two distinct itineraries back-to-back
- Expected:
  - second result does not include first itinerary entities
  - request IDs differ (if surfaced in logs)

## Test 6: Judge Skip Path
- Input: very small/clean risk set
- Expected:
  - `judge.applied == false`
  - `judge.reason == "skipped_by_policy"`

## Test 7: Throughput/Latency Smoke
- Execute 5 requests serially
- Expected:
  - no crashes
  - stable latency trend after first request (client reuse benefit)

## Pass Criteria
- All 7 tests satisfy expected outcomes.
- No schema-breaking changes in response keys used by clients.
