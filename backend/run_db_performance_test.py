#!/usr/bin/env python3
"""
Real Database Performance Test

Measures actual performance metrics using the live Supabase connection:
- INSERT latency (create users, trips, heartbeats)
- UPDATE latency (modify records)
- DELETE latency (cleanup)
- Watchdog cycle time with real database queries

This test uses REAL database I/O and will show production-representative metrics.

Usage:
    python run_db_performance_test.py
    python run_db_performance_test.py --num-trips 50
"""

import argparse
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask

from app.config import BaseConfig
from app.extensions import init_extensions
from app.models.heartbeats import insert_heartbeat, list_recent_heartbeats
from app.models.traveler_status import upsert_status
from app.models.trips import create_trip, delete_trip_by_id, get_trip_by_id, list_active_heartbeat_trips
from app.models.users import create_user, get_user_by_id
from app.services.heartbeat_monitor import run_watchdog_cycle


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class DatabasePerformanceTester:
    """Real database performance tester."""
    
    def __init__(self, num_trips: int = 10):
        self.num_trips = num_trips
        self.test_user_ids = []
        self.test_trip_ids = []
        self.trip_user_map = {}
        self.results = {}
        
    def print_header(self):
        """Print test header."""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}Real Database Performance Test{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
        print(f"Testing with: {Colors.YELLOW}{self.num_trips}{Colors.RESET} trips")
        print(f"Database: {Colors.YELLOW}{BaseConfig.SQLALCHEMY_DATABASE_URI.split('@')[1] if '@' in BaseConfig.SQLALCHEMY_DATABASE_URI else 'Local SQLite'}{Colors.RESET}")
        print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}[{title}]{Colors.RESET}")
        
    def print_metric(self, label: str, value: Any, unit: str = "", color: str = Colors.GREEN):
        """Print formatted metric."""
        print(f"  {label}: {color}{value}{unit}{Colors.RESET}")
        
    def cleanup(self):
        """Clean up test data."""
        self.print_section("Cleanup")
        deleted = 0
        failed = 0
        for trip_id in list(self.test_trip_ids):
            try:
                if self._delete_trip_records(trip_id):
                    deleted += 1
            except Exception:
                failed += 1

        if failed:
            print(f"  {Colors.YELLOW}⚠{Colors.RESET} Deleted {deleted} trips, failed to delete {failed} trips")
        else:
            print(f"  {Colors.GREEN}✓{Colors.RESET} Deleted {deleted} test trips")

        # Keep users to avoid accidental removal of shared references.
        print(f"  {Colors.YELLOW}ℹ{Colors.RESET} Kept {len(self.test_user_ids)} test users (manual cleanup required)")

    def _delete_trip_records(self, trip_id: str) -> bool:
        """Delete trip-scoped rows directly for robust benchmark cleanup."""
        from app.extensions import get_db_engine

        trip_tables = [
            "heartbeats",
            "alerts",
            "traveler_status",
            "monitoring_expectations",
        ]

        for table_name in trip_tables:
            try:
                with get_db_engine().begin() as connection:
                    connection.execute(text(f"DELETE FROM {table_name} WHERE trip_id = :trip_id"), {"trip_id": trip_id})
            except (ProgrammingError, OperationalError) as exc:
                # Ignore schema/table differences across Supabase environments.
                if "does not exist" in str(exc).lower() or "undefined_table" in str(exc).lower():
                    continue
                raise

        with get_db_engine().begin() as connection:
            result = connection.execute(text("DELETE FROM trips WHERE id = :trip_id"), {"trip_id": trip_id})
            return (result.rowcount or 0) > 0
    
    def test_insert_performance(self):
        """Test INSERT operations: users, trips, heartbeats."""
        self.print_section("INSERT Performance")
        
        # Test user creation
        user_times = []
        for i in range(min(5, self.num_trips)):  # Create 5 users max
            start = time.perf_counter()
            user = create_user({
                "full_name": f"Test User {i}",
                "phone_number": f"+1555010{i:04d}",
                "phone": f"+1555010{i:04d}"
            })
            elapsed = (time.perf_counter() - start) * 1000
            user_times.append(elapsed)
            self.test_user_ids.append(user['id'])
        
        avg_user_insert = sum(user_times) / len(user_times)
        self.results['user_insert_avg_ms'] = avg_user_insert
        self.print_metric("User INSERT (avg)", f"{avg_user_insert:.2f}", "ms")
        
        # Test trip creation
        trip_times = []
        for i in range(self.num_trips):
            user_id = self.test_user_ids[i % len(self.test_user_ids)]
            start = time.perf_counter()
            trip = create_trip({
                "user_id": user_id,
                "title": f"Performance Test Trip {i}",
                "destination": f"Test Destination {i}",
                "start_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=8)).isoformat(),
                "heartbeat_enabled": True
            })
            elapsed = (time.perf_counter() - start) * 1000
            trip_times.append(elapsed)
            self.test_trip_ids.append(trip['id'])
            self.trip_user_map[trip['id']] = user_id
        
        avg_trip_insert = sum(trip_times) / len(trip_times)
        self.results['trip_insert_avg_ms'] = avg_trip_insert
        self.print_metric("Trip INSERT (avg)", f"{avg_trip_insert:.2f}", "ms")
        
        # Test heartbeat insertion
        heartbeat_times = []
        for i in range(min(20, self.num_trips * 2)):  # Insert multiple heartbeats per trip
            trip_idx = i % len(self.test_trip_ids)
            trip_id = self.test_trip_ids[trip_idx]
            user_id = self.test_user_ids[trip_idx % len(self.test_user_ids)]
            start = time.perf_counter()
            insert_heartbeat({
                "id": str(uuid4()),
                "user_id": user_id,
                "trip_id": trip_id,
                "gps_lat": 37.7749 + (i * 0.001),
                "gps_lng": -122.4194 + (i * 0.001),
                "battery_percent": 95 - (i % 20),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "accuracy_meters": 10.0,
                "network_status": "4G",
                "offline_minutes": 0,
                "source": "mobile",
                "emergency_phone": None
            })
            elapsed = (time.perf_counter() - start) * 1000
            heartbeat_times.append(elapsed)
        
        avg_heartbeat_insert = sum(heartbeat_times) / len(heartbeat_times)
        self.results['heartbeat_insert_avg_ms'] = avg_heartbeat_insert
        self.print_metric("Heartbeat INSERT (avg)", f"{avg_heartbeat_insert:.2f}", "ms")
        
        # Calculate overall INSERT average
        all_inserts = user_times + trip_times + heartbeat_times
        overall_avg = sum(all_inserts) / len(all_inserts)
        self.results['overall_insert_avg_ms'] = overall_avg
        self.print_metric("Overall INSERT (avg)", f"{overall_avg:.2f}", "ms", Colors.CYAN)
        
    def test_update_performance(self):
        """Test UPDATE operations."""
        self.print_section("UPDATE Performance")
        
        update_times = []
        
        # Update traveler status for trips
        for trip_id in self.test_trip_ids[:min(10, len(self.test_trip_ids))]:
            user_id = self.trip_user_map.get(trip_id)
            if not user_id:
                continue
            start = time.perf_counter()
            upsert_status({
                "id": str(uuid4()),
                "user_id": user_id,
                "trip_id": trip_id,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "last_seen_lat": 37.7749,
                "last_seen_lng": -122.4194,
                "last_battery_percent": 88,
                "last_network_status": "4G",
                "location_risk": "moderate",
                "connectivity_risk": "low",
                "current_stage": "stage_1_initial_alert",
                "monitoring_state": "active",
                "last_stage_change_at": datetime.now(timezone.utc).isoformat(),
                "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
            })
            elapsed = (time.perf_counter() - start) * 1000
            update_times.append(elapsed)
        
        if not update_times:
            self.results['update_avg_ms'] = 0.0
            self.print_metric("Status UPDATE (avg)", "N/A", "")
            return

        avg_update = sum(update_times) / len(update_times)
        self.results['update_avg_ms'] = avg_update
        self.print_metric("Status UPDATE (avg)", f"{avg_update:.2f}", "ms")
        
    def test_query_performance(self):
        """Test SELECT query performance."""
        self.print_section("SELECT Query Performance")
        
        # Test single record retrieval
        start = time.perf_counter()
        user = get_user_by_id(self.test_user_ids[0])
        elapsed = (time.perf_counter() - start) * 1000
        self.results['select_user_by_id_ms'] = elapsed
        self.print_metric("User by ID", f"{elapsed:.2f}", "ms")
        
        # Test trip retrieval
        start = time.perf_counter()
        trip = get_trip_by_id(self.test_trip_ids[0])
        elapsed = (time.perf_counter() - start) * 1000
        self.results['select_trip_by_id_ms'] = elapsed
        self.print_metric("Trip by ID", f"{elapsed:.2f}", "ms")
        
        # Test heartbeat list query
        start = time.perf_counter()
        heartbeats = list_recent_heartbeats(self.test_user_ids[0], limit=10)
        elapsed = (time.perf_counter() - start) * 1000
        self.results['select_recent_heartbeats_ms'] = elapsed
        self.print_metric("Recent heartbeats (10)", f"{elapsed:.2f}", "ms")
        
        # Test active trips query (watchdog query)
        start = time.perf_counter()
        today_iso = datetime.now(timezone.utc).date().isoformat()
        active_trips = list_active_heartbeat_trips(today_iso)
        elapsed = (time.perf_counter() - start) * 1000
        self.results['select_active_trips_ms'] = elapsed
        self.print_metric(f"Active trips ({len(active_trips)})", f"{elapsed:.2f}", "ms")
        
    def test_watchdog_cycle(self):
        """Test full watchdog cycle with real database."""
        self.print_section("Watchdog Cycle Performance")
        
        # Create some statuses to evaluate
        for trip_id in self.test_trip_ids[:min(5, len(self.test_trip_ids))]:
            user_id = self.trip_user_map.get(trip_id)
            if not user_id:
                continue
            # Create a status that needs evaluation (last heartbeat 10 mins ago)
            upsert_status({
                "id": str(uuid4()),
                "user_id": user_id,
                "trip_id": trip_id,
                "last_seen_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
                "last_seen_lat": 37.7749,
                "last_seen_lng": -122.4194,
                "last_battery_percent": 82,
                "last_network_status": "offline",
                "location_risk": "moderate",
                "connectivity_risk": "high",
                "current_stage": "none",
                "monitoring_state": "active",
                "last_stage_change_at": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
                "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
            })
        
        # Run watchdog cycle
        start = time.perf_counter()
        try:
            results = run_watchdog_cycle()
            elapsed = (time.perf_counter() - start) * 1000
            
            self.results['watchdog_cycle_ms'] = elapsed
            self.results['watchdog_trips_evaluated'] = results.get('result_count', 0)
            self.results['watchdog_trips_escalated'] = results.get('alerts_created_count', 0)
            
            self.print_metric("Cycle duration", f"{elapsed:.2f}", "ms", Colors.CYAN)
            self.print_metric("Trips evaluated", results.get('result_count', 0), "")
            self.print_metric("Trips escalated", results.get('alerts_created_count', 0), "")
            
            if results.get('result_count', 0) > 0:
                per_trip = elapsed / results['result_count']
                self.results['watchdog_per_trip_ms'] = per_trip
                self.print_metric("Per-trip evaluation", f"{per_trip:.2f}", "ms")
                
        except Exception as e:
            print(f"  {Colors.RED}✗ Watchdog cycle failed: {e}{Colors.RESET}")
            traceback.print_exc()
    
    def test_delete_performance(self):
        """Test DELETE operations."""
        self.print_section("DELETE Performance")
        
        # Delete a few test trips to measure delete performance
        delete_times = []
        trips_to_delete = self.test_trip_ids[:min(3, len(self.test_trip_ids))]
        
        for trip_id in trips_to_delete:
            start = time.perf_counter()
            self._delete_trip_records(trip_id)
            elapsed = (time.perf_counter() - start) * 1000
            delete_times.append(elapsed)
        
        # Remove deleted trips from cleanup list
        for trip_id in trips_to_delete:
            self.test_trip_ids.remove(trip_id)
        
        if not delete_times:
            self.results['delete_avg_ms'] = 0.0
            self.print_metric("Trip DELETE (avg)", "N/A", "")
            return

        avg_delete = sum(delete_times) / len(delete_times)
        self.results['delete_avg_ms'] = avg_delete
        self.print_metric("Trip DELETE (avg)", f"{avg_delete:.2f}", "ms")
        
    def print_summary(self):
        """Print test summary."""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}Performance Summary{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
        
        print(f"{Colors.BOLD}Database Operations:{Colors.RESET}")
        self.print_metric("INSERT (avg)", f"{self.results.get('overall_insert_avg_ms', 0):.2f}", "ms", Colors.CYAN)
        self.print_metric("UPDATE (avg)", f"{self.results.get('update_avg_ms', 0):.2f}", "ms", Colors.CYAN)
        self.print_metric("DELETE (avg)", f"{self.results.get('delete_avg_ms', 0):.2f}", "ms", Colors.CYAN)
        
        print(f"\n{Colors.BOLD}Query Performance:{Colors.RESET}")
        self.print_metric("Single record lookup", f"{self.results.get('select_trip_by_id_ms', 0):.2f}", "ms", Colors.CYAN)
        self.print_metric("List query", f"{self.results.get('select_recent_heartbeats_ms', 0):.2f}", "ms", Colors.CYAN)
        self.print_metric("Complex join query", f"{self.results.get('select_active_trips_ms', 0):.2f}", "ms", Colors.CYAN)
        
        print(f"\n{Colors.BOLD}Heartbeat System:{Colors.RESET}")
        self.print_metric("Heartbeat ingestion", f"{self.results.get('heartbeat_insert_avg_ms', 0):.2f}", "ms", Colors.CYAN)
        
        if 'watchdog_cycle_ms' in self.results:
            self.print_metric("Watchdog cycle", f"{self.results.get('watchdog_cycle_ms', 0):.2f}", "ms", Colors.CYAN)
            if 'watchdog_per_trip_ms' in self.results:
                self.print_metric("Per-trip evaluation", f"{self.results.get('watchdog_per_trip_ms', 0):.2f}", "ms", Colors.CYAN)
        
        # Compare with mocked test results
        print(f"\n{Colors.BOLD}Comparison with Mocked Tests:{Colors.RESET}")
        print(f"  Mocked heartbeat insert:  {Colors.YELLOW}0.12ms{Colors.RESET}")
        heartbeat_ms = self.results.get('heartbeat_insert_avg_ms', 0)
        multiplier = (heartbeat_ms / 0.12) if heartbeat_ms else 0
        print(f"  Real heartbeat insert:    {Colors.CYAN}{heartbeat_ms:.2f}ms{Colors.RESET} ({Colors.GREEN}{multiplier:.1f}x slower{Colors.RESET})")
        
        if 'watchdog_cycle_ms' in self.results and self.results.get('watchdog_trips_evaluated', 0) > 0:
            # Mocked test showed 2ms for 1000 trips
            trips_eval = self.results.get('watchdog_trips_evaluated', 1)
            normalized_real = (self.results.get('watchdog_cycle_ms', 0) / trips_eval) * 1000
            print(f"  Mocked watchdog (1000 trips): {Colors.YELLOW}2ms{Colors.RESET}")
            print(f"  Real watchdog (1000 trips est): {Colors.CYAN}{normalized_real:.0f}ms{Colors.RESET} ({Colors.GREEN}{normalized_real / 2:.0f}x slower{Colors.RESET})")
        
        print()
    
    def run(self):
        """Run all tests."""
        try:
            self.print_header()
            
            self.test_insert_performance()
            self.test_update_performance()
            self.test_query_performance()
            self.test_watchdog_cycle()
            self.test_delete_performance()
            
            self.print_summary()
            
            return 0
            
        except Exception as e:
            print(f"\n{Colors.RED}✗ Test failed: {e}{Colors.RESET}")
            traceback.print_exc()
            return 1
            
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Real Database Performance Test',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--num-trips', type=int, default=10,
                       help='Number of test trips to create (default: 10)')
    
    args = parser.parse_args()
    
    # Initialize Flask app and extensions
    app = Flask(__name__)
    app.config.from_object(BaseConfig)
    
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')
    db_target = db_uri.split('@')[-1] if '@' in db_uri else db_uri
    print(f"Database target: {db_target}")
    
    with app.app_context():
        try:
            init_extensions(app)
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to initialize extensions: {e}{Colors.RESET}")
            traceback.print_exc()
            return 1
        
        # Import the engine after init
        from app.extensions import sqlalchemy_engine
        
        if not sqlalchemy_engine:
            print(f"{Colors.RED}✗ SQLAlchemy engine not initialized. Check database configuration.{Colors.RESET}")
            print(f"{Colors.YELLOW}Database URI in config: {app.config.get('SQLALCHEMY_DATABASE_URI', 'MISSING')}{Colors.RESET}")
            return 1
        
        try:
            # Test the connection
            with sqlalchemy_engine.connect() as conn:
                print(f"{Colors.GREEN}✓ Connected to database{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to connect to database: {e}{Colors.RESET}")
            print(f"{Colors.YELLOW}Check your database credentials and network connection{Colors.RESET}")
            return 1
        
        tester = DatabasePerformanceTester(num_trips=args.num_trips)
        return tester.run()


if __name__ == '__main__':
    sys.exit(main())
