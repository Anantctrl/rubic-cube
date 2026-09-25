"""Heuristic tests: 0-at-goal, admissibility vs optimal distance (BFS table)."""

import random

import pytest

from daa.cube.state import CubeState, from_alg
from daa.heuristics import HEURISTICS
from solver.bfs_solver import bfs_distance


def _random_states(n: int, seed: int = 0) -> list[CubeState]:
    rng = random.Random(seed)
    faces = "UDLRFB"
    out = []
    for _ in range(n):
        alg: list[str] = []
        last = None
        for _ in range(rng.randrange(1, 12)):
            while True:
                f = faces[rng.randrange(6)]
                if f != last:
                    break
            last = f
            alg.append(f + rng.choice(("", "'", "2")))
        out.append(from_alg(alg))
    return out


def test_all_heuristics_non_negative_and_zero_only_at_goal():
    for name, h in HEURISTICS.items():
        assert h.fn(CubeState.solved()) == 0, f"{name} must be 0 at solved"
        for s in _random_states(5):
            assert h.fn(s) >= 0, f"{name} negative on {s}"


def test_admissible_heuristics_never_overestimate():
    # Compare h(n) with the true optimal distance from the precomputed BFS table.
    states = _random_states(25, seed=7)
    admissible = [n for n, h in HEURISTICS.items() if h.admissible]
    assert len(admissible) >= 3, admissible
    for name in admissible:
        for s in states:
            d = bfs_distance((s.perm, s.orient))
            h = HEURISTICS[name].fn(s)
            assert h <= d, (
                f"{name} overestimated: h={h} > optimal={d} on {s}"
            )


def test_estimate_heuristics_registered_as_non_admissible():
    non_adm = [n for n, h in HEURISTICS.items() if not h.admissible]
    assert "Misplaced Stickers" in non_adm
    assert "Misplaced Corners (position)" in non_adm


def test_monotone_pattern_db_value_domain():
    h = HEURISTICS["Pattern database (3-corners)"]
    assert h.admissible is True
    for s in _random_states(15, seed=3):
        v = h.fn(s)
        assert 0 <= v <= 11


def test_corner_div4_equals_ceil_misplaced_over4():
    a = HEURISTICS["Admissible: corners / 4"].fn
    m = HEURISTICS["Misplaced Corners (position)"].fn
    for s in _random_states(20, seed=4):
        from math import ceil

        assert a(s) == ceil(m(s) / 4)


def test_registry_default_is_admissible():
    from daa.heuristics import default

    name = default()
    assert HEURISTICS[name].admissible is True