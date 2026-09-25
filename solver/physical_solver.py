"""Physical optimal solver in the 8-corner cubing.js basis.

Moves are cubing's own 2x2x2 KPuzzle turns (the same actions <twisty-player>
applies), so the returned solution genuinely undoes the scrambled cube.  The
7-corner BFS table gives an admissible, near-exact heuristic for the physical
space: ``h(state8) = bfs_distance(canonical7(state8))`` -- rotation-quotient
distance is a lower bound because every physical move induces a canonical move
of the same length.

Algorithm: a fast greedy exact-h descent (follows moves that drop h by exactly
1) usually walks most of the way, then a provably-optimal plain IDA* from the
original state (admissible h, bounds raised from ``h(start)``, per-iteration
transposition cut) guarantees the solution.
"""

from __future__ import annotations

from solver import bfs_solver as bfs
from solver import cube_state as cs

# Lexicographic smallest move first keeps solutions deterministic.
MOVE_ORDER = tuple(sorted(cs.MOVES))


def _expand(cur, prev):
    """Yield (move, child) for candidate moves from ``cur`` (smallest first)."""
    for move in MOVE_ORDER:
        if prev is not None and (move == cs.inverse(prev) or move[0] == prev[0]):
            continue
        yield move, cs.apply_physical(cur, move)


def heuristic(state8) -> int:
    """Admissible cost-to-solved: BFS distance of the canonical representative."""
    return bfs.bfs_distance(cs.canonical7(state8))


def _greedy(state8, stats):
    """Exact-h descent; returns (path, final_state, reached_solved_bool)."""
    path = []
    cur = state8
    prev = None
    while not cs.is_solved_physical(cur):
        h_cur = heuristic(cur)
        stats["nodes"] += 1
        best = None
        for move, child in _expand(cur, prev):
            hc = heuristic(child)
            stats["nodes"] += 1
            if hc == h_cur - 1:
                best = best or (move, child, hc)
        if best is None:
            break
        move, cur, _ = best
        path.append(move)
        prev = move
    return path, cur, cs.is_solved_physical(cur)


def _ida(state8, h_start, stats):
    """Plain IDA* from ``state8``; returns (path, last_bound)."""
    solution = None
    for bound in range(h_start, h_start + 32):
        seen = {}
        stats["bounds_seq"].append(bound)

        def search(s, g, path):
            h = heuristic(s)
            stats["nodes"] += 1
            if g + h > bound:
                return None
            if cs.is_solved_physical(s):
                return path
            key = (s[0], s[1])
            if seen.get(key, 1 << 30) <= g:
                return None
            seen[key] = g
            prev = path[-1] if path else None
            for move in MOVE_ORDER:
                if prev is not None and (
                    move == cs.inverse(prev) or move[0] == prev[0]
                ):
                    continue
                child = cs.apply_physical(s, move)
                found = search(child, g + 1, path + [move])
                if found is not None:
                    return found
            return None

        res = search(state8, 0, [])
        if res is not None:
            solution = res
            break
    if solution is None:
        raise RuntimeError("IDA* failed to find a solution")
    return solution, bound


def solve(state8, stats=None):
    """Return ``(solution, stats)`` -- an optimal physical solution.

    ``stats`` accumulates ``nodes`` (heuristic evaluations) and
    ``bounds_seq`` (tried bounds, mirroring the original contract: the first
    entry is the admissible heuristic of the start state, the last is the
    optimal length).
    """
    stats = stats if stats is not None else {}
    stats.setdefault("nodes", 0)
    stats.setdefault("bounds_seq", [])

    if cs.is_solved_physical(state8):
        stats["bounds_seq"] = stats["bounds_seq"] or [0]
        return [], stats

    h_start = heuristic(state8)
    stats["nodes"] += 1
    stats["bounds_seq"].append(h_start)

    path, _cur, solved = _greedy(state8, stats)
    if solved:
        return path, stats

    path, _ = _ida(state8, h_start, stats)
    return path, stats