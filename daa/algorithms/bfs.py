"""BFS — Breadth First Search (shortest path in the implicit graph).

Data structure: FIFO ``collections.deque``.
Textbook property: **complete** and **optimal for equal-cost edges** (every
move costs exactly 1), at the price of O(b^d) memory.

The cube graph's edges are symmetric, so we reuse ``UB``/``LB`` safely; the
parent map is a dict keyed by the state's collision-free integer code.
"""

from __future__ import annotations

from collections import deque

from daa.algorithms.base import Limits, SearchResult
from daa.algorithms.util import ExitGuard, time_and_profile
from daa.optimization.pruning import MovePruner


def solve(
    start,
    limits: Limits | None = None,
    pruner: MovePruner | None = None,
    memoizer=None,
) -> SearchResult:
    limits = limits or Limits()
    pruner = pruner or MovePruner()

    guard = ExitGuard(limits)
    target_code = start.solved().hash_state()

    # dedup via a set of integer codes (fast, memory-tight)
    visited: set[int] = set()
    result = SearchResult(algorithm="BFS")

    if start.is_solved():

        def _empty():
            return None

        _, elapsed, mem = time_and_profile(_empty)
        result.execution_time = elapsed
        result.memory_bytes = mem
        result.found = True
        result.solution = []
        result.length = 0
        return result

    def _search():
        queue: deque = deque([(start, start.hash_state(), 0)])
        parent: dict[int, tuple[int, str]] = {}
        visited.add(start.hash_state())
        result.nodes_explored = 0
        result.states_generated = 0
        result.duplicates = 0
        result.pruned = 0
        result.max_depth = 0

        while queue:
            node, code, depth = queue.popleft()
            result.nodes_explored += 1
            if depth > result.max_depth:
                result.max_depth = depth

            last_move = parent.get(code, (None, None))[1]

            for move in pruner.allowed_moves(last_move):
                child = node.apply_move(move)
                ccode = child.hash_state()
                if ccode in visited:
                    result.duplicates += 1
                    continue
                visited.add(ccode)
                parent[ccode] = (code, move)
                result.states_generated += 1
                if ccode == target_code:
                    # reconstruct path child <- ... <- start
                    path: list[str] = []
                    cur = ccode
                    while cur in parent:
                        pcode, mv = parent[cur]
                        path.append(mv)
                        cur = pcode
                    path.reverse()
                    result.found = True
                    result.solution = path
                    result.length = len(path)
                    return
                queue.append((child, ccode, depth + 1))
                stop, reason = guard.tick()
                if stop:
                    result.terminated = True
                    result.reason = reason
                    return

        result.terminated = True
        result.reason = "exhausted search space (no solution found)"

    _, elapsed, mem = time_and_profile(_search)
    result.execution_time = elapsed
    result.memory_bytes = mem
    if memoizer is not None:
        result.memo_hits = memoizer.hits
        result.memo_misses = memoizer.misses
    return result