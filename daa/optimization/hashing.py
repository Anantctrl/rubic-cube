"""Hashing / duplicate detection.

A Rubik's cube graph has ~3.7e6 reachable 2x2x2 states; blind search would
revisit the same configuration from many move sequences.  Detecting duplicates
is essential to (a) avoid exponential blow-up and (b) guarantee shortest paths.

We expose two complementary keys:

- Python's native ``hash(state)``/``==`` (used as ``set``/``dict`` keys), and
- :meth:`~daa.optimization.hashing.StateHasher.code` — a dense, collision-free
  integer bijection onto ``[0, 3,674,160)`` (Lehmer rank of the permutation +
  mixed-radix orientation code).  The bijection also gives the UI a cheap
  "unique states seen" table without storing every tuple.
"""

from __future__ import annotations

from typing import Callable

from daa.cube.state import CubeState


class StateHasher:
    """Counts how many duplicate detections happened during a search.

    ``seen`` is a set of native state hashes (not the 3.6M-bijection — Python
    int hashes collide benignly inside the set, which is fine because the set
    also stores the tuple for equality).  ``code`` uses the dense bijection
    which is exact and cheap.
    """

    def __init__(self, find_code: Callable[[CubeState], int] | None = None):
        self.seen: set[int] = set()
        self.hasher_calls = 0
        self.duplicates = 0
        self.unique_count = 0
        self._find_code = find_code or (lambda st: st.hash_state())

    def code(self, state: CubeState) -> int:
        return self._find_code(state)

    def visit(self, state: CubeState) -> bool:
        """Mark ``state`` seen.  Returns ``True`` if it was already present."""
        self.hasher_calls += 1
        h = hash(state)
        if h in self.seen:
            self.duplicates += 1
            return True
        self.seen.add(h)
        self.unique_count += 1
        return False

    @property
    def duplicate_ratio(self) -> float:
        if self.hasher_calls == 0:
            return 0.0
        return self.duplicates / self.hasher_calls