"""Algorithm registry: name -> solver callable with consistent signature.

Each registered solver accepts:
    solve(start, limits=..., pruner=..., memoizer=..., heuristic_name=...)
and returns a :class:`~daa.algorithms.base.SearchResult`.

``backend`` param is accepted (and ignored) by every entry so the UI can pass
an optional "which server computed this" handle without special-casing.
"""

from __future__ import annotations

from daa.algorithms import (
    astar,
    backtracking,
    bfs,
    bidirectional,
    branch_bound,
    dfs,
    dls,
    greedy,
    iddfs,
)
from daa.algorithms.base import Limits, SearchResult


def _id(x):
    return x


ALGORITHMS: dict[str, dict] = {
    "BFS": {
        "label": "BFS",
        "solver": bfs.solve,
        "needs_heuristic": False,
        "short": "Queue-based level-order search; optimal, O(b^d) memory.",
    },
    "DFS": {
        "label": "DFS",
        "solver": dfs.solve,
        "needs_heuristic": False,
        "short": "Stack-based depth-first; memory-light, not optimal.",
    },
    "DLS": {
        "label": "Depth-Limited Search",
        "solver": lambda start, limits=None, pruner=None, memoizer=None, heuristic_name=None, depth_limit=None: dls.solve(
            start, depth_limit=depth_limit if depth_limit is not None else (limits.max_depth if limits else 4), limits=limits, pruner=pruner
        ),
        "needs_heuristic": False,
        "short": "DFS bounded to a fixed depth limit.",
    },
    "IDDFS": {
        "label": "IDDFS",
        "solver": iddfs.solve,
        "needs_heuristic": False,
        "short": "Iterative deepening DLS: optimal like BFS, small memory.",
    },
    "Bidirectional": {
        "label": "Bidirectional Search",
        "solver": bidirectional.solve,
        "needs_heuristic": False,
        "short": "Two BFS frontiers meeting in the middle.",
    },
    "Greedy": {
        "label": "Greedy Best-First",
        "solver": greedy.solve,
        "needs_heuristic": True,
        "short": "f(n)=h(n); fast but not optimal.",
    },
    "A*": {
        "label": "A*",
        "solver": astar.solve,
        "needs_heuristic": True,
        "short": "f(n)=g(n)+h(n); optimal with admissible h.",
    },
    "Backtracking": {
        "label": "Backtracking",
        "solver": backtracking.solve,
        "needs_heuristic": False,
        "short": "Recursive try/undo; first solution wins.",
    },
    "Branch & Bound": {
        "label": "Branch and Bound",
        "solver": branch_bound.solve,
        "needs_heuristic": True,
        "short": "Prune branches whose lower bound can't beat the incumbent.",
    },
}


def available() -> list[str]:
    return list(ALGORITHMS.keys())


def run_algorithm(
    alg_name: str,
    start,
    limits: Limits | None = None,
    pruner=None,
    memoizer=None,
    heuristic_name: str | None = None,
    depth_limit: int | None = None,
) -> SearchResult:
    """Dispatch ``alg_name`` to its solver with a uniform signature.

    Solvers accept a slightly different keyword set (only informed algorithms
    take ``heuristic_name``, only DLS takes ``depth_limit``); we pass exactly
    the keywords each solver declares.
    """
    import inspect

    entry = ALGORITHMS[alg_name]
    if entry["needs_heuristic"] and not heuristic_name:
        import daa.heuristics as H

        heuristic_name = H.default()

    solver = entry["solver"]
    accepted = set(inspect.signature(solver).parameters)
    kwargs = {
        "start": start,
        "limits": limits,
        "pruner": pruner,
        "memoizer": memoizer,
    }
    if "heuristic_name" in accepted:
        kwargs["heuristic_name"] = heuristic_name
    if "depth_limit" in accepted and depth_limit is not None:
        kwargs["depth_limit"] = depth_limit
    return solver(**kwargs)


def run_algorithm_by_label(label: str, *args, **kwargs) -> SearchResult:
    for name, entry in ALGORITHMS.items():
        if entry["label"] == label:
            return run_algorithm(name, *args, **kwargs)
    raise KeyError(f"no algorithm labelled {label!r}")