"""Admissible heuristics.

A heuristic is admissible when ``h(n) <= h*(n)`` for every state ``n``, where
``h*(n)`` is the true shortest distance to goal.  Both heuristics below are
admissible because they divide a "potential disturbance" measure by the
maximum number of units a single move can repair:

- a face turn permutes at most 4 corners   -> ``ceil(errors / 4)``
- a face turn moves at most 12 stickers     -> ``ceil(errors / 12)``

``ceil(x/k) = (x + k - 1) // k``.  Division is what makes them admissible:
a count alone may exceed the true move distance, but the **average damage per
move** is a rock-bottom lower bound.
"""

from __future__ import annotations

from math import ceil

from daa.cube.state import CubeState
from daa.heuristics.misplaced import misplaced_corners, misplaced_stickers


def h_corners_div4(state: CubeState) -> int:
    """ceil(misplaced corners / 4) — strong-ish, admissible."""
    return ceil(misplaced_corners(state) / 4)


def h_stickers_div12(state: CubeState) -> int:
    """ceil(misplaced stickers / 12) — weak but admissible."""
    return ceil(misplaced_stickers(state) / 12)