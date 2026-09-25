"""Memoization (optional cache of heuristic results).

The pattern: ``cube state -> previously computed result``.  Search algorithms
may look up ``h(state)`` thousands of times; without memoization the same
state's heuristic is recomputed on every visit.  Memoization turns this into
one dict access after the first computation.

Counters are exposed exactly as the DAA report wants them: cache hits, cache
misses, and a memory estimate of the stored data.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, Hashable


@dataclass
class Memoizer:
    """Wraps ``fn`` with a dict cache and records hit/miss statistics.

    ``fn`` must be a pure function (deterministic, side-effect free) —
    otherwise caching changes the algorithm's meaning.  Heuristics qualify;
    a random scramble generator does not.
    """

    fn: Callable[[Hashable], int]
    cache: dict[Hashable, int] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    def __call__(self, key: Hashable) -> int:
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        value = self.fn(key)
        self.cache[key] = value
        return value

    def memory_bytes(self) -> int:
        """Rough estimate: dict table + one int entry per distinct key."""
        return sys.getsizeof(self.cache) + (
            len(self.cache) * (sys.getsizeof(int()) + sys.getsizeof(tuple()))
        )

    def clear(self) -> None:
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0