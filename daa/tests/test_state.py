"""CubeState unit tests: determinism, immutability, move algebra."""

import pytest

from daa.cube.state import CubeState, from_alg, scramble
from daa.optimization.pruning import MovePruner


def _rng_alg(seed: int, length: int = 8) -> list[str]:
    import random

    rng = random.Random(seed)
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
    return alg


def test_solved_constructors():
    assert CubeState.solved().is_solved()
    assert from_alg([]) == CubeState.solved()


def test_scramble_returns_valid_move_list():
    alg = scramble(6)
    assert isinstance(alg, list)
    assert len(alg) == 6
    from daa.cube.state import MOVES

    for m in alg:
        assert m in MOVES


def test_apply_then_undo_returns_original():
    s = CubeState.solved()
    for m in ("R", "U", "F", "R'", "U2"):
        assert s.apply_move(m).undo_move(m) == s
        assert s.undo_move(m).apply_move(m).apply_move(m).undo_move(m) == s


def test_immutable_hashable():
    s = from_alg(_rng_alg(1))
    h1 = hash(s)
    s2 = s.apply_move("R")
    assert hash(s) == h1  # frozen — never changes
    assert s2 != s
    assert s2.perm == s.apply_move("R").perm


def test_hash_state_encoding_is_consistent():
    s = from_alg(_rng_alg(2))
    assert isinstance(s.hash_state(), int)
    assert CubeState(*((s.perm, s.orient))) == s
    assert s.hash_state() == from_alg(_rng_alg(2)).hash_state()


def test_full_move_algebra_roundtrip():
    # applying the inverse of every move in reverse undoes the sequence
    import random

    rng = random.Random(3)
    from daa.cube.state import MOVES

    alg = [MOVES[rng.randrange(len(MOVES))] for _ in range(10)]
    s = from_alg(alg)
    for m in reversed(alg):
        s = s.undo_move(m)
    assert s.is_solved()


def test_from_alg_matches_solver_model():
    from solver import cube_state as cs

    alg = _rng_alg(4)
    got = from_alg(alg)
    expected = cs.apply_alg(cs.SOLVED, alg)
    assert got.perm == expected[0]
    assert got.orient == expected[1]


def test_neighbours_respects_face_filter():
    s = CubeState.solved()
    moves = {m for m, _ in s.neighbours("U")}
    assert moves == {"U", "U'", "U2"}
    assert len(s.neighbours()) == 18


def test_pruner_rules():
    p = MovePruner()
    pm = set(p.allowed_moves(None))
    assert len(pm) == 18
    safe = set(p.allowed_moves("R"))
    assert "R'" not in safe and "R" not in safe and "R2" not in safe
    for m in safe:
        assert m[0] != "R"
    # same face reduced
    assert len(set(p.allowed_moves("U'")).intersection({"U", "U'", "U2"})) == 0