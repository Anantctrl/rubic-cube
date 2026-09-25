"""Pattern database heuristic.

A **pattern database (PDB)** is a precomputed lookup table: for every possible
state of a chosen *subset* of pieces (a "pattern"), it stores the minimum
number of moves needed to reach the abstract goal (that subset back home).
The full-cube distance is always >= the pattern distance, because ignoring the
other pieces cannot make the puzzle harder — so a PDB heuristic is **admissible
by construction**.

This module is a *demonstration* of precomputation / dynamic-programming-style
reuse.  It does NOT store the whole cube: it tracks only ``k`` reference
corners (default 3, out of 7 canonical corners) — their positions and
orientations — which keeps the table tiny (a few thousand entries) while still
guiding A* much better than a naive count heuristic.
"""

from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field

from solver import cube_state as _cs
from daa.cube.state import CubeState

_PDB_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")
_PDB_FILE = os.path.join(_PDB_DIR, "pdb_3corners.pkl")

# canonical effective move tables: slot_map[i] = destination slot of the piece
# initially at slot i; orient_map[i][o] = its new orientation.
_SLOT = {m: t[0] for m, t in _cs.MOVE_TABLES.items()}
_ORIENT = {m: t[1] for m, t in _cs.MOVE_TABLES.items()}


def _abstract_goal(seeded_labels: tuple[int, ...]) -> tuple[int, int]:
    """The pattern goal: every seeded corner at its home slot, twist 0."""
    return tuple((l, 0) for l in seeded_labels)


def _abstract_key(state: CubeState, seeded_labels: tuple[int, ...]) -> tuple:
    """Project a cube state onto the pattern: ``(slot, orient)`` per corner."""
    pos_by_label = {label: idx for idx, label in enumerate(state.perm)}
    out = []
    for label in seeded_labels:
        slot = pos_by_label[label]
        out.append((slot, state.orient[slot]))
    return tuple(out)


def build_pattern_db(k: int = 3, save: bool = True) -> dict[tuple, int]:
    """BFS over the abstract pattern space; returns ``abstract_state -> dist``.

    ``k`` seeded corners; abstract state space size is
    ``7!/(7-k)! * 3**k`` (here ~5 670 for k=3), far smaller than the full
    3.67M-state cube graph — that is the whole point of a pattern database.
    """
    seeded = tuple(range(k))
    goal = _abstract_goal(seeded)

    dist: dict[tuple, int] = {goal: 0}
    frontier = [goal]
    depth = 0
    while frontier:
        depth += 1
        nxt = []
        for key in frontier:
            for move in _cs.MOVES:
                slot_map, orient_map = _SLOT[move], _ORIENT[move]
                # keep label order: key[i] always describes seeded corner i.
                child = tuple(
                    (slot_map[slot], orient_map[slot][o]) for (slot, o) in key
                )
                if child not in dist:
                    dist[child] = depth
                    nxt.append(child)
        frontier = nxt
    return dist


_PDB: dict[tuple, int] | None = None


@dataclass
class PatternDatabaseHeuristic:
    """Memoisable PDB heuristic over a fixed set of seeded corners."""

    k: int = 3
    table: dict[tuple, int] = field(default_factory=dict)
    cache: dict[tuple, int] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def __call__(self, state: CubeState) -> int:
        key = _abstract_key(state, tuple(range(self.k)))
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        value = self.table[key]
        self.cache[key] = value
        return value


def h_pattern_db_default(state: CubeState) -> int:
    """Default 3-corner PDB, built/cached once per process."""
    global _PDB
    if _PDB is None:
        table = _load_or_build()
        if table is None:
            raise RuntimeError("pattern database unavailable")
        _PDB = table
    return _abstract_lookup(state, _PDB)


def _abstract_lookup(state: CubeState, table: dict[tuple, int]) -> int:
    key = _abstract_key(state, (0, 1, 2))
    return table.get(key, 0)


def _load_or_build() -> dict[tuple, int] | None:
    if os.path.exists(_PDB_FILE):
        try:
            with open(_PDB_FILE, "rb") as fh:
                return pickle.load(fh)
        except Exception:
            pass
    os.makedirs(_PDB_DIR, exist_ok=True)
    table = build_pattern_db(k=3)
    try:
        with open(_PDB_FILE, "wb") as fh:
            pickle.dump(table, fh)
    except Exception:
        pass
    return table