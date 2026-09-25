"""A* Search.

    f(n) = g(n) + h(n)

- ``g(n)`` = cost from the initial state (number of moves so far),
- ``h(n)`` = admissible estimate of the remaining cost,
- ``f(n)`` = total estimated cost of a solution passing through ``n``.

With an **admissible** heuristic (never overestimates), A* is *optimal* — the
first time it pops the goal, that path is a shortest solution.  The "best
first" frontier (a priority queue keyed by f) expands promising states first,
so A* typically explores far fewer nodes than BFS while keeping BFS's
optimality guarantee.  This module also *re-opens* nodes found via a cheaper
path (strictly better g), which keeps optimality intact with non-consistent
heuristics.
"""

from __future__ import annotations

import heapq

from daa.algorithms.base import Limits, SearchResult
from daa.algorithms.util import ExitGuard, time_and_profile
from daa.optimization.pruning import MovePruner


def solve(
    start,
    limits: Limits | None = None,
    pruner: MovePruner | None = None,
    memoizer=None,
    heuristic_name: str | None = None,
) -> SearchResult:
    limits = limits or Limits()

    import daa.heuristics as H

    if heuristic_name is None or heuristic_name not in H.HEURISTICS:
        heuristic_name = H.default()
    heuristic = H.HEURISTICS[heuristic_name]
    pruner = pruner or MovePruner()
    result = SearchResult(algorithm="A*")
    result.heuristic = heuristic.name

    if start.is_solved():
        _, elapsed, mem = time_and_profile(lambda: None)
        result.execution_time, result.memory_bytes = elapsed, mem
        result.found = True
        result.initial_h = heuristic.fn(start)
        return result

    h_of = heuristic.fn
    if memoizer is not None:
        h_of = memoizer

    def _search():
        # heap entries: (f, g, seq, code, state, depth, parent_code, parent_move)
        seq = 0
        open_heap: list = []
        g_best: dict[int, int] = {start.hash_state(): 0}
        parent: dict[int, tuple[int, str]] = {}
        result.initial_h = h_of(start)
        result.nodes_explored = 0
        result.states_generated = 0
        result.duplicates = 0
        result.pruned = 0
        result.max_depth = 0
        guard = ExitGuard(limits)

        heapq.heappush(
            open_heap,
            (h_of(start), 0, seq, start.hash_state(), start, 0, None, None),
        )
        seq += 1

        while open_heap:
            f, g, _, code, node, depth, pcode, p_move = heapq.heappop(open_heap)
            if g_best.get(code, float("inf")) < g:
                # stale entry — a cheaper path to this node was already found
                result.duplicates += 1
                continue
            if pcode is not None and code not in parent:
                parent[code] = (pcode, p_move)  # type: ignore[assignment]
            result.nodes_explored += 1
            if depth > result.max_depth:
                result.max_depth = depth

            if node.is_solved() and node != start:
                path: list[str] = []
                while code in parent:
                    p, mv = parent[code]
                    path.append(mv)
                    code = p
                path.reverse()
                result.found = True
                result.solution = path
                result.length = len(path)
                return

            for move in pruner.allowed_moves(p_move):
                child = node.apply_move(move)
                ccode = child.hash_state()
                ng = g + 1
                if g_best.get(ccode, float("inf")) <= ng:
                    result.duplicates += 1
                    continue
                g_best[ccode] = ng
                result.states_generated += 1
                heapq.heappush(
                    open_heap,
                    (ng + h_of(child), ng, seq, ccode, child, depth + 1, code, move),
                )
                seq += 1
                stop, reason = guard.tick()
                if stop:
                    result.terminated = True
                    result.reason = reason
                    return

        result.terminated = True
        result.reason = "search exhausted without reaching solved"

    _, elapsed, mem = time_and_profile(_search)
    result.execution_time = elapsed
    result.memory_bytes = mem
    if memoizer is not None:
        result.memo_hits = memoizer.hits
        result.memo_misses = memoizer.misses
    return result