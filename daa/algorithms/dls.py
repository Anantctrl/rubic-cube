"""DLS — Depth-Limited Search.

A DFS that never expands nodes deeper than a user-chosen ``depth_limit``.
Demonstrates the *incompleteness* of a bounded search: if the goal lies beyond
the limit, DLS reports "not found at this depth" — even though a solution
exists.  This is the failure mode that IDDFS fixes by iterating the limit.
"""

from __future__ import annotations

from daa.algorithms.base import Limits, SearchResult
from daa.algorithms.util import ExitGuard, time_and_profile
from daa.optimization.pruning import MovePruner


def solve(
    start,
    depth_limit: int,
    limits: Limits | None = None,
    pruner: MovePruner | None = None,
    memoizer=None,
) -> SearchResult:
    limits = limits or Limits()
    pruner = pruner or MovePruner()
    guard = ExitGuard(limits)
    result = SearchResult(algorithm="DLS")
    # DLS is a *depth-limited tree search*: it must not use a global "visited"
    # set.  A global set is a different algorithm — under a depth limit a state
    # is often first met at a deep recurrence, its shallower occurrence is then
    # skipped, nearby goals are missed, and IDDFS stops returning optimal paths.
    # Instead we prevent cycles *along the current root path only* (O(depth)
    # memory), which is the textbook DLS and keeps DLS complete to the limit.

    if start.is_solved():
        _, elapsed, mem = time_and_profile(lambda: None)
        result.execution_time, result.memory_bytes = elapsed, mem
        result.found = True
        return result

    def _search():
        # frames: (node, move_used_to_reach, depth, exiting_flag)
        # ``path_moves`` is a live mirror of the current root->node path, so
        # the reported solution is *the actual moves along this branch* —
        # never a reassembled substitute.
        stack: list[tuple] = [(start, None, 0, False)]
        on_path: set[int] = {start.hash_state()}
        path_moves: list[str] = []
        result.nodes_explored = 0
        result.states_generated = 0
        result.duplicates = 0
        result.pruned = 0
        result.max_depth = 0
        result.iterations = []  # not used by DLS; kept for interface symmetry

        while stack:
            node, move_in, depth, exiting = stack.pop()

            if exiting:
                if move_in is not None:
                    path_moves.pop()
                on_path.discard(node.hash_state())
                continue

            if move_in is not None:
                path_moves.append(move_in)
            result.nodes_explored += 1
            if depth > result.max_depth:
                result.max_depth = depth

            if node.is_solved() and depth > 0:
                result.found = True
                result.solution = path_moves.copy()
                result.length = len(path_moves)
                return

            if depth >= depth_limit:
                # at the edge of the allowed depth: this branch is a dead end
                # for this limit, so prune it (this is DLS's incompleteness).
                result.pruned += 1
                if move_in is not None:
                    path_moves.pop()
                on_path.discard(node.hash_state())
                continue

            # schedule the "exit" frame *below* the children so that this state
            # is released from the path only after the whole subtree finished.
            stack.append((node, move_in, depth, True))
            for move in pruner.allowed_moves(move_in):
                child = node.apply_move(move)
                ccode = child.hash_state()
                if ccode in on_path:
                    result.duplicates += 1
                    continue
                on_path.add(ccode)
                result.states_generated += 1
                stack.append((child, move, depth + 1, False))
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
        # reached the depth limit without finding a solution: incomplete.
        result.reason = f"no solution within depth {depth_limit}"
        # keep terminated=False so the UI can distinguish 'incomplete at L'
        # from 'resource-exhausted' — see IDDFS which relies on this signal.
    return result