"""PhysicalCubeState — the 8-corner physical state as a DAA search node.

The DAA algorithms are written against a small duck-typed interface:

    apply_move(move) -> state
    is_solved()      -> bool
    solved()         -> the goal state
    hash_state()     -> collision-free int (duplicate-detection key)

``daa.cube.state.CubeState`` satisfies that contract in the *canonical*
7-corner quotient (piece 7 fixed).  That quotient is perfect for studying the
algorithms — its move tables form a well-defined graph — but a canonical
solution, applied as real face turns to the cube the browser displays, is only
correct *up to a whole-cube rotation*: the quotient is by the 24 rotations,
which is not a subgroup-compatible quotient, so canonical move sequences do not
faithfully descend to physical move sequences.

This module solves that: it wraps a full 8-corner ``(perm, orient)`` physical
state and implements the same DAA interface using real face turns
(``cube_state.apply_physical``).  Every search now runs over the *actual*
physical cube group, so the moves an algorithm returns genuinely solve the
cube on screen.

Heuristics stay admissible: they are computed on the rotation-quotient
``canonical7`` projection of the physical state, whose distance to solved
equals the physical distance (rotating the whole cube never changes the
minimum number of face turns).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solver import cube_state as _cs

#: collision-free packed code of the solved physical cube (computed once).
_SOLVED_CODE = None  # type: int | None


def _pack(p8, o8) -> int:
    """Bijective int code for an 8-corner state.

    perm8 uses 3 bits per corner (8 x 3 = 24 bits), orient8 uses 2 bits per
    corner (8 x 2 = 16 bits); concatenated -> 40-bit code, unique per state.
    """
    code = 0
    for i, p in enumerate(p8):
        code |= p << (3 * i)
    for i, o in enumerate(o8):
        code |= o << (24 + 2 * i)
    return code


@dataclass(frozen=True)
class PhysicalCubeState:
    """An immutable 8-corner physical cube state, usable as a search node."""

    perm8: tuple[int, ...]
    orient8: tuple[int, ...]

    # lazy rotation-quotient projection (heuristic input); computed only when
    # an informed search actually reads ``.perm`` / ``.orient``.
    _c7: tuple[tuple[int, ...], tuple[int, ...]] | None = field(
        init=False, compare=False, repr=False, default=None
    )

    @property
    def perm(self) -> tuple[int, ...]:
        return self._projection()[0]

    @property
    def orient(self) -> tuple[int, ...]:
        return self._projection()[1]

    def _projection(self) -> tuple[tuple[int, ...], tuple[int, ...]]:
        if self._c7 is None:
            object.__setattr__(self, "_c7", _cs.canonical7((self.perm8, self.orient8)))
        return self._c7

    # -- constructors -----------------------------------------------------
    @classmethod
    def solved(cls) -> "PhysicalCubeState":
        return cls(_cs.PHYS_SOLVED[0], _cs.PHYS_SOLVED[1])

    @classmethod
    def from_alg(cls, alg: list[str]) -> "PhysicalCubeState":
        """State reached by physically applying ``alg`` to the solved cube."""
        state = (tuple(range(8)), (0,) * 8)
        for move in alg:
            state = _cs.apply_physical(state, move)
        return cls(state[0], state[1])

    # -- DAA interface ----------------------------------------------------
    def apply_move(self, move: str) -> "PhysicalCubeState":
        p8, o8 = _cs.apply_physical((self.perm8, self.orient8), move)
        return PhysicalCubeState(p8, o8)

    def undo_move(self, move: str) -> "PhysicalCubeState":
        return self.apply_move(_cs.inverse(move))

    def is_solved(self) -> bool:
        return self.perm8 == _cs.PHYS_SOLVED[0] and self.orient8 == _cs.PHYS_SOLVED[1]

    def hash_state(self) -> int:
        return _pack(self.perm8, self.orient8)

    def __str__(self) -> str:
        return f"PhysicalCubeState(perm={self.perm8}, orient={self.orient8})"