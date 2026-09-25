"""Flask app: serves the web UI and exposes the optimal /solve API.

Endpoints:
- GET /                  -> index.html
- GET /simulation.js     -> the browser-side simulation controller
- GET /style.css         -> stylesheet
- GET /solve?scramble=R U R' U2 ...&algo=BFS -> JSON { scramble, solution,
  length, nodes, algorithm, bfs_length, optimal, found, terminated, reason }
  ``algo`` selects which solver runs: "physical" (default; BFS + exact-h IDA*)
  or one of the nine DAA algorithms (BFS, DFS, DLS, IDDFS, Bidirectional,
  Greedy, A*, Backtracking, Branch & Bound).  DAA algorithms run on the real
  8-corner physical state, so their solutions truly undo the cube on screen.
- GET /scramble?length=12 -> JSON { scramble } (random Python-side scramble)
- GET/POST /current-scramble -> JSON { scramble } — the scramble last entered
  in the 3D-page input (set by the page on Random/typing, polled by the DAA
  dashboard so both views study the same case).

The backend does not visualize; the browser does not solve.
"""

from __future__ import annotations

import os
import sys

from flask import Flask, jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from solver import bfs_solver as bfs
from solver import cube_state as cs
from solver import physical_solver as phys
from solver import scramble as scrambler

app = Flask(__name__)
_VALID_MOVES = set(cs.MOVES)

_ALGO_LABELS = {
    "BFS": "BFS (optimal)",
    "DFS": "DFS",
    "DLS": "Depth-Limited Search",
    "IDDFS": "IDDFS (optimal)",
    "Bidirectional": "Bidirectional (optimal)",
    "Greedy": "Greedy Best-First",
    "A*": "A* (admissible h)",
    "Backtracking": "Backtracking",
    "Branch & Bound": "Branch & Bound",
}


def _run_daa(alg_name: str, moves: list[str], depth_limit: int | None = None):
    """Run a DAA algorithm on the physical cube state; return SearchResult.

    The algorithm is fed a :class:`~daa.cube.physical.PhysicalCubeState`, so
    ``apply_move``/``is_solved``/``hash_state`` all operate on the real
    8-corner physical group -- not the canonical quotient -- and the returned
    solution really undoes the displayed scramble.

    Admissible heuristics (Greedy/A*/Branch & Bound) use the rotation-invariant
    canonical projection via :meth:`PhysicalCubeState.perm`/``.orient``.
    """
    from daa.algorithms.base import Limits
    from daa.benchmark.registry import run_algorithm
    from daa.cube.physical import PhysicalCubeState

    start = PhysicalCubeState.from_alg(moves)
    limits = Limits(max_depth=20, max_states=600_000, max_time_s=20.0)
    # Informed algorithms (A*, Greedy, Branch & Bound) use the *exact* BFS
    # distance as their admissible heuristic — the same h the physical IDA*
    # solver uses — so they keep solving deep scrambles that the weak
    # ``corners / 4`` bound cannot reach within the 20 s web budget.
    is_informed = alg_name in ("A*", "Greedy", "Branch & Bound")
    return run_algorithm(
        alg_name,
        start,
        limits=limits,
        heuristic_name="BFS distance (exact)" if is_informed else None,
        depth_limit=depth_limit,
    ), start

_FRONTEND_FILES = {"index.html", "simulation.js", "style.css"}

# Latest scramble shown in the 3D-page input; polled by the DAA dashboard so a
# Random click (or manual typing) there drives the study's Solve & Compare.
_CURRENT_SCRAMBLE = ""


def parse_scramble(text: str):
    """Split whitespace notation into a validated list of moves."""
    tokens = text.split()
    for token in tokens:
        if token not in _VALID_MOVES:
            raise ValueError(f"unknown move: {token!r}")
    return tokens


@app.get("/")
def index():
    resp = send_from_directory(HERE, "index.html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/<path:filename>")
def frontend_file(filename: str):
    # Serve only the small whitelist of frontend assets (no path traversal).
    if filename not in _FRONTEND_FILES or os.path.normpath(filename) != filename:
        return jsonify(error="not found"), 404
    resp = send_from_directory(HERE, filename)
    # Never let the browser keep a stale copy of the UI/controller; the page
    # is always tiny and the dev cycle re-loads it often.
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/solve")
def solve():
    text = request.args.get("scramble", "")
    algo = request.args.get("algo", "") or "physical"
    depth_arg = request.args.get("depth", "")
    try:
        moves = parse_scramble(text)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    state = cs.apply_physical_alg(cs.PHYS_SOLVED, moves)
    expected = bfs.bfs_distance(cs.canonical7(state))

    if algo == "physical":
        import time as _time
        stats = {}
        # Physical solver in cubing's own move basis: the returned moves undo
        # the cube the <twisty-player> displays.  h = exact BFS distance of the
        # canonical representative (admissible); IDA* guarantees optimality.
        t0 = _time.perf_counter()
        solution = phys.solve(state, stats=stats)[0]
        return jsonify(
            scramble=" ".join(moves),
            solution=" ".join(solution),
            length=len(solution),
            nodes=stats["nodes"],
            bounds=stats["bounds_seq"],
            algorithm="BFS + IDA* (physical, optimal)",
            bfs_length=expected,
            optimal=len(solution) == expected,
            found=True,
            terminated=False,
            reason=None,
            time_s=round(_time.perf_counter() - t0, 4),
        )

    # One of the nine DAA algorithms, run on the REAL physical cube state.
    from daa.benchmark.registry import ALGORITHMS

    if algo not in ALGORITHMS:
        return jsonify(error=f"unknown algo: {algo!r}"), 400

    depth_limit = None
    if depth_arg:
        try:
            depth_limit = int(depth_arg)
        except ValueError:
            return jsonify(error="depth must be an integer"), 400

    result, start = _run_daa(algo, moves, depth_limit=depth_limit)

    # Physical correctness is a hard guarantee: the algorithm operated on the
    # 8-corner physical group, so its own found path must undo the cube.
    verify = start
    for m in result.solution:
        verify = verify.apply_move(m)
    physically_solved = result.found and verify.is_solved()

    label = _ALGO_LABELS.get(algo, algo)
    return jsonify(
        scramble=" ".join(moves),
        solution=" ".join(result.solution if physically_solved else []),
        length=len(result.solution) if physically_solved else 0,
        nodes=result.nodes_explored,
        bounds=[],
        algorithm=label,
        bfs_length=expected,
        optimal=physically_solved and len(result.solution) == expected,
        found=physically_solved,
        terminated=result.terminated and not physically_solved,
        reason=result.reason,
        time_s=round(result.execution_time, 4),
    )


@app.get("/current-scramble")
def get_current_scramble():
    return jsonify(scramble=_CURRENT_SCRAMBLE)


@app.post("/current-scramble")
def set_current_scramble():
    global _CURRENT_SCRAMBLE
    text = request.args.get("scramble", "")
    try:
        moves = parse_scramble(text)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    _CURRENT_SCRAMBLE = " ".join(moves)
    return jsonify(scramble=_CURRENT_SCRAMBLE)


@app.get("/scramble")
def scramble():
    text = request.args.get("length", "12")
    try:
        length = int(text)
    except ValueError:
        return jsonify(error="length must be an integer"), 400
    length = max(1, min(length, 40))
    moves = scrambler.generate_scramble(length=length)
    return jsonify(scramble=" ".join(moves))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)