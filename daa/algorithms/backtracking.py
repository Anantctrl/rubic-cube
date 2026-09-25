"""Backtracking search.

Classic recursive generate-and-test:

    Choose Move -> Apply Move -> Recurse -> Solved? (yes: return / no: Undo
    Move -> Try Next Move)

Implemented iteratively (safety under many frames) but structured to mirror
the recursion: each stack frame is one recursive call, and when it completes
without a solution we "backtrack" (pop) and the loop tries the next sibling.

- ``recursive_calls``  = number of frames entered
- ``backtracks``       = number of times a branch was abandoned (dead end,
                         cycle, or resource limit)
- ``max_depth``        = deepest recursion level reached

Status: **complete** (explores the entire tree up to max_depth when unlimited),
**not optimal** — the first solution it stumbles on is returned as-is, which
is exactly what a student should observe and discuss for DFS-family methods.
"""

from __future__ import annotations

from dataclasses import field

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
    result = SearchResult(algorithm="Backtracking")
    result._recursive_calls = 0
    result._backtracks = 0

    if start.is_solved():
        _, elapsed, mem = time_and_profile(lambda: None)
        result.execution_time, result.memory_bytes = elapsed, mem
        result.found = True
        return result

    guard = ExitGuard(limits)

    def _search():
        # stack: (state, move_path, depth, on_branch_codes)
        stack: list[tuple] = [
            (start, [], 0, {start.hash_state()})
        ]
        result.nodes_explored = 0
        result.states_generated = 0
        result.pruned = 0
        result.max_depth = 0

        while stack:
            node, path, depth, branch_codes = stack.pop()
            result._recursive_calls += 1
            result.nodes_explored += 1
            if depth > result.max_depth:
                result.max_depth = depth

            if node.is_solved() and depth > 0:
                result.found = True
                result.solution = list(path)
                result.length = len(path)
                return

            if depth >= limits.max_depth:
                result.pruned += 1
                result._backtracks += 1
                continue

            last_move = path[-1] if path else None
            moves = pruner.allowed_moves(last_move)
            # push in reverse so we try the first allowed move next ("Try Next
            # Move" semantics) — matches DFS ordering.
            for move in reversed(moves):
                child = node.apply_move(move)
                ccode = child.hash_state()
                if ccode in branch_codes:
                    # undoing would create a cycle on this branch
                    result._backtracks += 1
                    result.duplicates += 1
                    continue
                result.states_generated += 1
                stack.append(
                    (
                        child,
                        path + [move],
                        depth + 1,
                        branch_codes | {ccode},
                    )
                )
                stop, reason = guard.tick()
                if stop:
                    result.terminated = True
                    result.reason = reason
                    return

            # frame completed without a solution: we backtrack to the parent.
            result._backtracks += 1

        result.terminated = True
        result.reason = "search space exhausted without finding a solution"

    _, elapsed, mem = time_and_profile(_search)
    result.execution_time = elapsed
    result.memory_bytes = mem
    if memoizer is not None:
        result.memo_hits = memoizer.hits
        result.memo_misses = memoizer.misses
    return result