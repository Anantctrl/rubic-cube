"""Heuristics for informed search (A*, Greedy, Branch & Bound).

Every heuristic is a pure ``CubeState -> int``.  For **admissible** heuristics
``h(n) <= h*(n)`` holds for every state (``h`` never overestimates), which is
what lets A* return proven-optimal solutions; **estimate-only** heuristics may
return longer-guesses and are labelled explicitly in the UI so the DAA report
can distinguish an "estimate" from an "admissible lower bound".

Registry
--------
``HEURISTICS: dict[str, Heuristic]`` maps a display name to a callable plus
its admissibility flag (``admissible: bool``) for the UI menu.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from daa.cube.state import CubeState
from daa.heuristics import corners, misplaced, pattern_database

#: callable signature:  h(state) -> int  (non-negative, 0 at goal)
HeuristicFn = Callable[[CubeState], int]


def h_bfs_distance(state) -> int:
    """Exact optimal distance via the precomputed full BFS table.

    Reads the optimal length straight out of ``solver/bfs_table.npy`` for the
    state's canonical projection (``state.perm`` / ``state.orient``).  Because
    a whole-cube rotation never changes the minimum number of face turns, the
    canonical distance equals the physical distance — so this heuristic is
    *perfect*: h == h* for every state (exactly admissible).  It is the same
    admissible heuristic the physical IDA* solver uses; providing it to an
    informed search collapses the search to (near) the optimal path.
    """
    from solver import bfs_solver as bfs

    return int(bfs.bfs_distance((state.perm, state.orient)))


@dataclass(frozen=True)
class Heuristic:
    name: str
    fn: HeuristicFn
    admissible: bool
    description: str


def make_registry() -> dict[str, Heuristic]:
    heuristics: dict[str, Heuristic] = {}

    def reg(name: str, fn: HeuristicFn, admissible: bool, description: str) -> None:
        heuristics[name] = Heuristic(name, fn, admissible, description)

    reg(
        "Misplaced Stickers",
        misplaced.misplaced_stickers,
        False,
        "Number of facelets whose colour differs from the solved colour. "
        "A facelet is 'correct' if the sticker in that slot is the colour the "
        "solved cube shows there.  This is an *estimate* (a single move can "
        "fix up to 12 stickers), so A* is NOT optimal with it.",
    )
    reg(
        "Misplaced Corners (position)",
        misplaced.misplaced_corners,
        False,
        "Number of corner cubies not in their solved position.  Estimate "
        "only: one move can place up to 4 corners, but also disturb others.",
    )
    reg(
        "Admissible: corners / 4",
        corners.h_corners_div4,
        True,
        "ceil(misplaced_corners / 4).  A single face turn changes at most 4 "
        "corner positions, so this never overestimates the remaining number "
        "of moves: admissible -> A* is optimal with it.",
    )
    reg(
        "Admissible: stickers / 12",
        corners.h_stickers_div12,
        True,
        "ceil(misplaced_stickers / 12).  One move turns at most 12 stickers "
        "so this is admissible (weak but safe).",
    )
    reg(
        "Pattern database (3-corners)",
        pattern_database.h_pattern_db_default,
        True,
        "h(n) extracted from a pattern database covering 3 reference corners "
        "(positions + orientations ignored otherwise).  Precomputed once and "
        "cached on disk; admissible by construction (projection distance).",
    )
    reg(
        "BFS distance (exact)",
        h_bfs_distance,
        True,
        "Perfect heuristic: the exact optimal distance, looked up in O(1) from "
        "the precomputed full BFS table (same admissible h as the physical IDA* "
        "solver).  Equal to the true distance on every state, so informed "
        "searches with it expand (near) only the optimal path.",
    )
    return heuristics


HEURISTICS = make_registry()


def get(name: str) -> Heuristic:
    return HEURISTICS[name]


def default() -> str:
    return "Admissible: corners / 4"