"""Move pruning.

Three safe, configurable pruning rules used while expanding a search node:

1. **Inverse-move pruning** — never follow a move with its algebraic inverse
   (``R R'``).  The two moves cancel; that branch can only waste space.
2. **Same-face pruning** — never turn the same face twice in a row
   (``R R``, ``R R2``, ``R R'``, ...).  Any two consecutive turns of one
   face collapse into a single turn of that face (e.g. ``R R = R2``), which
   the algorithm will generate on its own, so deeper duplicates are removed
   without losing any shortest solution.
3. **Consecutive-repeat pruning** — never apply the exact same move twice in
   a row (a special case of same-face, kept as a separately-controllable
   rule for the pedagogical UI).

All three rules are **complete**: for the 2x2x2 group, the pruned edges are
always "dominated" — their removal cannot increase the length of the shortest
path to any state, because a one-move shorter alias of the branch's first two
moves always exists in the remaining move set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from solver import cube_state as _cs

# canonical move-inverse table
_INVERSE = {m: _cs.inverse(m) for m in _cs.MOVES}
_FACE = {m: m[0] for m in _cs.MOVES}


@dataclass
class MovePruner:
    inverse_move: bool = True
    same_face: bool = True
    consecutive_repeat: bool = True

    @property
    def description(self) -> list[str]:
        active = []
        if self.inverse_move:
            active.append("Inverse-move pruning (R R′)")
        if self.same_face:
            active.append("Same-face pruning (R R → R2)")
        if self.consecutive_repeat:
            active.append("Consecutive-repeat pruning (R R)")
        if not active:
            active = ["none (full branching)"]
        return active

    def allowed_moves(self, last_move: str | None) -> list[str]:
        """Branch factor after pruning, given the move just applied (or None).

        Returns the subset of ``MOVES`` that may follow ``last_move``.
        """
        if last_move is None:
            return list(_cs.MOVES)
        out = []
        for m in _cs.MOVES:
            if self.inverse_move and m == _INVERSE[last_move]:
                continue  # cancel: R R' is a wasted branch
            if self.same_face and _FACE[m] == _FACE[last_move]:
                continue  # R R, R R2, R' R2 ... collapse
            if self.consecutive_repeat and m == last_move:
                continue
            out.append(m)
        return out