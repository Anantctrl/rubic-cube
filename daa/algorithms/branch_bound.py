"""Branch and Bound search.

Maintains the **best solution found so far** (an upper bound ``U``).  For
every branch compute a lower bound ``g(state) + h(state)`` — the cost already
spent plus an admissible estimate of the remainder:

    if  current_cost + lower_bound  >=  best_solution:  prune branch

Branches that cannot possibly beat the incumbent are discarded ("bounding").
Here ``U`` starts at +infinity and the first complete solution (found via the
guided DFS order) becomes the incumbent; the search then continues until it
proves no better solution exists — so with enough budget B&B returns the
**optimal** solution, while reporting exactly how much was pruned.
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
    heuristic_name: str | None = None,
) -> SearchResult:
    limits = limits or Limits()

    import daa.heuristics as H

    if heuristic_name is None or heuristic_name not in H.HEURISTICS:
        heuristic_name = H.default()
    heuristic = H.HEURISTICS[heuristic_name]
    pruner = pruner or MovePruner()
    result = SearchResult(algorithm="Branch & Bound")
    result.heuristic = heuristic.name

    if start.is_solved():
        _, elapsed, mem = time_and_profile(lambda: None)
        result.execution_time, result.memory_bytes = elapsed, mem
        result.found = True
        result.lower_bound = heuristic.fn(start)
        return result

    h_of = heuristic.fn
    if memoizer is not None:
        h_of = memoizer

    def _search():
        guard = ExitGuard(limits)
        result.branches_explored = 0
        result.branches_pruned = 0
        result.nodes_explored = 0
        result.states_generated = 0
        result.pruned = 0
        result.max_depth = 0
        result.lower_bound = h_of(start)

        # Constructive incumbent: B&B is only "bounding" once it has a first
        # solution to beat.  Raw DFS may not reach the goal within the budget on
        # deep states, so seed an initial upper bound with a cheap greedy descent
        # using the same heuristic.  The walk scans ALL 18 face turns (no
        # pruner/visited restrictions).  A canonical-projection heuristic can
        # read 0 on a state that is a whole-cube rotation of the labelled goal
        # but not literally solved (e.g. on the physical group); the walk closes
        # that tiny gap with a bounded BFS so the seed is always a genuine
        # solution.  With a weak heuristic the walk simply stops when h no
        # longer improves, and the search falls back to plain DFS as before.
        def _close_gap(node, max_steps: int = 4):
            """Short bounded BFS from ``node`` to the literal goal (or None)."""
            from collections import deque

            seen = {node.hash_state()}
            dq = deque([(node, [])])
            while dq:
                n, path = dq.popleft()
                if len(path) >= max_steps:
                    continue
                for mv in pruner.allowed_moves(path[-1] if path else None):
                    ch = n.apply_move(mv)
                    if ch.hash_state() in seen:
                        continue
                    npath = path + [mv]
                    if ch.is_solved():
                        return npath
                    seen.add(ch.hash_state())
                    dq.append((ch, npath))
            return None

        cur, seed_path = start, []
        best = None
        HUGE = float("inf")
        for _ in range(min(limits.max_depth, 16)):
            if cur.is_solved():
                best = list(seed_path)
                break
            cur_h = h_of(cur)
            if cur_h <= 0:
                compl = _close_gap(cur)
                if compl is not None:
                    best = seed_path + compl
                break
            pick_h, pick_move = HUGE, None
            for move in pruner.allowed_moves(None):  # all 18 face turns
                hv = h_of(cur.apply_move(move))
                if hv < pick_h:
                    pick_h, pick_move = hv, move
            if pick_move is None or pick_h >= cur_h:
                break
            cur = cur.apply_move(pick_move)
            seed_path.append(pick_move)
        best: list[str] | None = best  # incumbent (upper bound U)
        result.branches_explored = 0
        result.branches_pruned = 0
        result.nodes_explored = 0
        result.states_generated = 0
        result.pruned = 0
        result.max_depth = 0
        result.lower_bound = h_of(start)

        # stack: (state, path, depth, cost_so_far)
        stack: list[tuple] = [(start, [], 0, 0)]
        while stack:
            node, path, depth, cost = stack.pop()
            result.nodes_explored += 1
            result.branches_explored += 1
            if depth > result.max_depth:
                result.max_depth = depth

            lb = cost + h_of(node)
            if best is not None and lb >= len(best):
                # cannot beat the incumbent: prune this whole subtree
                result.branches_pruned += 1
                result.pruned += 1
                continue

            if node.is_solved():
                if best is None or len(path) < len(best):
                    best = list(path)
                # do not return: search on to prove optimality (bounding)
                continue

            if depth >= limits.max_depth:
                result.branches_pruned += 1
                continue

            last_move = path[-1] if path else None
            for move in pruner.allowed_moves(last_move):
                child = node.apply_move(move)
                result.states_generated += 1
                stack.append((child, path + [move], depth + 1, cost + 1))
                stop, reason = guard.tick()
                if stop:
                    result.terminated = True
                    result.reason = reason
                    if best:
                        result.found = True
                        result.solution = best
                        result.length = len(best)
                        result.best_solution = best
                    return

        if best is not None:
            result.found = True
            result.solution = best
            result.length = len(best)
            result.best_solution = list(best)

    _, elapsed, mem = time_and_profile(_search)
    result.execution_time = elapsed
    result.memory_bytes = mem
    if memoizer is not None:
        result.memo_hits = memoizer.hits
        result.memo_misses = memoizer.misses
    return result