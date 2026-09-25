"""Simple (non-admissible) counting heuristics.

Both are useful as teaching baselines for A* and Greedy, and are deliberately
labelled ``admissible=False`` in the registry: they can overestimate the true
distance.  For example misplacing 2 stickers does NOT imply 2 moves are needed
— a single turn fixes many stickers at once.
"""

from __future__ import annotations

from daa.cube.state import CubeState

_SOLVED_PERM = tuple(range(7))
_SOLVED_ORIENT = (0,) * 7


def misplaced_corners(state: CubeState) -> int:
    """Count of corner cubies in a wrong position (orientation ignored)."""
    return sum(1 for a, b in zip(state.perm, _SOLVED_PERM) if a != b)


def misplaced_stickers(state: CubeState) -> int:
    """Count of mis-oriented + misplaced corner stickers.

    A corner is "sticker-correct" only if it occupies its home slot *and* has
    the home orientation.  Each disturbed corner costs its 3 stickers.
    """
    count = 0
    for i in range(7):
        if state.perm[i] != _SOLVED_PERM[i]:
            count += 3
        elif state.orient[i] != _SOLVED_ORIENT[i]:
            count += 3
    return count