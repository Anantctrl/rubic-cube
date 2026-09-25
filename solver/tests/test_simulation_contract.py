"""End-to-end contract tests for the Flask API.

Uses Flask's test client (no live server).  Checks the exact /solve JSON
schema from the plan (scramble + solution strings, bounds = tried-bound
sequence), optimality vs the BFS distance, legal moves, the independent
verifier's postcondition (scramble + solution -> solved), and the /scramble
endpoint.
"""

from __future__ import annotations

import os
import sys
import random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
VIZ = os.path.join(PROJECT_ROOT, "viz")
if VIZ not in sys.path:
    sys.path.insert(0, VIZ)

# Import AFTER the sys.path setup (app.py inserts PROJECT_ROOT itself).
import app as viz_app  # noqa: E402
from solver import bfs_solver as bfs  # noqa: E402
from solver import cube_state as cs  # noqa: E402
from solver import scramble as scrambler  # noqa: E402
# solver/tests is not a package; pytest puts this directory on sys.path.
from test_verifier import verifies  # noqa: E402

client = viz_app.app.test_client()

_EXPECTED_KEYS = {
    "scramble",
    "solution",
    "length",
    "nodes",
    "bounds",
    "bfs_length",
    "optimal",
    "algorithm",
    "found",
    "terminated",
    "reason",
    "time_s",
}


def _solve(scramble_text):
    return client.get("/solve?scramble=" + scramble_text)


def test_solve_schema_valid_scramble():
    r = _solve("R U R' U'")
    assert r.status_code == 200
    data = r.get_json()
    assert set(data) == _EXPECTED_KEYS, data
    assert data["scramble"] == "R U R' U'"
    assert isinstance(data["solution"], str)
    assert data["solution"].split()  # non-empty
    assert data["length"] >= data["bfs_length"]
    assert data["optimal"] is (data["length"] == data["bfs_length"])
    assert data["nodes"] > 0
    # bounds: admissible start heuristic, then the tried bounds ending at length
    assert isinstance(data["bounds"], list)
    assert data["bounds"][0] == data["bfs_length"]
    assert data["bounds"][-1] == data["length"]
    assert all(isinstance(b, int) for b in data["bounds"])


def test_solve_solution_uses_only_valid_moves_and_solves():
    r = _solve("F R U2 B' D R' F2 L'")
    assert r.status_code == 200
    data = r.get_json()
    solution = data["solution"].split()
    for move in solution:
        assert move in cs.MOVES
    assert verifies(data["scramble"].split(), solution)


def test_solve_user_supplied_arbitrary_scrambles():
    """Manual scrambles (the user's primary workflow) always solve back."""
    rng = random.Random(31)
    for _ in range(20):
        scrambles = scrambler.generate_scramble(rng, length=rng.randrange(2, 20))
        data = _solve(" ".join(scrambles)).get_json()
        assert data["length"] >= data["bfs_length"]
        assert verifies(scrambles, data["solution"].split())


def test_solve_invalid_move_400():
    r = _solve("Q")
    assert r.status_code == 400
    body = r.get_json()
    assert "error" in body


def test_solve_empty_scramble_solved_trivially():
    r = _solve("")
    assert r.status_code == 200
    data = r.get_json()
    assert data["length"] == 0
    assert data["bfs_length"] == 0
    assert data["solution"] == ""
    assert data["optimal"] is True


def test_solve_depth_categories_verified():
    """Depth-0..11 scrambles: /solve returns physical solutions back to solved.

    The scrambler guarantees the canonical-model trajectory has the target
    distance; the raw physical accumulation differs by rotation residue, so
    /solve's own ``bfs_length`` is checked for admissibility only.
    """
    rng = random.Random(17)
    for distance in (0, 1, 2, 4, 6, 8, 10, 11):
        scramble = scrambler.scramble_with_distance(distance, rng)
        # scrambler invariant (canonical model)
        model = cs.apply_alg(cs.SOLVED, scramble)
        assert bfs.bfs_distance(model) == distance, (distance, scramble)
        data = _solve(" ".join(scramble)).get_json()
        assert data["length"] >= data["bfs_length"], (distance, scramble, data)
        assert data["optimal"] is (data["length"] == data["bfs_length"])
        assert verifies(scramble, data["solution"].split())


def test_scramble_endpoint_default_length_and_wellformed():
    r = client.get("/scramble")
    assert r.status_code == 200
    moves = r.get_json()["scramble"].split()
    assert len(moves) == 12
    for i, move in enumerate(moves):
        assert move in cs.MOVES
        if i > 0:
            assert moves[i][0] != moves[i - 1][0]


def test_scramble_endpoint_custom_length():
    r = client.get("/scramble?length=8")
    assert r.status_code == 200
    assert len(r.get_json()["scramble"].split()) == 8


def test_scramble_endpoint_clamps_and_rejects():
    assert len(client.get("/scramble?length=999").get_json()["scramble"].split()) == 40
    assert len(client.get("/scramble?length=0").get_json()["scramble"].split()) == 1
    assert client.get("/scramble?length=abc").status_code == 400


def test_current_scramble_defaults_empty():
    assert client.get("/current-scramble").get_json() == {"scramble": ""}


def test_current_scramble_roundtrip_normalized():
    r = client.post("/current-scramble?scramble=R%20U%20R'%20U2")
    assert r.status_code == 200
    assert r.get_json() == {"scramble": "R U R' U2"}
    assert client.get("/current-scramble").get_json() == {"scramble": "R U R' U2"}


def test_current_scramble_rejects_invalid_and_keeps_last():
    client.post("/current-scramble?scramble=L2%20B")
    assert client.post("/current-scramble?scramble=Q").status_code == 400
    assert client.get("/current-scramble").get_json() == {"scramble": "L2 B"}