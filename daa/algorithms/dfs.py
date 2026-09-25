"""DFS — Depth First Search (stack-based; backtracking behaviour).

Data structure: LIFO stack (Python ``list``).
Textbook properties:
- **complete** on finite/implicit graphs with cycle-prevention
- **not optimal** — first solution found is usually NOT shortest
- memory O(b·d) — the advantage over BFS's O(b^d)

Backtracking is visible here: when deep branches hit ``max_depth`` or fail,
the algorithm *backs up* and tries the next branch.  Duplicate detection
(visited set keyed by integer code) prevents exponential revisits while still
illustrating DFS's depth-first shape.
"""

from __future__ import annotations

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
    target = start.solved()
    result = SearchResult(algorithm="DFS")
    visited: set[int] = set()

    if start.is_solved():
        _, elapsed, mem = time_and_profile(lambda: None)
        result.execution_time, result.memory_bytes = elapsed, mem
        result.found = True
        return result

    def _search():
        # stack holds (state, parent_code, move_used_to_reach, depth)
        stack: list[tuple] = [(start, None, None, 0)]
        parent: dict[int, tuple[int, str]] = {}
        visited.add(start.hash_state())
        result.nodes_explored = 0
        result.states_generated = 0
        result.duplicates = 0
        result.pruned = 0
        result.max_depth = 0

        while stack:
            node, pcode, p_move, depth = stack.pop()
            code = node.hash_state()
            if pcode is not None and code not in parent:
                parent[code] = (pcode, p_move)  # type: ignore[assignment]
            result.nodes_explored += 1
            if depth > result.max_depth:
                result.max_depth = depth

            if node.is_solved() and node != start:
                path: list[str] = []
                cur = code
                while cur in parent:
                    p, mv = parent[cur]
                    path.append(mv)
                    cur = p
                path.reverse()
                result.found = True
                result.solution = path
                result.length = len(path)
                return

            if depth >= limits.max_depth:
                result.pruned += 1
                continue

            for move in pruner.allowed_moves(p_move):
                child = node.apply_move(move)
                ccode = child.hash_state()
                if ccode in visited:
                    result.duplicates += 1
                    continue
                visited.add(ccode)
                result.states_generated += 1
                stack.append((child, code, move, depth + 1))
                stop, reason = guard.tick()
                if stop:
                    result.terminated = True
                    result.reason = reason
                    return

    _, elapsed, mem = time_and_profile(_search)
    result.execution_time = elapsed
    result.memory_bytes = mem
    if memoizer is not None:
        result.memo_hits = memoizer.hits
        result.memo_misses = memoizer.misses
    if not result.found and not result.terminated:
        result.terminated = True
        result.reason = "search space exhausted without reaching solved"
    return result