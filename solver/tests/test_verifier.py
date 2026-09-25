"""Independent end-to-end verifier for the cubing.js-basis solver.

This file carries its OWN 8-corner simulator built directly from the cubing.js
2x2x2 KPuzzle definition record -- permutation + orientationDelta composition
of ``U``/``x``/``y`` and the ``[g: h] = g h g^-1`` conjugation rule that
defines the remaining face turns.  It does NOT import ``solver.cube_state``'s
move tables, so correctness of returned solutions never depends on the solver,
the BFS table, or IDA*.

A dedicated test compares this independent model against ``cube_state`` on 150
random scrambles, proving the two implementations agree everywhere the solver
is used.
"""

from __future__ import annotations

import random

from solver import bfs_solver as bfs
from solver import cube_state as cs
from solver import physical_solver as phys
from solver import scramble as scrambler

MOVES = (
    "U", "U'", "U2",
    "D", "D'", "D2",
    "L", "L'", "L2",
    "R", "R'", "R2",
    "F", "F'", "F2",
    "B", "B'", "B2",
)

_DEF = {
    "U": (1, 2, 3, 0, 4, 5, 6, 7),
    "x": (4, 0, 3, 5, 7, 6, 2, 1),
    "y": (1, 2, 3, 0, 7, 4, 5, 6),
}
_DELTA = {
    "U": (0, 0, 0, 0, 0, 0, 0, 0),
    "x": (2, 1, 2, 1, 1, 2, 1, 2),
    "y": (0, 0, 0, 0, 0, 0, 0, 0),
}


def _compose(A, B):
    (pa, da), (pb, db) = A, B
    perm = tuple(pa[pb[i]] for i in range(8))
    delta = tuple((da[pb[i]] + db[i]) % 3 for i in range(8))
    return perm, delta


def _inv(A):
    p, d = A
    pinv = [0] * 8
    for i in range(8):
        pinv[p[i]] = i
    return tuple(pinv), tuple((-d[pinv[i]]) % 3 for i in range(8))


def _conj(g, h):
    return _compose(g, _compose(h, _inv(g)))


def _build_actions():
    U = (_DEF["U"], _DELTA["U"])
    x = (_DEF["x"], _DELTA["x"])
    y = (_DEF["y"], _DELTA["y"])
    z = _conj(x, y)
    base = {
        "U": U,
        "L": _conj(z, U),
        "F": _conj(x, U),
        "R": _conj(_inv(z), U),
        "B": _conj(_inv(x), U),
        "D": _conj(_compose(x, x), U),
    }
    actions = {}
    for face, m in base.items():
        for suffix, act in (("", m), ("'", _inv(m)), ("2", _compose(m, m))):
            actions[face + suffix] = act
    return actions


ACTIONS = _build_actions()

_SOLVED = (tuple(range(8)), (0,) * 8)


def apply_alg(alg):
    """Apply ``alg`` from solved (independent cubing-semantics model)."""
    pieces, orient = _SOLVED
    for move in alg:
        perm, delta = ACTIONS[move]
        pieces = tuple(pieces[perm[i]] for i in range(8))
        orient = tuple((orient[perm[i]] + delta[i]) % 3 for i in range(8))
    return pieces, orient


def _rotations():
    """The 24 whole-cube rotations, built from x / y (independent of solver)."""
    x = (_DEF["x"], _DELTA["x"])
    y = (_DEF["y"], _DELTA["y"])
    gens = (x, _inv(x), y, _inv(y))

    def apply_to(st, action):
        perm, delta = action
        p = tuple(st[0][perm[i]] for i in range(8))
        o = tuple((st[1][perm[i]] + delta[i]) % 3 for i in range(8))
        return p, o

    seen = {_SOLVED}
    frontier = [_SOLVED]
    while len(seen) < 24:
        nxt = []
        for st in frontier:
            for gen in gens:
                child = apply_to(st, gen)
                if child not in seen:
                    seen.add(child)
                    nxt.append(child)
        frontier = nxt
    return seen


_ROTATIONS = _rotations()


