"""Test helpers for performance testing with synthetic data and mocked database."""

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from uuid import uuid4


class MockConnection:
    """Mock database connection for performance testing."""
    
    def __init__(self, db: Dict[str, List[Dict]]):
        self._db = db
        self._results = []
    
    def execute(self, query, params: Dict = None):
        """Mock execute that returns synthetic results."""
        sql = str(query)
        params = params or {}
        
        # Mock heartbeat inserts
        if "INSERT INTO heartbeats" in sql:
            row = dict(params)
            row['id'] = str(uuid4())
            self._db['heartbeats'].append(row)
            self._results = [row]
            return self
        
        # Mock traveler_status queries
        if "SELECT * FROM traveler_status" in sql:
            trip_id = params.get('trip_id')
            results = [s for s in self._db['traveler_status'] if s.get('trip_id') == trip_id]
            self._results = results
            return self
        
        # Mock traveler_status upserts
        if "INSERT INTO traveler_status" in sql or "ON CONFLICT" in sql:
            row = dict(params)
            # Update or insert
            existing_idx = None
            for idx, status in enumerate(self._db['traveler_status']):
                if status.get('trip_id') == row.get('trip_id'):
                    existing_idx = idx
                    break
            
            if existing_idx is not None:
                self._db['traveler_status'][existing_idx].update(row)
                self._results = [self._db['traveler_status'][existing_idx]]
            else:
                row['id'] = row.get('id') or str(uuid4())
                self._db['traveler_status'].append(row)
                self._results = [row]
            return self
        
        # Mock trip queries
        if "SELECT" in sql and "FROM trips" in sql:
            if "WHERE id = " in sql or ":id" in sql or ":trip_id" in sql:
                trip_id = params.get('id') or params.get('trip_id')
                results = [t for t in self._db['trips'] if t.get('id') == trip_id]
            else:
                results = self._db['trips']
            self._results = results
            return self
        
        # Mock user queries
        if "SELECT" in sql and "FROM users" in sql:
            user_id = params.get('id') or params.get('user_id')
            results = [u for u in self._db['users'] if u.get('id') == user_id]
            self._results = results
            return self
        
        # Mock alert queries
        if "SELECT" in sql and "FROM alert_events" in sql:
            self._results = []
            return self
        
        # Mock monitoring expectations
        if "FROM monitoring_expectations" in sql:
            trip_id = params.get('trip_id')
            results = [e for e in self._db.get('monitoring_expectations', []) 
                      if e.get('trip_id') == trip_id]
            self._results = results[:1]  # Latest one
            return self
        
        # Mock insert/upsert monitoring expectations
        if "INSERT INTO monitoring_expectations" in sql:
            row = dict(params)
            row['id'] = str(uuid4())
            if 'monitoring_expectations' not in self._db:
                self._db['monitoring_expectations'] = []
            self._db['monitoring_expectations'].append(row)
            self._results = [row]
            return self
        
        self._results = []
        return self
    
    def mappings(self):
        """Return self for chaining."""
        return self
    
    def first(self):
        """Return first result."""
        return self._results[0] if self._results else None
    
    def all(self):
        """Return all results."""
        return self._results


class MockEngineContext:
    """Mock database engine context manager."""
    
    def __init__(self, db: Dict[str, List[Dict]]):
        self._db = db
    
    def __enter__(self):
        return MockConnection(self._db)
    
    def __exit__(self, exc_type, exc, tb):
        return False


class MockEngine:
    """Mock database engine for performance testing."""
    
    def __init__(self, db: Dict[str, List[Dict]]):
        self._db = db
    
    def begin(self):
        return MockEngineContext(self._db)


def create_mock_database() -> Dict[str, List[Dict]]:
    """Create in-memory mock database with empty tables."""
    return {
        'users': [],
        'trips': [],
        'heartbeats': [],
        'traveler_status': [],
        'alert_events': [],
        'monitoring_expectations': [],
        'itineraries': [],
        'itinerary_risks': [],
        'emergency_contacts': []
    }


def generate_synthetic_user(user_index: int = 0) -> Dict[str, Any]:
    """Generate synthetic user for testing."""
    user_id = f"perf_user_{user_index:04d}"
    return {
        'id': user_id,
        'full_name': f'Test User {user_index}',
        'email': f'user{user_index}@test.com',
        'phone': f'+9191{user_index:08d}',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'emergency_contact': {
            'name': f'Emergency Contact {user_index}',
            'phone': f'+9192{user_index:08d}',
            'telegram_chat_id': None,
            'telegram_bot_active': False
        }
    }


