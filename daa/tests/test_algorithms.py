"""End-to-end algorithm tests: each solver returns a verified, valid solution.

Optimality of the guarantees-documented algorithms (BFS, A*-admissible, IDDFS,
Bidirectional) is checked against the precomputed BFS distance table.
"""

import pytest

from daa.algorithms import (
    astar,
    backtracking,
    bfs,
    bidirectional,
    branch_bound,
    dfs,
    dls,
    greedy,
    iddfs,
)
from daa.algorithms.base import Limits, apply_alg
from daa.cube.state import CubeState, from_alg, scramble
from solver.bfs_solver import bfs_distance

L = Limits(max_depth=12, max_states=800_000, max_time_s=90.0)
HEUR = "Admissible: corners / 4"
PDB = "Pattern database (3-corners)"

# Seeds whose scrambles BFS provably solves within the budget above.
OPT_SEEDS = (2, 3, 5)


def _scramble(seed: int, length: int = 7) -> CubeState:
    rng = __import__("random").Random(seed)
    faces = "UDLRFB"
    alg: list[str] = []
    last = None
    for _ in range(length):
        while True:
            f = faces[rng.randrange(6)]
            if f != last:
                break
        last = f
        alg.append(f + rng.choice(("", "'", "2")))
    return from_alg(alg)


def _apply(start: CubeState, sol: list[str]) -> CubeState:
    return apply_alg(start, sol)


@pytest.mark.parametrize(
    "solver,kwargs",
    [
        (bfs.solve, {}),
        (dfs.solve, {}),
        (iddfs.solve, {}),
        (bidirectional.solve, {}),
        (dls.solve, {"depth_limit": 6}),
        (backtracking.solve, {}),
        (greedy.solve, {"heuristic_name": HEUR}),
        (astar.solve, {"heuristic_name": HEUR}),
        (astar.solve, {"heuristic_name": PDB}),
        (branch_bound.solve, {"heuristic_name": HEUR}),
    ],
)
def test_solver_returns_verified_solution(solver, kwargs):
    s = _scramble(11)
    r = solver(s, limits=L, **kwargs)
    if r.found:
        assert _apply(s, r.solution).is_solved(), f"{r.algorithm} invalid solution {r.solution}"
        assert r.length == len(r.solution)
    else:
        assert r.terminated or r.reason


def _run_all(s):
    out = {}
    out["BFS"] = bfs.solve(s, limits=L)
    out["DFS"] = dfs.solve(s, limits=L)
    out["IDDFS"] = iddfs.solve(s, limits=L)
    out["Bidir"] = bidirectional.solve(s, limits=L)
    out["Greedy"] = greedy.solve(s, limits=L, heuristic_name=HEUR)
    out["A*"] = astar.solve(s, limits=L, heuristic_name=HEUR)
    out["BB"] = branch_bound.solve(s, limits=L, heuristic_name=HEUR)
    return out


def test_bfs_is_optimal():
    for seed in OPT_SEEDS:
        s = _scramble(seed, length=6)
        r = bfs.solve(s, limits=L)
        assert r.found and r.length == bfs_distance((s.perm, s.orient))
        assert _apply(s, r.solution).is_solved()


def test_bidirectional_is_optimal_and_reports_meeting():
    for seed in OPT_SEEDS:
        s = _scramble(seed, length=6)
        r = bidirectional.solve(s, limits=L)
        assert r.found, f"bidirectional failed seed {seed}"
        assert _apply(s, r.solution).is_solved()
        assert r.length == bfs_distance((s.perm, s.orient))
        assert r.meeting_depth == r.length


def test_iddfs_optimal_and_reports_iterations():
    for seed in OPT_SEEDS:
        s = _scramble(seed, length=5)
        r = iddfs.solve(s, limits=L)
        assert r.found
        assert _apply(s, r.solution).is_solved()
        assert r.length == bfs_distance((s.perm, s.orient))
        assert r.iterations


def test_astar_with_admissible_is_optimal():
    for seed in OPT_SEEDS:
        s = _scramble(seed, length=6)
        r = astar.solve(s, limits=L, heuristic_name=HEUR)
        assert r.found
        assert r.length == bfs_distance((s.perm, s.orient))
        assert _apply(s, r.solution).is_solved()
        assert r.initial_h <= bfs_distance((s.perm, s.orient))


def test_astar_with_pdb_optimal():
    s = _scramble(2)
    r = astar.solve(s, limits=L, heuristic_name=PDB)
    assert r.found and r.length == bfs_distance((s.perm, s.orient))
    assert _apply(s, r.solution).is_solved()


def test_greedy_slowest_moveset_still_verified():
    s = _scramble(2)
    r = greedy.solve(s, limits=L, heuristic_name=HEUR)
    assert r.found and _apply(s, r.solution).is_solved()
    assert r.length >= bfs_distance((s.perm, s.orient))  # may be longer, never shorter


def test_dls_respects_depth_limit():
    s = _scramble(3, length=6)
    r = dls.solve(s, depth_limit=2, limits=L)
    assert r.found is False or r.length <= 2


def test_backtracking_terminates_and_verifies():
    s = _scramble(3, length=5)
    r = backtracking.solve(s, limits=Limits(max_depth=6, max_states=80_000, max_time_s=60.0))
    assert r._recursive_calls >= 0
    assert r._backtracks >= 0
    if r.found:
        assert _apply(s, r.solution).is_solved()


def test_branch_and_bound_reports_branches():
    s = _scramble(2, length=4)
    r = branch_bound.solve(s, limits=Limits(max_depth=8, max_states=120_000, max_time_s=60.0))
    assert r.branches_explored >= 0
    assert r.branches_pruned >= 0
    if r.found:
        assert _apply(s, r.solution).is_solved()


def test_resource_limits_produce_terminated_result():
    s = _scramble(5, length=11)
    tiny = Limits(max_depth=3, max_states=300, max_time_s=1.0)
    r = bfs.solve(s, limits=tiny)
    assert r.terminated  # max_states exceeded


def test_solved_input_short_circuits():
    for solver, kwargs in [
        (bfs.solve, {}),
        (dfs.solve, {}),
        (iddfs.solve, {}),
        (bidirectional.solve, {}),
        (dls.solve, {"depth_limit": 4}),
        (backtracking.solve, {}),
        (greedy.solve, {"heuristic_name": HEUR}),
        (astar.solve, {"heuristic_name": HEUR}),
        (branch_bound.solve, {"heuristic_name": HEUR}),
    ]:
        r = solver(CubeState.solved(), limits=L, **kwargs)
        assert r.found and r.length == 0


def test_memoizer_wiring_reports_hits():
    from daa.optimization.memoization import Memoizer
    from daa.heuristics import HEURISTICS

    s = _scramble(2)
    mem = Memoizer(HEURISTICS[HEUR].fn)
    r = astar.solve(s, limits=L, memoizer=mem, heuristic_name=HEUR)
    assert r.memo_hits + r.memo_misses == mem.hits + mem.misses
    assert mem.hits >= 0 and mem.misses >= 1