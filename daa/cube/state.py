"""CubeState — deterministic, hashable, immutable 2x2x2 state.

Wraps the canonical 7-corner ``(perm, orient)`` representation from
``solver.cube_state``.  The DAA algorithms treat the cube as an *implicit
graph*:

    cube configuration  = node
    legal cube move     = directed edge  (well, symmetric in fact)
    move sequence       = path
    solved cube         = goal node

No full graph is ever built in memory; neighbours are generated lazily with
:meth:`CubeState.neighbours`.  States are immutable tuples of tuples, so they
are natively hashable and usable directly as ``dict``/``set`` keys (duplicate
detection), and ``encode`` gives a dense collision-free integer code.
"""

from __future__ import annotations

from dataclasses import dataclass

from solver import cube_state as _cs
from solver import bfs_solver as _bfs

#: The 18 legal face turns in the canonical DAA move alphabet.
MOVES: tuple[str, ...] = _cs.MOVES

SOLVED_PHYS = _cs.PHYS_SOLVED


@dataclass(frozen=True)
class CubeState:
    """A canonical 2x2x2 state: ``(perm7, orient7)``, piece 7 fixed in slot 7.

    ``frozen=True`` + tuple-of-tuples layout makes it immutable and hashable,
    which is exactly what the DAA search algorithms rely on.
    """

    perm: tuple[int, ...]
    orient: tuple[int, ...]

    # -- constructors -----------------------------------------------------
    @classmethod
    def solved(cls) -> "CubeState":
        return cls(_cs.SOLVED[0], _cs.SOLVED[1])

    @classmethod
    def from_alg(cls, alg: list[str]) -> "CubeState":
        """State reached by applying ``alg`` to the solved cube."""
        perm, orient = _cs.SOLVED
        for m in alg:
            perm, orient = _cs.apply_move((perm, orient), m)
        return cls(perm, orient)

    # -- DAA spec interface ----------------------------------------------
    def apply_move(self, move: str) -> "CubeState":
        """Return the new state after ``move`` (immutable — state unchanged)."""
        perm, orient = _cs.apply_move((self.perm, self.orient), move)
        return CubeState(perm, orient)

    def undo_move(self, move: str) -> "CubeState":
        """Return the state *before* ``move`` (apply the algebraic inverse)."""
        return self.apply_move(_cs.inverse(move))

    def is_solved(self) -> bool:
        return self.perm == _cs.SOLVED[0] and self.orient == _cs.SOLVED[1]

    def clone_state(self) -> "CubeState":
        return self  # immutable — cloning is a no-op, documented as such.

    def hash_state(self) -> int:
        """Collision-free integer code (duplicate-detection key)."""
        return _bfs.encode(self.perm, self.orient)

    # -- implicit-graph helpers ------------------------------------------
    def neighbours(self, faces: str = "UDLRFB") -> list[tuple[str, "CubeState"]]:
        """Generate all ``(move, state)`` edges out of this node.

        ``faces`` restricts which faces may be turned (used by move pruning:
        an exhaustive data structure such as BFS can use all six faces, while
        tree searches restrict them to honour the same-face rule).
        """
        out: list[tuple[str, CubeState]] = []
        for m in MOVES:
            if m[0] not in faces:
                continue
            out.append((m, self.apply_move(m)))
        return out

    def __str__(self) -> str:
        return f"CubeState(perm={self.perm}, orient={self.orient})"


def solved() -> CubeState:
    return CubeState.solved()


def from_alg(alg: list[str]) -> CubeState:
    return CubeState.from_alg(alg)


def scramble(length: int = 10) -> list[str]:
    """A fresh random scramble (DAA entry point; delegates to solver.scramble)."""
    from solver import scramble as _scrambler

    return _scrambler.generate_scramble(length=length)