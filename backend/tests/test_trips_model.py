from datetime import date, timedelta

from sqlalchemy import create_engine

from app.models import trips as trips_model


def test_list_active_heartbeat_trips_includes_unresolved_after_end_date(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    today = date.today()

    with engine.begin() as connection:
        connection.exec_driver_sql(
        """
        CREATE TABLE trips (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            mode TEXT,
            start_date DATE,
            end_date DATE,
            source TEXT,
            heartbeat_enabled BOOLEAN DEFAULT FALSE,
            trip_planned BOOLEAN DEFAULT TRUE,
            created_at TEXT,
            updated_at TEXT
        )
        """
        )
        connection.exec_driver_sql(
        """
        CREATE TABLE traveler_status (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            trip_id TEXT,
            monitoring_state TEXT,
            created_at TEXT
        )
        """
        )

        connection.exec_driver_sql(
        """
        INSERT INTO trips (id, user_id, mode, start_date, end_date, source, heartbeat_enabled, trip_planned)
        VALUES (?, ?, 'bus', ?, ?, 'manual', 1, 1)
        """,
            (
                "ended-unresolved",
                "u1",
                (today - timedelta(days=5)).isoformat(),
                (today - timedelta(days=1)).isoformat(),
            ),
        )
        connection.exec_driver_sql(
        """
        INSERT INTO traveler_status (id, user_id, trip_id, monitoring_state, created_at)
        VALUES ('s1', 'u1', 'ended-unresolved', 'active', datetime('now'))
        """
        )

        connection.exec_driver_sql(
        """
        INSERT INTO trips (id, user_id, mode, start_date, end_date, source, heartbeat_enabled, trip_planned)
        VALUES (?, ?, 'bus', ?, ?, 'manual', 1, 1)
        """,
            (
                "ended-resolved",
                "u2",
                (today - timedelta(days=5)).isoformat(),
                (today - timedelta(days=1)).isoformat(),
            ),
        )
        connection.exec_driver_sql(
        """
        INSERT INTO traveler_status (id, user_id, trip_id, monitoring_state, created_at)
        VALUES ('s2', 'u2', 'ended-resolved', 'resolved', datetime('now'))
        """
        )

    monkeypatch.setattr(trips_model, "get_db_engine", lambda: engine)
    monkeypatch.setattr(trips_model, "_ensure_trips_table_for_sqlite", lambda: None)

    active = trips_model.list_active_heartbeat_trips(today.isoformat())
    active_ids = {trip["id"] for trip in active}

    assert "ended-unresolved" in active_ids
    assert "ended-resolved" not in active_ids
