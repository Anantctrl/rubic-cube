"""IDDFS — Iterative Deepening Depth-First Search.

Runs DLS with ``depth_limit = 1, 2, 3, ...`` until a solution is found.

    Depth 1  -> search(depth_limit=1)
    Depth 2  -> search(depth_limit=2)  (re-explores depth 1 from scratch)
    ...
    Depth L  -> solution

This restores DFS's O(b·d) memory while giving BFS's *optimality* (guaranteed
shortest solution), at the cost of re-exploring earlier depth layers — the
classic space/time trade-off, reported per-iteration in ``result.iterations``.
"""

from __future__ import annotations

from daa.algorithms.base import Limits, SearchResult
from daa.algorithms import dls
from daa.optimization.pruning import MovePruner


def solve(
    start,
    limits: Limits | None = None,
    pruner: MovePruner | None = None,
    memoizer=None,
) -> SearchResult:
    limits = limits or Limits()
    pruner = pruner or MovePruner()
    result = SearchResult(algorithm="IDDFS")
    max_d = limits.max_depth
    result.iterations = []

    for depth in range(0, max_d + 1):
        iter_result = dls.solve(start, depth_limit=depth, limits=limits, pruner=pruner)
        result.iterations.append(
            {
                "depth": depth,
                "found": iter_result.found,
                "nodes": iter_result.nodes_explored,
                "generated": iter_result.states_generated,
                "duplicates": iter_result.duplicates,
                "time_s": round(iter_result.execution_time, 6),
            }
        )
        # accumulate across iterations (IDDFS explores each depth anew)
        result.nodes_explored += iter_result.nodes_explored
        result.states_generated += iter_result.states_generated
        result.duplicates += iter_result.duplicates
        result.pruned += iter_result.pruned
        result.execution_time += iter_result.execution_time
        result.memory_bytes = max(result.memory_bytes, iter_result.memory_bytes)
        result.max_depth = max(result.max_depth, iter_result.max_depth)

        if iter_result.found:
            result.found = True
            result.solution = iter_result.solution
            result.length = iter_result.length
            result.terminated = iter_result.terminated
            result.reason = iter_result.reason
            if result.execution_time == 0:
                result.execution_time = iter_result.execution_time
            return result

        if iter_result.terminated:
            # a single depth run blew the budget; no point continuing deeper.
            result.terminated = True
            result.reason = iter_result.reason
            return result

    result.terminated = True
    result.reason = "depth limit reached without finding a solution"
    return result