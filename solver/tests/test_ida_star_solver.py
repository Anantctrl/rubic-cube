"""Tests for the IDA* solver: admissibility and optimality vs the BFS table."""

import random

from solver import bfs_solver as bfs
from solver import cube_state as cs
from solver import ida_star_solver as ida


def _random_scramble(rng, length):
    return [rng.choice(cs.MOVES) for _ in range(length)]


def test_heuristic_solved_is_zero():
    assert ida.heuristic(cs.SOLVED) == 0


def test_heuristic_of_single_turn():
    state = cs.apply_move(cs.SOLVED, "R")
    # R moves 4 corners, each to the wrong slot -> m = 4 -> ceil(4/4) = 1
    assert ida.heuristic(state) == 1


def test_heuristic_is_admissible_on_samples():
    rng = random.Random(4)
    for _ in range(300):
        alg = _random_scramble(rng, rng.randrange(1, 9))
        state = cs.apply_alg(cs.SOLVED, alg)
        assert ida.heuristic(state) <= bfs.bfs_distance(state)


def test_ida_solution_solves_state():
    rng = random.Random(5)
    for _ in range(20):
        alg = _random_scramble(rng, rng.randrange(1, 9))
        state = cs.apply_alg(cs.SOLVED, alg)
        solution = ida.ida_star_solve(state)
        assert cs.apply_alg(state, solution) == cs.SOLVED


def test_ida_len_matches_bfs_for_50_scrambles_depth_le_8():
    rng = random.Random(6)
    for _ in range(50):
        depth = rng.randrange(1, 9)
        alg = _random_scramble(rng, depth)
        state = cs.apply_alg(cs.SOLVED, alg)
        expected = bfs.bfs_distance(state)
        stats = {}
        solution = ida.ida_star_solve(state, stats=stats)
        assert len(solution) == expected
        assert stats["nodes"] >= expected


def test_bounds_seq_records_the_tried_bounds():
    # With the default ceil(m/4) heuristic, IDA* iterates every bound from
    # h(start) up to and including the optimal length: bounds_seq is that run.
    rng = random.Random(9)
    for _ in range(10):
        alg = _random_scramble(rng, rng.randrange(2, 9))
        state = cs.apply_alg(cs.SOLVED, alg)
        expected = bfs.bfs_distance(state)
        stats = {}
        ida.ida_star_solve(state, stats=stats)
        assert stats["bounds"] == len(stats["bounds_seq"])
        assert stats["bounds_seq"] == list(range(ida.heuristic(state), expected + 1))