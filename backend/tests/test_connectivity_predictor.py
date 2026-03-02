"""Tests for standalone deterministic connectivity predictor service."""

from pathlib import Path

from app.services import connectivity_predictor


CSV_HEADER = (
    "Timestamp,Locality,Latitude,Longitude,Signal Strength (dBm),Signal Quality (%),"
    "Data Throughput (Mbps),Latency (ms),Network Type\n"
)


def _clear_predictor_caches() -> None:
    connectivity_predictor._load_signal_records.cache_clear()
    connectivity_predictor._dataset_stats.cache_clear()


def _write_dataset(file_path: Path, rows: list[str]) -> None:
    file_path.write_text(CSV_HEADER + "".join(rows), encoding="utf-8")


def test_predictor_is_deterministic(monkeypatch, tmp_path):
    dataset_path = tmp_path / "signal_metrics.csv"
    _write_dataset(
        dataset_path,
        [
            "2023-05-05 12:50:40.000000,Anisabad,25.60,85.13,-84.0,0.0,8.0,80.0,4G\n",
            "2023-05-05 12:53:47.210173,Fraser Road,25.61,85.14,-88.0,0.0,6.0,90.0,4G\n",
            "2023-05-05 12:56:54.420346,Danapur,25.62,85.15,-95.0,0.0,35.0,35.0,5G\n",
            "2023-05-05 13:00:01.630519,Boring Road,25.58,85.12,-92.0,0.0,2.0,160.0,LTE\n",
            "2023-05-05 13:03:08.840692,Gandhi Maidan,25.57,85.11,-86.0,0.0,12.0,60.0,4G\n",
            "2023-05-05 13:06:16.050865,Kankarbagh,25.59,85.10,-90.0,0.0,4.0,130.0,3G\n",
        ],
    )

    monkeypatch.setattr(connectivity_predictor, "DATASET_PATH", dataset_path)
    _clear_predictor_caches()

    first = connectivity_predictor.predict_connectivity_for_latlon(25.60, 85.13)
    second = connectivity_predictor.predict_connectivity_for_latlon(25.60, 85.13)

    assert first == second
    assert 0.0 <= first["connectivity_score"] <= 100.0
    assert first["connectivity_group"] in {"Poor", "Average", "Good", "Excellent"}


def test_group_boundaries_are_fixed():
    assert connectivity_predictor._group_for_score(0.0) == "Poor"
    assert connectivity_predictor._group_for_score(24.0) == "Poor"
    assert connectivity_predictor._group_for_score(25.0) == "Average"
    assert connectivity_predictor._group_for_score(49.0) == "Average"
    assert connectivity_predictor._group_for_score(50.0) == "Good"
    assert connectivity_predictor._group_for_score(74.0) == "Good"
    assert connectivity_predictor._group_for_score(75.0) == "Excellent"
    assert connectivity_predictor._group_for_score(100.0) == "Excellent"


def test_offline_minutes_mapping_is_deterministic():
    assert connectivity_predictor._offline_minutes_for_score(0.0) == 180
    assert connectivity_predictor._offline_minutes_for_score(25.0) == 120
    assert connectivity_predictor._offline_minutes_for_score(50.0) == 70
    assert connectivity_predictor._offline_minutes_for_score(75.0) == 35
    assert connectivity_predictor._offline_minutes_for_score(100.0) == 15
    assert connectivity_predictor._offline_minutes_for_score(80.0) < connectivity_predictor._offline_minutes_for_score(76.0)
    assert connectivity_predictor._offline_minutes_for_score(60.0) < connectivity_predictor._offline_minutes_for_score(30.0)


def test_sparse_neighborhood_sets_fallback_metadata(monkeypatch, tmp_path):
    dataset_path = tmp_path / "signal_metrics.csv"
    _write_dataset(
        dataset_path,
        [
            "2023-05-05 12:50:40.000000,Anisabad,25.60,85.13,-84.0,0.0,8.0,80.0,4G\n",
        ],
    )

    monkeypatch.setattr(connectivity_predictor, "DATASET_PATH", dataset_path)
    _clear_predictor_caches()

    prediction = connectivity_predictor.predict_connectivity_for_latlon(25.60, 85.13)

    assert prediction["is_sparse"] is True
    assert prediction["fallback_reason"] == "sparse_local_neighborhood"
    assert prediction["data_points_used"] == 1


def test_outside_bihar_returns_fallback(monkeypatch, tmp_path):
    dataset_path = tmp_path / "signal_metrics.csv"
    _write_dataset(
        dataset_path,
        [
            "2023-05-05 12:50:40.000000,Anisabad,25.60,85.13,-84.0,0.0,8.0,80.0,4G\n",
        ],
    )

    monkeypatch.setattr(connectivity_predictor, "DATASET_PATH", dataset_path)
    _clear_predictor_caches()

    prediction = connectivity_predictor.predict_connectivity_for_latlon(12.0, 77.0)

    assert prediction["fallback_reason"] == "outside_bihar_bbox"
    assert prediction["connectivity_group"] == "Poor"
    assert prediction["expected_offline_minutes"] == connectivity_predictor._offline_minutes_for_score(
        prediction["connectivity_score"]
    )


def test_real_coordinate_prediction_works():
    prediction = connectivity_predictor.predict_connectivity_for_latlon(26.185754, 84.881594)

    assert 0.0 <= prediction["connectivity_score"] <= 100.0
    assert prediction["connectivity_group"] in {"Poor", "Average", "Good", "Excellent"}
    assert prediction["expected_connectivity"] == prediction["connectivity_group"]
    assert isinstance(prediction["expected_offline_minutes"], int)
    assert prediction["expected_offline_minutes"] >= 0
    assert prediction["fallback_reason"] != "outside_bihar_bbox"
