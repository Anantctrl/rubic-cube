"""Search algorithm base types and the shared result contract.

Every algorithm in ``daa.algorithms`` returns a :class:`SearchResult` with the
*exact same fields*, so the comparison dashboard can render one table.  The
fields are the DAA-mandated observations:

- ``solution`` / ``length``      - what the algorithm returned
- ``nodes_explored``             - states expanded (popped from the frontier)
- ``states_generated``           - neighbours produced
- ``duplicates``                 - removals by duplicate detection (hashable set)
- ``pruned``                     - branches removed by move pruning / bounds
- ``max_depth``                  - deepest node expanded
- ``execution_time``             - wall-clock seconds of the search proper
- ``memory_bytes``               - peak resident-memory estimate during search
- ``memo_hits`` / ``memo_misses``- memoization cache counters
- ``heuristic``                  - name of the h() used (informed algorithms)
- ``initial_h``                  - h(start) (informed algorithms)
- ``forward/backward/meeting``   - bidirectional specifics
- ``iterations``                 - IDDFS per-depth table
- ``b&b best/bound/branches``    - branch-and-bound specifics
"""

from __future__ import annotations

from dataclasses import dataclass, field

from daa.cube.state import CubeState

DEFAULT_MAX_DEPTH = 20


@dataclass
class Limits:
    """Safety resource budget (spec: 'never freeze / never run forever')."""

    max_depth: int = DEFAULT_MAX_DEPTH
    max_states: int = 1_000_000  # generated states hard cap
    max_time_s: float = 30.0
    max_memory_mb: float = 512.0

    @classmethod
    def fast(cls) -> "Limits":
        return cls(max_depth=12, max_states=200_000, max_time_s=8.0)


@dataclass
class SearchResult:
    algorithm: str
    found: bool = False
    solution: list[str] = field(default_factory=list)
    length: int = 0
    nodes_explored: int = 0
    states_generated: int = 0
    duplicates: int = 0
    pruned: int = 0
    max_depth: int = 0
    execution_time: float = 0.0
    memory_bytes: int = 0
    memo_hits: int = 0
    memo_misses: int = 0
    heuristic: str | None = None
    initial_h: int | None = None
    iterations: list[dict] = field(default_factory=list)  # IDDFS / DLS
    forward_states: int = 0
    backward_states: int = 0
    meeting_depth: int = 0
    branches_explored: int = 0
    branches_pruned: int = 0
    best_solution: list[str] = field(default_factory=list)
    lower_bound: int = 0
    terminated: bool = False  # stopped by a resource limit before proof
    reason: str | None = None

    def summary(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "found": self.found,
            "length": self.length,
            "nodes": self.nodes_explored,
            "generated": self.states_generated,
            "duplicates": self.duplicates,
            "pruned": self.pruned,
            "max_depth": self.max_depth,
            "time_s": round(self.execution_time, 6),
            "memory_mb": round(self.memory_bytes / 1e6, 3),
            "memo_hits": self.memo_hits,
            "memo_misses": self.memo_misses,
            "terminated": self.terminated,
            "reason": self.reason,
        }


def apply_alg(state: CubeState, moves: list[str]) -> CubeState:
    for m in moves:
        state = state.apply_move(m)
    return state


def verify_solution(scramble: list[str], solution: list[str]) -> bool:
    """Solve-correctness: scramble then solution returns to solved."""
    start = CubeState.solved()
    start = apply_alg(start, scramble)
    end = apply_alg(start, solution)
    return end.is_solved()