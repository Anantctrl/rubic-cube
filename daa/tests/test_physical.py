"""PhysicalCubeState + /solve?algo= integration tests.

The DAA algorithms are duck-typed against a small state interface.  When they
run against :class:`~daa.cube.physical.PhysicalCubeState` instead of the
canonical ``CubeState``, their solutions must genuinely undo the 8-corner
physical cube (canonical solutions are only correct up to whole-cube rotation,
which the browser does not display).

Non-optimal searches (DFS/DLS/Backtracking/B&B) may legitimately exhaust a
resource limit and return ``found=False`` with a reason, exactly as in the
dashboard; the invariant this module pins is that *every returned solution* is
a genuine physical solve and that the optimal searches match the reference
physical solver.
"""

from __future__ import annotations

from solver import cube_state as cs
from solver import physical_solver as phys

from daa.algorithms.base import Limits
from daa.benchmark.registry import ALGORITHMS, run_algorithm
from daa.cube.physical import PhysicalCubeState

#: search budget for the "all algorithms" sweep (physical space is the full
#: 8-corner group, so tree searches are heavier than in the canonical quotient;
#: this keeps the suite fast while letting the optimal searches finish)
_SWEEP = Limits(max_depth=12, max_states=300_000, max_time_s=20.0)


def _verify_phys(start: PhysicalCubeState, solution: list[str]) -> bool:
    cur = start
    for m in solution:
        cur = cur.apply_move(m)
    return cur.is_solved()


def test_solved_is_solved() -> None:
    s = PhysicalCubeState.solved()
    assert s.is_solved()
    assert s.hash_state() == PhysicalCubeState.from_alg([]).hash_state()


def test_from_alg_matches_solver_physical() -> None:
    alg = ["R", "U", "F", "R2", "D'"]
    mine = PhysicalCubeState.from_alg(alg)
    ref = cs.apply_physical_alg(cs.PHYS_SOLVED, alg)
    assert mine.perm8 == ref[0]
    assert mine.orient8 == ref[1]


def test_hash_is_collision_free_on_sweep() -> None:
    seen = set()
    state = PhysicalCubeState.solved()
    for move in cs.MOVES:
        child = state.apply_move(move)
        assert child.hash_state() not in seen
        seen.add(child.hash_state())


def test_every_returned_solution_is_physical() -> None:
    scramble = ["R", "U", "F", "L'"]
    start = PhysicalCubeState.from_alg(scramble)
    for name in ALGORITHMS:
        res = run_algorithm(name, start, limits=_SWEEP)
        if not res.found:
            assert res.terminated, f"{name}: found=False without terminated flag"
            continue
        assert res.solution, f"{name}: found=True but empty solution"
        assert _verify_phys(start, res.solution), f"{name} solution is not physical"


def test_optimal_searches_always_solve_and_match_reference() -> None:
    """BFS / IDDFS / Bidirectional are optimal: they must solve at the
    shortest physical length AND validate against the true physical state."""
    scramble = ["R", "U", "F", "L'"]
    for name in ("BFS", "IDDFS", "Bidirectional"):
        start = PhysicalCubeState.from_alg(scramble)
        res = run_algorithm(name, start, limits=_SWEEP)
        assert res.found, f"{name} failed on {scramble}"
        assert _verify_phys(start, res.solution)
        ref_len = len(phys.solve(cs.apply_physical_alg(cs.PHYS_SOLVED, scramble))[0])
        assert res.length == ref_len, f"{name} len {res.length} != optimal {ref_len}"


def test_physical_solver_length_agrees_on_short_scrambles() -> None:
    for alg in (["R"], ["U", "F"], ["R", "U", "F", "R2"], ["L", "D'", "R", "U2", "F"]):
        start = PhysicalCubeState.from_alg(alg)
        res = run_algorithm("BFS", start, limits=_SWEEP)
        assert res.found
        assert res.length == len(phys.solve(cs.apply_physical_alg(cs.PHYS_SOLVED, alg))[0])
        assert _verify_phys(start, res.solution)


def test_heuristics_projected_are_zero_at_goal() -> None:
    from daa.heuristics import corners, misplaced

    s = PhysicalCubeState.solved()
    assert misplaced.misplaced_stickers(s) == 0
    assert misplaced.misplaced_corners(s) == 0
    assert corners.h_corners_div4(s) == 0
    assert corners.h_stickers_div12(s) == 0


def test_informed_web_algorithms_solve_deep_with_exact_h() -> None:
    """A*/Greedy/B&B on the web run with the exact BFS-table heuristic, so a
    deep scramble that the weak ``corners / 4`` bound times out on must still
    be solved, optimally, at the reference physical length."""
    scratch = ["L2", "B", "R2", "B'", "L2", "F", "L'", "U2", "L", "B2", "D2", "U2"]
    start = PhysicalCubeState.from_alg(scratch)

    # corners / 4 is far too weak on the 88M-state physical space to reach
    # distance 9 inside the sweep budget (the reported web failure).
    weak = run_algorithm("A*", start, limits=_SWEEP, heuristic_name="Admissible: corners / 4")
    assert not weak.found, "expected the weak bound to time out on a dist-9 physical scramble"
    assert weak.terminated and weak.reason

    ref_len = len(phys.solve(cs.apply_physical_alg(cs.PHYS_SOLVED, scratch))[0])
    assert ref_len == 9
    for name in ("A*", "Greedy", "Branch & Bound"):
        res = run_algorithm(name, start, limits=_SWEEP, heuristic_name="BFS distance (exact)")
        assert res.found, f"{name}: exact-h failed on dist-9 ({res.reason})"
        assert _verify_phys(start, res.solution)
        # Optimality guarantee: A* (with admissible h) and B&B (bound = exact
        # distance) return the reference length; Greedy best-first is documented
        # "not optimal" — even with a perfect h its min-h tie order can route a
        # longer chain, so we only require a physical solve here.
        if name != "Greedy":
            assert res.length == ref_len, f"{name}: len {res.length} != optimal {ref_len}"