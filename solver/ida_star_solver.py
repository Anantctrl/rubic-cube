"""IDA* optimal solver with admissible heuristic h(n) = ceil(m / 4).

``m`` is the number of corners not occupying their home slot (position only;
with the 8th corner fixed, piece ``i`` belongs in slot ``i``).  A quarter-turn
moves exactly four corners, so it can improve at most four misplaced corners
per move, which makes ``ceil(m / 4)`` admissible (never exceeds the true
distance).  Orientation is deliberately omitted — including it would only
over-estimate and break admissibility.

Branch-and-bound pruning: consecutive moves on the same face are skipped —
any two same-face moves collapse into one move (or cancel), so an optimal
solution never needs them, dropping the branching factor from 18 to 15.
"""

from __future__ import annotations

from solver import cube_state as cs

MOVES = cs.MOVES

_AXIS_OF = tuple(
    {"U": "y", "D": "y", "L": "x", "R": "x", "F": "z", "B": "z"}[m[0]] for m in MOVES
)


def heuristic(state) -> int:
    """Admissible position-only estimate: ceil(m/4), m = misplaced corners."""
    perm = state[0]
    m = sum(1 for i, piece in enumerate(perm) if piece != i)
    return (m + 3) // 4


def ida_star_solve(state, max_bound=11, stats=None, heuristic=heuristic):
    """Return an optimal move list (move names) for ``state``.

    ``stats``, if given, is a dict updated in place with ``nodes`` (heuristic
    evaluations), ``bounds`` (number of IDA* iterations tried) and
    ``bounds_seq`` (the concrete bound values tried, e.g. [4, 5, 6, 7]).

    ``heuristic`` is an admissible estimate function (default: the ceil(m/4)
    position bound above).  Callers may substitute the exact BFS distance
    table (also admissible) where solving must be instant at any distance.
    """
    if stats is None:
        stats = {}
    stats["nodes"] = 0
    stats["bounds"] = 0
    stats["bounds_seq"] = []

    def dfs(current, g, bound, last_direction):
        stats["nodes"] += 1
        if cs.is_solved(current):
            return True, []
        h = heuristic(current)
        if g + h > bound:
            return False, None
        for i, move in enumerate(MOVES):
            if last_direction is not None and _AXIS_OF[i] == last_direction:
                continue
            child = cs.apply_move(current, move)
            solved, path = dfs(child, g + 1, bound, _AXIS_OF[i])
            if solved:
                return True, [move] + path
        return False, None

    start_bound = heuristic(state)
    for bound in range(start_bound, max_bound + 1):
        stats["bounds"] += 1
        stats["bounds_seq"].append(bound)
        solved, path = dfs(state, 0, bound, None)
        if solved:
            return path
    raise RuntimeError(f"no solution up to depth {max_bound}")