def generate_synthetic_trip(user_id: str, trip_index: int = 0, 
                           active: bool = True) -> Dict[str, Any]:
    """Generate synthetic trip for testing."""
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=2)).date().isoformat()
    end_date = (now + timedelta(days=5)).date().isoformat()
    
    trip_id = f"perf_trip_{trip_index:04d}"
    return {
        'id': trip_id,
        'user_id': user_id,
        'title': f'Test Trip {trip_index}',
        'trip_planned': True,
        'start_date': start_date,
        'end_date': end_date,
        'destination_country': 'IN',
        'heartbeat_enabled': active,
        'created_at': now.isoformat(),
        'updated_at': now.isoformat()
    }


def generate_synthetic_heartbeat(user_id: str, trip_id: str,
                                timestamp_offset_minutes: int = 0,
                                network_status: str = 'online') -> Dict[str, Any]:
    """Generate synthetic heartbeat payload."""
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=timestamp_offset_minutes)
    
    # Bihar coordinates (random within region)
    lat = 25.0 + random.uniform(-0.5, 0.5)
    lng = 85.0 + random.uniform(-0.5, 0.5)
    
    return {
        'user_id': user_id,
        'trip_id': trip_id,
        'timestamp': timestamp.isoformat(),
        'gps_lat': lat,
        'gps_lng': lng,
        'accuracy_meters': random.uniform(10, 50),
        'battery_percent': random.randint(20, 100),
        'network_status': network_status,
        'offline_minutes': 0 if network_status == 'online' else random.randint(5, 30),
        'source': 'mobile',
        'emergency_phone': None
    }


def generate_synthetic_status(user_id: str, trip_id: str,
                             stage: str = 'none',
                             last_seen_minutes_ago: int = 120) -> Dict[str, Any]:
    """Generate synthetic traveler status."""
    now = datetime.now(timezone.utc)
    last_seen = now - timedelta(minutes=last_seen_minutes_ago)
    
    lat = 25.0 + random.uniform(-0.5, 0.5)
    lng = 85.0 + random.uniform(-0.5, 0.5)
    
    return {
        'id': str(uuid4()),
        'user_id': user_id,
        'trip_id': trip_id,
        'last_seen_at': last_seen.isoformat(),
        'last_seen_lat': lat,
        'last_seen_lng': lng,
        'last_battery_percent': random.randint(20, 100),
        'last_network_status': 'offline',
        'location_risk': 'moderate',
        'connectivity_risk': 'high',
        'monitoring_state': 'active' if stage == 'none' else 'alerted',
        'current_stage': stage,
        'last_stage_change_at': last_seen.isoformat(),
        'last_evaluated_at': (now - timedelta(minutes=5)).isoformat()
    }


def populate_test_database(db: Dict[str, List[Dict]], num_trips: int = 100) -> None:
    """Populate mock database with synthetic test data."""
    now = datetime.now(timezone.utc)
    
    for i in range(num_trips):
        # Create user
        user = generate_synthetic_user(i)
        db['users'].append(user)
        
        # Create active trip
        trip = generate_synthetic_trip(user['id'], i, active=True)
        db['trips'].append(trip)
        
        # Create traveler status (some with delays)
        if random.random() < 0.8:  # 80% have status
            # Random offline duration between 30-180 minutes
            offline_minutes = random.randint(30, 180)
            stage = 'none'
            
            # 10% should be in stage_1
            if random.random() < 0.1:
                stage = 'stage_1_initial_alert'
                offline_minutes = random.randint(90, 150)
            
            status = generate_synthetic_status(
                user['id'], 
                trip['id'],
                stage=stage,
                last_seen_minutes_ago=offline_minutes
            )
            db['traveler_status'].append(status)
            
            # Add some historical heartbeats
            for j in range(random.randint(5, 20)):
                heartbeat = generate_synthetic_heartbeat(
                    user['id'],
                    trip['id'],
                    timestamp_offset_minutes=offline_minutes + j * 10,
                    network_status='online'
                )
                db['heartbeats'].append(heartbeat)
