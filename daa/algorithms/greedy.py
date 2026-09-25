"""Greedy Best-First Search.

f(n) = h(n)   — the estimate *alone* guides the search, no accumulated cost.
This makes it fast to make progress but **not optimal**: a decent-looking
heuristic can chase a promising-but-long detour.  Compared to A* (f = g + h),
greedy ignores how many moves it already took, so it may return a longer
solution than necessary.  Perfect for the A* vs Greedy comparison table.
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
    result = SearchResult(algorithm="Greedy")
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
        # heap entries (h, seq, code, state, depth, parent_code, move)
        seq = 0
        open_heap: list = []
        g_score: dict[int, int] = {start.hash_state(): 0}
        parent: dict[int, tuple[int, str]] = {}
        closed: set = set()
        result.initial_h = h_of(start)
        result.nodes_explored = 0
        result.states_generated = 0
        result.duplicates = 0
        result.pruned = 0
        result.max_depth = 0
        guard = ExitGuard(limits)

        heapq.heappush(open_heap, (h_of(start), seq, start.hash_state(), start, 0, None, None))
        seq += 1

        while open_heap:
            _, _, code, node, depth, pcode, p_move = heapq.heappop(open_heap)
            if code in closed:
                result.duplicates += 1
                continue
            closed.add(code)
            if pcode is not None:
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
                if ccode in closed:
                    result.duplicates += 1
                    continue
                if ccode in g_score and g_score[ccode] <= depth + 1:
                    result.duplicates += 1
                    continue
                g_score[ccode] = depth + 1
                result.states_generated += 1
                heapq.heappush(
                    open_heap,
                    (h_of(child), seq, ccode, child, depth + 1, code, move),
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