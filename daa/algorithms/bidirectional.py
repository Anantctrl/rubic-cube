"""Bidirectional Search (bidirectional BFS, level-synchronized).

Two BFS runs race toward each other — one from the scrambled state, one from
the solved state (using *inverse* moves backwards from the goal) — and meet in
the middle.  The meeting node proves a start→meet→goal path of length
``f_dist(meet) + b_dist(meet)``.

Optimality:

  Frontiers are expanded **level by level** on both sides (frontier F explores
  forward distances 0..F, back frontier B explores 0..B).  After both sides are
  at levels (F, B), every node within forward distance ≤ F or backward distance
  ≤ B has been seen, so any *undiscovered* meeting node has f_dist ≥ F+1 AND
  b_dist ≥ B+1 — its path length is ≥ F+B+2.  The search therefore keeps the
  best (shortest) meeting found and stops as soon as ``best ≤ F+B+1``: no
  better solution can exist.  This makes the returned path guaranteed optimal
  (unlike a "first meet wins" implementation, whose result depends on the
  order the two fronts happen to collide).

Why it helps (the DAA point): BFS explores a ball of radius d around its start.
Two balls of radius d/2 cover what one full ball would, and a ball grows
exponentially with its radius — so meeting in the middle is dramatically
cheaper on deeply-scrambled states (exponential half vs. exponential full).
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
    goal = start.solved()
    result = SearchResult(algorithm="Bidirectional")

    if start.is_solved():
        _, elapsed, mem = time_and_profile(lambda: None)
        result.execution_time, result.memory_bytes = elapsed, mem
        result.found = True
        return result

    def _search():
        # predecessor maps: code -> (parent_code, move_from_parent_to_this)
        f_parent: dict[int, tuple[int, str] | None] = {start.hash_state(): None}
        b_parent: dict[int, tuple[int, str] | None] = {goal.hash_state(): None}
        # depth on each side, used for the optimality bound and meet lengths
        f_depth: dict[int, int] = {start.hash_state(): 0}
        b_depth: dict[int, int] = {goal.hash_state(): 0}

        f_level: list = [start]
        b_level: list = [goal]
        F = 0  # forward frontier fully expanded through depth F
        B = 0  # backward frontier fully expanded through depth B

        best_len: int | None = None
        best_meet: int | None = None  # meeting node code (in both depth maps)

        result.nodes_explored = 0
        result.states_generated = 0
        result.duplicates = 0
        result.pruned = 0
        result.max_depth = 0

        guard = ExitGuard(limits)

        def _record(cand_len: int, code: int) -> None:
            nonlocal best_len, best_meet
            if best_len is None or cand_len < best_len:
                best_len = cand_len
                best_meet = code

        def _expand_forward() -> bool:
            """Expand the forward frontier one level.  Returns False on budget."""
            nonlocal F
            next_level: list = []
            for node in f_level:
                node_code = node.hash_state()
                result.nodes_explored += 1
                parent = f_parent[node_code]
                last_move = parent[1] if parent else None
                for move in pruner.allowed_moves(last_move):
                    child = node.apply_move(move)
                    ccode = child.hash_state()
                    if ccode in f_parent:
                        result.duplicates += 1
                        continue
                    f_parent[ccode] = (node_code, move)
                    f_depth[ccode] = F + 1
                    result.states_generated += 1
                    if ccode in b_depth:
                        _record((F + 1) + b_depth[ccode], ccode)
                    next_level.append(child)
                    stop, reason = guard.tick()
                    if stop:
                        result.terminated = True
                        result.reason = reason
                        return False
            f_level.clear()
            f_level.extend(next_level)
            result.forward_states = len(f_parent)
            F += 1
            return True

        def _expand_backward() -> bool:
            """Expand the backward frontier one level.  Returns False on budget."""
            nonlocal B
            next_level: list = []
            for node in b_level:
                node_code = node.hash_state()
                result.nodes_explored += 1
                parent = b_parent[node_code]
                last_move = parent[1] if parent else None
                for move in pruner.allowed_moves(last_move):
                    # going backward = from the goal side we apply the inverse
                    child = node.apply_move(_inverse_of(move))
                    ccode = child.hash_state()
                    if ccode in b_parent:
                        result.duplicates += 1
                        continue
                    b_parent[ccode] = (node_code, move)  # move leads back to goal
                    b_depth[ccode] = B + 1
                    result.states_generated += 1
                    if ccode in f_depth:
                        cand = f_depth[ccode] + (B + 1)
                        # f_depth[ccode] is the CURRENT recorded forward depth,
                        # which may pre-date the latest forward expansion; the
                        # recorded depth is exact, so cand is the path length.
                        _record(cand, ccode)
                    next_level.append(child)
                    stop, reason = guard.tick()
                    if stop:
                        result.terminated = True
                        result.reason = reason
                        return False
            b_level.clear()
            b_level.extend(next_level)
            result.backward_states = len(b_parent)
            B += 1
            return True

        while f_level and b_level:
            if not _expand_forward() or not _expand_backward():
                return
            # both fronts are fully explored through (F, B): an undiscovered
            # meeting node needs f_dist >= F+1 and b_dist >= B+1, i.e. path
            # length >= F+B+2.  If the best found already meets that bound,
            # no better solution exists.
            if best_len is not None and best_len <= F + B + 1:
                break

        if best_meet is None:
            result.terminated = True
            result.reason = "state space exhausted before meeting"
            return

        _finish(result, f_parent, b_parent, best_meet, best_len)

    _, elapsed, mem = time_and_profile(_search)
    result.execution_time = elapsed
    result.memory_bytes = mem
    if memoizer is not None:
        result.memo_hits = memoizer.hits
        result.memo_misses = memoizer.misses
    if not result.found and not result.terminated:
        result.terminated = True
        result.reason = "state space exhausted before meeting"
    return result


def _inverse_of(move: str) -> str:
    if move.endswith("2"):
        return move
    return move[:-1] if move.endswith("'") else move + "'"


def _finish(result, f_parent, b_parent, meet_code: int, best_len: int) -> None:
    """Assemble start → meet → goal from the two predecessor chains."""
    f_path: list[str] = []
    cur = meet_code
    while f_parent.get(cur) is not None:
        p, mv = f_parent[cur]
        f_path.append(mv)
        cur = p
    f_path.reverse()

    b_path: list[str] = []
    cur = meet_code
    while b_parent.get(cur) is not None:
        p, mv = b_parent[cur]
        b_path.append(mv)
        cur = p

    result.found = True
    result.solution = f_path + b_path
    result.length = len(result.solution)
    result.meeting_depth = best_len
    result.forward_states = len(f_parent)
    result.backward_states = len(b_parent)