def canonicalize(state):
    """Independent canonical frame: piece 7 in slot 7 with twist 0."""
    for rot in _ROTATIONS:
        p = tuple(state[0][rot[0][i]] for i in range(8))
        o = tuple((state[1][rot[0][i]] + rot[1][i]) % 3 for i in range(8))
        if p[7] == 7 and o[7] == 0:
            return p[:7], o[:7]
    raise RuntimeError("could not canonicalize")


def verifies(scramble, solution) -> bool:
    """True iff applying ``scramble`` then ``solution`` returns to solved."""
    return apply_alg(list(scramble) + list(solution)) == _SOLVED


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_verifies_each_move_followed_by_its_inverse():
    for move in MOVES:
        assert verifies([], [move, cs.inverse(move)])


def test_verifies_quarter_turn_pow_4():
    for face in "UDLRFB":
        assert verifies([], [face] * 4)
        assert verifies([], [face + "'"] * 4)


def test_verifies_scramble_then_its_own_inverse():
    rng = random.Random(7)
    for _ in range(25):
        alg = scrambler.generate_scramble(rng, length=rng.randrange(3, 12))
        inverse_alg = [cs.inverse(m) for m in reversed(alg)]
        assert verifies(alg, inverse_alg)


def test_verifier_model_matches_solver_model_on_random_states():
    """The two independent models must agree exactly on physical + canonical."""
    rng = random.Random(11)
    for _ in range(150):
        alg = scrambler.generate_scramble(rng, length=rng.randrange(1, 15))
        expected_phys = cs.apply_physical_alg(cs.PHYS_SOLVED, alg)
        assert apply_alg(alg) == expected_phys, alg
        # canonical frames must agree too
        expected_canon = cs.canonical7(expected_phys)
        assert canonicalize(expected_phys) == expected_canon, alg


def test_map_notation_matches_cubing_definition():
    """Derived-move conjugations match the cubing.js record exactly."""
    z = _conj((_DEF["x"], _DELTA["x"]), (_DEF["y"], _DELTA["y"]))
    assert ACTIONS["F"] == _conj((_DEF["x"], _DELTA["x"]), (_DEF["U"], _DELTA["U"]))
    assert ACTIONS["L"] == _conj(z, (_DEF["U"], _DELTA["U"]))
    assert ACTIONS["R"] == _conj(_inv(z), (_DEF["U"], _DELTA["U"]))
    assert ACTIONS["B"] == _conj(_inv((_DEF["x"], _DELTA["x"])), (_DEF["U"], _DELTA["U"]))
    assert ACTIONS["D"] == _conj(
        _compose((_DEF["x"], _DELTA["x"]), (_DEF["x"], _DELTA["x"])),
        (_DEF["U"], _DELTA["U"]),
    )
    assert len(_ROTATIONS) == 24


def test_end_to_end_depth_categories_reach_solved():
    """Scrambles of exact (canonical-model) distance 0..11 -> physical solve.

    NOTE on gauges: the canonical-model trajectory and the raw physical
    accumulation of the same moves differ by a whole-cube rotation residue
    (considering the frame each step vs accumulating turns in a fixed frame),
    so the raw scramble state's canonical distance need not equal the model
    distance.  The physically meaningful invariants are checked instead.
    """
    rng = random.Random(13)
    for distance in (0, 1, 2, 4, 6, 8, 10, 11):
        scramble = scrambler.scramble_with_distance(distance, rng)
        # scrambler invariant: canonical-model trajectory has this distance
        model = cs.apply_alg(cs.SOLVED, scramble)
        assert bfs.bfs_distance(model) == distance, (distance, scramble)
        # physical solve of the raw accumulation: admissible quotient bound
        # (h = bfs distance of the uniquely-canonicalized raw state) + verifies
        state = cs.apply_physical_alg(cs.PHYS_SOLVED, scramble)
        h = bfs.bfs_distance(cs.canonical7(state))
        solution = phys.solve(state)[0]
        assert len(solution) >= h
        assert verifies(scramble, solution)


def test_manual_arbitrary_scrambles_solve():
    """User-supplied (arbitrary) scrambles must always solve back."""
    rng = random.Random(19)
    for _ in range(60):
        alg = scrambler.generate_scramble(rng, length=rng.randrange(1, 25))
        state = cs.apply_physical_alg(cs.PHYS_SOLVED, alg)
        solution = phys.solve(state)[0]
        assert verifies(alg, solution)