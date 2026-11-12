"""Tests for the centroid tracker (modules/object_tracking.py)."""

from modules.object_tracking import CentroidTracker


def det(x, y):
    return ((x, y), (x - 5, y - 5, 10, 10))


def test_ids_stay_consistent_for_moving_objects():
    tracker = CentroidTracker(max_disappeared=5, max_distance=50)
    for f in range(20):
        visible = tracker.update([det(10 + 5 * f, 50), det(300 - 5 * f, 200)], f)
        ids = {t.centroid: t.track_id for t in visible}
        assert ids[(10 + 5 * f, 50)] == 1
        assert ids[(300 - 5 * f, 200)] == 2
    assert tracker.total_tracks == 2


def test_track_survives_short_occlusion():
    tracker = CentroidTracker(max_disappeared=5, max_distance=60)
    for f in range(5):
        tracker.update([det(100 + 4 * f, 100)], f)
    for f in range(5, 8):          # 3 frames with no detection
        tracker.update([], f)
    visible = tracker.update([det(132, 100)], 8)
    assert visible[0].track_id == 1
    assert tracker.total_tracks == 1


def test_track_removed_after_max_disappeared():
    tracker = CentroidTracker(max_disappeared=2, max_distance=60)
    tracker.update([det(100, 100)], 0)
    for f in range(1, 5):
        tracker.update([], f)
    assert len(tracker.tracks) == 0
    visible = tracker.update([det(100, 100)], 5)
    assert visible[0].track_id == 2  # a new ID, the old one was dropped


def test_far_detection_creates_new_track():
    tracker = CentroidTracker(max_disappeared=5, max_distance=30)
    tracker.update([det(10, 10)], 0)
    visible = tracker.update([det(300, 300)], 1)
    assert visible[0].track_id == 2


def test_new_object_appearing_gets_new_id():
    tracker = CentroidTracker()
    tracker.update([det(50, 50)], 0)
    visible = tracker.update([det(52, 50), det(400, 300)], 1)
    assert sorted(t.track_id for t in visible) == [1, 2]


def test_summary_reports_path_length():
    tracker = CentroidTracker()
    for f in range(11):
        tracker.update([det(10 * f, 0)], f)
    row = tracker.summary()[0]
    assert row["Frames seen"] == 11
    assert row["Path length (px)"] == 100.0
