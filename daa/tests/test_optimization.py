"""Optimization-module tests (hashing, pruning, memoization)."""

from daa.cube.state import CubeState, from_alg
from daa.optimization.hashing import StateHasher
from daa.optimization.memoization import Memoizer
from daa.optimization.pruning import MovePruner


def hint(s: CubeState) -> int:
    return sum(1 for v in s.orient if v != 0)


def test_state_hasher_counts_unique_and_duplicates():
    h = StateHasher()
    s = CubeState.solved()
    assert h.visit(s) is False  # first visit: new state
    assert h.duplicates == 0
    assert h.visit(s) is True  # second visit: duplicate
    assert h.visit(s) is True
    assert h.duplicates == 2
    assert h.unique_count == 1


def test_pruner_forbids_inverse_and_same_face():
    p = MovePruner()
    no_prev = set(p.allowed_moves(None))
    assert "R" in no_prev and len(no_prev) == 18

    after_r = set(p.allowed_moves("R"))
    assert after_r == {"U", "U'", "U2", "D", "D'", "D2", "L", "L'", "L2",
                       "F", "F'", "F2", "B", "B'", "B2"}

    after_u2 = set(p.allowed_moves("U2"))
    for m in ("U", "U'", "U2"):
        assert m not in after_u2
    assert "U" not in after_u2 and "U'" not in after_u2


def test_pruner_forbids_consecutive_repeats():
    p = MovePruner()
    after = p.allowed_moves("F2")
    # same face dropped; also F itself (same face), never inverse (different face)
    assert all(m[0] != "F" for m in after)


def test_memoizer_counts_hits_and_misses():
    m = Memoizer(hint)
    s = from_alg(["R"])
    assert m(s) == hint(s)  # miss
    assert m.misses == 1
    assert m(s) == hint(s)  # hit
    assert m.hits == 1
    assert m.hits + m.misses == 2


def test_memoizer_results_equal_raw_fn():
    m = Memoizer(hint)
    for alg in (["R"], ["U", "F'"], ["R2", "U2", "F'"], []):
        s = from_alg(alg)
        assert m(s) == hint(s)