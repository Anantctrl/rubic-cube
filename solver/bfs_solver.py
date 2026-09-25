"""BFS full-graph precomputation: distance-to-solved for every canonical state.

A single breadth-first search from the solved state fills a ``numpy.uint8``
table indexed by a bijective ``encode(perm, orient) -> int`` over all
``7! * 3**6 = 3,674,160`` reachable states.  Optimal distance is O(1) per query.
"""

from __future__ import annotations

import os

import numpy as np

from solver import cube_state as cs

STATE_COUNT = 5040 * 3**6  # 3,674,160

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "bfs_table.npy")

# Lehmer-code factorials for mixed-radix ranks of the 7-element permutation.
_FACT = (1, 1, 2, 6, 24, 120, 720, 5040)

_ORIENT_DIGITS = 6  # o[0..5] are free; o[6] = -(sum o[0..5]) mod 3.
_ORIENT_BASE = 3**_ORIENT_DIGITS  # 729


def encode(perm, orient) -> int:
    """Bijective code for a canonical state into ``[0, STATE_COUNT)``.

    Validates that ``perm`` is a permutation of ``0..6`` and that the
    reachability constraint ``sum(orient) % 3 == 0`` holds (piece 7's twist is 0
    in the canonical frame, so the full 8-corner sum is the 7-corner sum here).
    """
    if sorted(perm) != list(range(7)):
        raise ValueError(f"permutation must be a permutation of 0..6, got {perm!r}")
    if sum(orient) % 3:
        raise ValueError(f"orientation sum must be 0 mod 3, got {orient!r}")

    perm_rank = 0
    for i in range(7):
        smaller = 0
        pi = perm[i]
        for j in range(i + 1, 7):
            if perm[j] < pi:
                smaller += 1
        perm_rank += smaller * _FACT[6 - i]

    orient_code = 0
    for i in range(_ORIENT_DIGITS):
        orient_code += orient[i] * (3**i)

    return perm_rank * _ORIENT_BASE + orient_code


def _encode_fast(perm, orient) -> int:
    """Unchecked variant for hot loops inside the BFS build."""
    perm_rank = 0
    for i in range(7):
        smaller = 0
        pi = perm[i]
        for j in range(i + 1, 7):
            if perm[j] < pi:
                smaller += 1
        perm_rank += smaller * _FACT[6 - i]
    orient_code = 0
    for i in range(_ORIENT_DIGITS):
        orient_code += orient[i] * (3**i)
    return perm_rank * _ORIENT_BASE + orient_code


def decode(code: int):
    """Invert :func:`encode` for ``code`` in ``[0, STATE_COUNT)``."""
    if not 0 <= code < STATE_COUNT:
        raise ValueError(f"code out of range: {code}")
    perm_rank, orient_code = divmod(code, _ORIENT_BASE)

    perm = []
    remaining = list(range(7))
    for i in range(7):
        digit = perm_rank // _FACT[6 - i]
        perm_rank %= _FACT[6 - i]
        perm.append(remaining.pop(digit))
    perm = tuple(perm)

    orient = [0] * 7
    for i in range(_ORIENT_DIGITS):
        orient[i] = orient_code % 3
        orient_code //= 3
    orient[6] = (-sum(orient[:6])) % 3
    return perm, tuple(orient)


def build_bfs_table() -> np.ndarray:
    """Breadth-first search from solved; returns the uint8 distance table.

    The table is indexed by :func:`encode`.  Value 255 marks "not yet reached"
    only during the build; the search is asserted to reach every one of the
    ``STATE_COUNT`` states with a maximum distance of 11 (God's number for the
    canonical 2x2x2 graph).
    """
    table = np.full(STATE_COUNT, 255, dtype=np.uint8)
    moves = cs.MOVES
    apply_move = cs.apply_move
    encode_fast = _encode_fast

    start = cs.SOLVED
    table[encode_fast(*start)] = 0
    frontier = [start]
    depth = 0
    while frontier:
        depth += 1
        nxt = []
        for state in frontier:
            for move in moves:
                child = apply_move(state, move)
                code = encode_fast(*child)
                if table[code] == 255:
                    table[code] = depth
                    nxt.append(child)
        frontier = nxt

    assert not (table == 255).any(), "BFS failed to reach every state"
    assert int(table.max()) == 11, f"expected diameter 11, got {table.max()}"
    assert int(table.min()) == 0
    assert (table == 0).sum() == 1, "only the solved state should have distance 0"
    return table


_TABLE = None


def get_bfs_table() -> np.ndarray:
    """BFS table, built at most once per process (cached to disk)."""
    global _TABLE
    if _TABLE is None:
        if os.path.exists(_TABLE_PATH):
            _TABLE = np.load(_TABLE_PATH)
            _validate_table(_TABLE)
        else:
            _TABLE = build_bfs_table()
            np.save(_TABLE_PATH, _TABLE)
    return _TABLE


def _validate_table(table: np.ndarray) -> None:
    """Sanity checks for a table loaded from disk."""
    if table.shape != (STATE_COUNT,):
        raise ValueError(
            f"cached {_TABLE_PATH} has shape {table.shape}, expected {(STATE_COUNT,)}"
        )
    assert (table == 255).sum() == 0
    assert int(table.max()) == 11
    assert (table == 0).sum() == 1


def bfs_distance(state) -> int:
    """Optimal distance of ``state`` to solved, O(1) via the BFS table."""
    return int(get_bfs_table()[encode(*state)])