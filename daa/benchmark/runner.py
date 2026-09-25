"""Benchmark runner: many scrambles × selected algorithms, honest numbers."""

from __future__ import annotations

import random

from daa.algorithms.base import Limits, apply_alg
from daa.algorithms.util import ExitGuard
from daa.benchmark.registry import run_algorithm
from daa.cube.state import CubeState
from daa.optimization.memoization import Memoizer
from daa.optimization.pruning import MovePruner


def run_single(
    scramble_alg: list[str],
    algorithms: list[str],
    limits: Limits | None = None,
    pruner: MovePruner | None = None,
    heuristic_name: str | None = None,
    use_memo: bool = True,
    seed: int = 1,
) -> list[dict]:
    """Run ``algorithms`` on one scramble; return per-algorithm summary dicts.

    The SAME :class:`~daa.cube.state.CubeState` is handed to every algorithm
    (the spec's "same initial cube state" rule).  Each entry is a plain dict
    so it is trivially serialisable to CSV/JSON for the dashboard.
    """
    limits = limits or Limits()
    pruner = pruner or MovePruner()
    start = CubeState.solved()
    for m in scramble_alg:
        start = start.apply_move(m)

    rows: list[dict] = []
    for alg in algorithms:
        memo = _make_memo(alg, heuristic_name) if use_memo else None

        res = run_algorithm(
            alg,
            start,
            limits=limits,
            pruner=pruner,
            memoizer=memo,
            heuristic_name=heuristic_name,
        )
        row = res.summary()
        row["scramble"] = " ".join(scramble_alg)
        rows.append(row)
    return rows


def _make_memo(alg: str, heuristic_name: str | None):
    import daa.heuristics as H

    name = heuristic_name or H.default()
    fn = H.HEURISTICS[name].fn
    return Memoizer(fn)


def run_benchmark(
    n_scrambles: int,
    scramble_lengths: list[int],
    algorithms: list[str],
    limits: Limits | None = None,
    pruner: MovePruner | None = None,
    heuristic_name: str | None = None,
    use_memo: bool = True,
    seed: int = 42,
) -> list[dict]:
    """Run ``n_scrambles`` per scramble length across all algorithms."""
    rng = random.Random(seed)
    all_rows: list[dict] = []
    for length in scramble_lengths:
        for _ in range(n_scrambles):
            alg = _random_scramble(rng, length)
            rows = run_single(
                alg, algorithms, limits, pruner, heuristic_name, use_memo, seed
            )
            all_rows.extend(rows)
    return all_rows


def _random_scramble(rng: random.Random, length: int) -> list[str]:
    faces = "UDLRFB"
    alg: list[str] = []
    last = None
    for _ in range(length):
        while True:
            f = faces[rng.randrange(6)]
            if f != last:
                break
        last = f
        alg.append(f + rng.choice(("", "'", "2")))
    return alg