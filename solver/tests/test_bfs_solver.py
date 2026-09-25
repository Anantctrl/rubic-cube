"""Tests for the BFS distance table and its encode/decode bijection."""

import random

import numpy as np
import pytest

from solver import bfs_solver as bfs
from solver import cube_state as cs


def _random_valid_state(rng):
    perm = list(range(7))
    rng.shuffle(perm)
    orient = [rng.randrange(3) for _ in range(7)]
    orient[6] = (-sum(orient[:6])) % 3
    return tuple(perm), tuple(orient)


def _random_scramble(rng, length):
    return [rng.choice(cs.MOVES) for _ in range(length)]


def test_encode_decode_roundtrip():
    rng = random.Random(0)
    for _ in range(2000):
        state = _random_valid_state(rng)
        code = bfs.encode(*state)
        assert 0 <= code < bfs.STATE_COUNT
        assert bfs.decode(code) == state


def test_encode_is_injective_on_sample():
    rng = random.Random(1)
    states = [_random_valid_state(rng) for _ in range(8000)]
    codes = [bfs.encode(*s) for s in states]
    # encode must be injective: distinct states never share a code
    assert len(set(codes)) == len(set(states))


def test_encode_rejects_invalid():
    with pytest.raises(ValueError):
        bfs.encode(tuple(range(7)), (1, 0, 0, 0, 0, 0, 0))  # sum 1 mod 3
    with pytest.raises(ValueError):
        bfs.encode((0, 1, 2, 3, 4, 5, 5), (0,) * 7)  # not a permutation


def test_decode_code_boundaries():
    assert bfs.decode(0) == cs.SOLVED
    assert bfs.decode(bfs.STATE_COUNT - 1)[0] == (6, 5, 4, 3, 2, 1, 0)


def test_table_shape_dtype_and_size():
    table = bfs.get_bfs_table()
    assert table.shape == (bfs.STATE_COUNT,)
    assert table.dtype == np.uint8
    assert (table == 255).sum() == 0  # every state filled
    assert (table == 0).sum() == 1    # only solved at distance 0


def test_table_max_is_god_number_11():
    table = bfs.get_bfs_table()
    assert int(table.max()) == 11


def test_scramble_distance_upper_bound():
    rng = random.Random(2)
    table = bfs.get_bfs_table()
    for _ in range(100):
        alg = _random_scramble(rng, rng.randrange(1, 12))
        state = cs.apply_alg(cs.SOLVED, alg)
        assert bfs.bfs_distance(state) <= len(alg)


def test_neighbor_distance_differs_by_at_most_one():
    rng = random.Random(3)
    for _ in range(500):
        alg = _random_scramble(rng, rng.randrange(1, 8))
        state = cs.apply_alg(cs.SOLVED, alg)
        d = bfs.bfs_distance(state)
        for move in cs.MOVES:
            assert abs(bfs.bfs_distance(cs.apply_move(state, move)) - d) <= 1