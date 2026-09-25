"""Scramble generation for the 2x2x2 solver.

Scrambles live in the standard 18-move notation (U D L R F B with ' and 2),
never repeat the same face twice in a row, and are generated on the Python
side so the browser never has to reimplement cube logic.
"""

from __future__ import annotations

import random

from solver import cube_state as cs

MOVES = cs.MOVES

_FACES = "UDLRFB"


def generate_scramble(rng: random.Random | None = None, length: int = 12) -> list[str]:
    """Return a random scramble of ``length`` moves with no same-face repeats.

    Uses the full 18-move alphabet (quarter turns and half turns).  ``rng``
    may be supplied for deterministic tests.
    """
    rng = rng or random
    moves_out: list[str] = []
    last_face = None
    for _ in range(length):
        while True:
            face = _FACES[rng.randrange(6)]
            if face != last_face:
                break
        last_face = face
        moves_out.append(face + rng.choice(("", "'", "2")))
    return moves_out


def scramble_with_distance(
    distance: int,
    rng: random.Random | None = None,
    max_tries: int = 100_000,
) -> list[str]:
    """Return a scramble whose BFS distance is exactly ``distance`` (0..11).

    Uses rejection sampling: draw long (near-uniform) scrambles and keep the
    first whose measured distance matches.  Distance 11 holds only ~0.07% of
    the state space, hence ``max_tries``.  Requires the BFS table to be
    loaded; raise ``RuntimeError`` if no scramble is found within the budget.
    """
    from solver import bfs_solver as bfs

    rng = rng or random.Random()
    if distance == 0:
        return []
    table = bfs.get_bfs_table()
    for _ in range(max_tries):
        alg = generate_scramble(rng, length=25)
        state = cs.apply_alg(cs.SOLVED, alg)
        if int(table[bfs.encode(*state)]) == distance:
            return alg
    raise RuntimeError(f"no scramble with distance {distance} found in {max_tries} tries")