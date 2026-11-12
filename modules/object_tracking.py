"""
Simple centroid-based multi-object tracker.

This is NOT a deep-learning tracker. It links detections between
consecutive frames purely by the distance between their centroids:

    1. For each new frame we receive the list of detected centroids.
    2. We compute the Euclidean distance between every existing track and
       every new centroid.
    3. Pairs are matched greedily, closest first, as long as the distance
       is below `max_distance` pixels.
    4. Unmatched detections start new tracks (new IDs).
    5. Unmatched tracks are marked "disappeared"; if a track is missing for
       more than `max_disappeared` consecutive frames it is removed.

Step 5 lets an object survive short missed detections (e.g. motion blur or
brief occlusion) while keeping its ID.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np

Point = Tuple[int, int]
Box = Tuple[int, int, int, int]


@dataclass
class Track:
    """State kept for one tracked object."""

    track_id: int
    centroid: Point
    box: Box
    first_frame: int
    last_frame: int
    disappeared: int = 0
    hits: int = 1
    trail: Deque[Point] = field(default_factory=lambda: deque(maxlen=40))


class CentroidTracker:
    """Track objects across frames by nearest-centroid matching."""

    def __init__(self, max_disappeared: int = 15, max_distance: float = 80.0,
                 trail_length: int = 40):
        self.max_disappeared = int(max_disappeared)
        self.max_distance = float(max_distance)
        self.trail_length = int(trail_length)
        self.next_id = 1
        self.tracks: "OrderedDict[int, Track]" = OrderedDict()
        # Every track ever created, kept for analytics after processing.
        self.history: Dict[int, Dict] = {}

    # -- internal helpers ---------------------------------------------------
    def _register(self, centroid: Point, box: Box, frame_idx: int) -> None:
        track = Track(self.next_id, centroid, box, frame_idx, frame_idx,
                      trail=deque(maxlen=self.trail_length))
        track.trail.append(centroid)
        self.tracks[self.next_id] = track
        self.history[self.next_id] = {
            "first_frame": frame_idx,
            "last_frame": frame_idx,
            "hits": 1,
            "path": [(frame_idx, centroid[0], centroid[1])],
        }
        self.next_id += 1

    def _deregister(self, track_id: int) -> None:
        self.tracks.pop(track_id, None)

    def _update_track(self, track: Track, centroid: Point, box: Box, frame_idx: int) -> None:
        track.centroid = centroid
        track.box = box
        track.last_frame = frame_idx
        track.disappeared = 0
        track.hits += 1
        track.trail.append(centroid)
        record = self.history[track.track_id]
        record["last_frame"] = frame_idx
        record["hits"] += 1
        record["path"].append((frame_idx, centroid[0], centroid[1]))

    def _mark_missing(self, track_id: int) -> None:
        track = self.tracks[track_id]
        track.disappeared += 1
        if track.disappeared > self.max_disappeared:
            self._deregister(track_id)

    # -- public API ---------------------------------------------------------
    def update(self, detections: Sequence[Tuple[Point, Box]], frame_idx: int) -> List[Track]:
        """Update the tracker with this frame's detections.

        detections: list of (centroid, bounding_box) tuples.
        Returns the tracks that were matched or created in this frame
        (i.e. the objects visible right now).
        """
        visible: List[Track] = []

        # No detections: every track is missing for one more frame.
        if len(detections) == 0:
            for track_id in list(self.tracks.keys()):
                self._mark_missing(track_id)
            return visible

        # No existing tracks: everything is new.
        if len(self.tracks) == 0:
            for centroid, box in detections:
                self._register(centroid, box, frame_idx)
                visible.append(self.tracks[self.next_id - 1])
            return visible

        track_ids = list(self.tracks.keys())
        track_points = np.array([self.tracks[t].centroid for t in track_ids], dtype=float)
        det_points = np.array([c for c, _ in detections], dtype=float)

        # Distance matrix: rows = existing tracks, cols = new detections
        diff = track_points[:, None, :] - det_points[None, :, :]
        distances = np.sqrt((diff ** 2).sum(axis=2))

        used_rows, used_cols = set(), set()
        # Greedy matching: consider all pairs from closest to farthest.
        for flat_index in np.argsort(distances, axis=None):
            row, col = divmod(int(flat_index), distances.shape[1])
            if row in used_rows or col in used_cols:
                continue
            if distances[row, col] > self.max_distance:
                break  # all remaining pairs are even farther away
            track = self.tracks[track_ids[row]]
            centroid, box = detections[col]
            self._update_track(track, centroid, box, frame_idx)
            visible.append(track)
            used_rows.add(row)
            used_cols.add(col)

        # Existing tracks that found no partner
        for row, track_id in enumerate(track_ids):
            if row not in used_rows:
                self._mark_missing(track_id)

        # New detections that found no partner -> new tracks
        for col, (centroid, box) in enumerate(detections):
            if col not in used_cols:
                self._register(centroid, box, frame_idx)
                visible.append(self.tracks[self.next_id - 1])

        return visible

    @property
    def total_tracks(self) -> int:
        """Number of unique IDs created so far."""
        return self.next_id - 1

    def summary(self, min_hits: int = 1) -> List[Dict]:
        """Per-track statistics for the analytics page."""
        rows = []
        for track_id, record in self.history.items():
            if record["hits"] < min_hits:
                continue
            path = record["path"]
            distance = 0.0
            for (_, x1, y1), (_, x2, y2) in zip(path, path[1:]):
                distance += float(np.hypot(x2 - x1, y2 - y1))
            rows.append({
                "Track ID": track_id,
                "First frame": record["first_frame"],
                "Last frame": record["last_frame"],
                "Frames seen": record["hits"],
                "Path length (px)": round(distance, 1),
            })
        return rows

    def get(self, track_id: int) -> Optional[Track]:
        return self.tracks.get(track_id)
