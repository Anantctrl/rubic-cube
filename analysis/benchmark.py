"""Phase 5 benchmark: BFS O(1) queries vs IDA* nodes/time, depths 2..8.

Writes ``analysis/benchmark_results.csv`` and two plots:
- ``analysis/benchmark_nodes.png``  -- average IDA* nodes per depth vs theoretical b^d (full
  18-move tree grows ~18^d; measured IDA* explores far fewer thanks to the admissible heuristic
  plus same-face pruning, which also makes the effective branching ~15).
- ``analysis/benchmark_time.png``   -- average wall time per depth (log scale).
"""

from __future__ import annotations

import csv
import os
import random
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from solver import bfs_solver as bfs
from solver import cube_state as cs
from solver import ida_star_solver as ida
SEED = 20260923
SAMPLES = {2: 60, 3: 60, 4: 50, 5: 40, 6: 30, 7: 25, 8: 20}
MAX_DEPTH = 8


def _benchmark():
    rng = random.Random(SEED)
    rows = []
    for depth in range(2, MAX_DEPTH + 1):
        nodes_sum = 0.0
        time_sum = 0.0
        opt_len_sum = 0.0
        for _ in range(SAMPLES[depth]):
            alg = [rng.choice(cs.MOVES) for _ in range(depth)]
            state = cs.apply_alg(cs.SOLVED, alg)
            expected = bfs.bfs_distance(state)
            stats = {}
            t0 = time.perf_counter()
            solution = ida.ida_star_solve(state, stats=stats)
            dt = time.perf_counter() - t0
            assert len(solution) == expected  # optimality cross-check
            nodes_sum += stats["nodes"]
            time_sum += dt
            opt_len_sum += expected
        n = SAMPLES[depth]
        rows.append(
            dict(
                depth=depth,
                samples=n,
                avg_nodes=nodes_sum / n,
                avg_time_ms=time_sum / n * 1000.0,
                avg_optimal_len=opt_len_sum / n,
            )
        )
    return rows


def _bfs_query_time():
    rng = random.Random(123)
    states = []
    for _ in range(3000):
        alg = [rng.choice(cs.MOVES) for _ in range(9)]
        states.append(cs.apply_alg(cs.SOLVED, alg))
    table = bfs.get_bfs_table()
    t0 = time.perf_counter()
    for state in states:
        table[bfs.encode(*state)]
    return time.perf_counter() - t0, len(states)


def main():
    rows = _benchmark()
    csv_path = os.path.join(HERE, "benchmark_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["depth", "samples", "avg_nodes", "avg_time_ms", "avg_optimal_len"])
        w.writeheader()
        w.writerows(rows)

    depths = [r["depth"] for r in rows]
    nodes = [r["avg_nodes"] for r in rows]
    times = [r["avg_time_ms"] for r in rows]
    theoretical18 = [18 ** d for d in depths]
    theoretical15 = [15 ** d for d in depths]

    plt.figure(figsize=(7, 5))
    plt.plot(depths, theoretical18, "--", color="gray", label="theoretical 18^d (full 18-move tree)")
    plt.plot(depths, theoretical15, ":", color="darkgray", label="theoretical 15^d (same-face pruned)")
    plt.plot(depths, nodes, "o-", color="#3b82f6", label="IDA* avg nodes (h = ceil(m/4))")
    plt.yscale("log")
    plt.xlabel("scramble depth d")
    plt.ylabel("nodes (log scale)")
    plt.title("IDA* search effort vs theoretical b^d")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "benchmark_nodes.png"), dpi=120)

    plt.figure(figsize=(7, 5))
    plt.plot(depths, theoretical18, "--", color="gray", label="theoretical 18^d (right: log scale)")
    plt.plot(depths, times, "s-", color="#16a34a", label="IDA* avg wall time (ms)")
    plt.yscale("log")
    plt.xlabel("scramble depth d")
    plt.ylabel("time (ms, log scale)")
    plt.title("IDA* wall time per depth")
    plt.legend()
    plt.grid(True, which="both", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(HERE, "benchmark_time.png"), dpi=120)

    qtime, nq = _bfs_query_time()
    print(f"wrote {csv_path}")
    for r in rows:
        print(
            f"d={r['depth']:2d} n={r['samples']:2d} avg_nodes={r['avg_nodes']:12.0f} "
            f"avg_time={r['avg_time_ms']:9.3f} ms  avg_opt_len={r['avg_optimal_len']:4.1f}  "
            f"18^d={18 ** r['depth']:12,.0f}"
        )
    print(f"BFS table query: {nq} lookups in {qtime * 1e3:.1f} ms "
          f"({qtime / nq * 1e6:.2f} us/query) -- O(1)")
    print("plots: benchmark_nodes.png, benchmark_time.png")


if __name__ == "__main__":
    main()