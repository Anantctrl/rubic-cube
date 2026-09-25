# Complexity Analysis — 2x2x2 Optimal Cube Solver

Measured with the Phase 5 benchmark (`analysis/benchmark.py`, `benchmark_results.csv`).
All solving is performed on the **canonical** state space (piece 7 fixed in slot 7, twist 0),
which quotients the full 8-corner group by the 24 whole-cube rotations.

## 1. State space

| Quantity | Value |
|---|---|
| Full 8-corner group size | `8! * 3^7 = 88,300,800` |
| Reachable subgroup (orientation sum mod 3) | `8! * 3^7 / 3 = 88,300,800 / 3` |
| Canonical quotient (this solver) | `7! * 3^6 = **3,674,160** states |
| God's number (diameter of the canonical graph) | **11** (measured) |
| Moves | U U' U2 D D' D2 L L' L2 R R' R2 F F' F2 B B' B2 (18) |

BFS depth histogram (exact, from `build_bfs_table`):

`0:1, 1:9, 2:54, 3:321, 4:1847, 5:9992, 6:50136, 7:227536, 8:870072, 9:1887748, 10:623800, 11:2644`

## 2. BFS vs IDA* — the two algorithms

### BFS (exact table, O(1) queries)
- One-time breadth-first search from solved: `3,674,160` states x 18 edges. Measured build (pure
  Python): **~405 s**, cached to `solver/bfs_table.npy` (3.7 MB, `uint8`); disk reload 0.37 s.
- Query: O(1) table lookups via a bijective `encode(perm, orient)` (Lehmer mixed-radix).
  Measured: **1.93 µs/lookup** (3,000 lookups in 5.8 ms).
- Space: ~3.7 MB for the table itself (plus the tables' construction).

### IDA* (branch-and-bound DFS)
- Recursive DFS with a growing depth bound; admissible heuristic `h = ceil(m/4)` (position-only,
  m = misplaced corners, max improvement per move = 4). Same-face consecutive moves pruned
  (branching 18 -> 15; optimality preserved).
- **Space:** O(depth) stack — constant, tiny.
- **Time:** measured nodes grow roughly exponentially in the *scramble length*:

| depth d | samples | avg IDA* nodes | avg wall time | theoretical 18^d |
|---|---|---|---|---|
| 2  | 60 | 22        | 0.036 ms   | 324 |
| 3  | 60 | 186       | 0.259 ms   | 5,832 |
| 4  | 50 | 1,176     | 1.492 ms   | 104,976 |
| 5  | 40 | 3,010     | 3.912 ms   | 1,889,568 |
| 6  | 30 | 41,541    | 51.1 ms    | 34,012,224 |
| 7  | 25 | 645,073   | 928.7 ms   | 612,220,032 |
| 8  | 20 | 935,726   | 1150.7 ms  | 11,019,960,576 |

Plots: `analysis/benchmark_nodes.png` (nodes vs 18^d and 15^d, log scale) and
`analysis/benchmark_time.png`.

- The measured nodes are orders of magnitude below `18^d`: the admissible heuristic plus
  same-face pruning (effective branching ~15) keeps the search small for typical scrambles.
- **Worst case is bad (by design):** with this weak heuristic a depth-9 (distance 9) state took
  >10 minutes (hundreds of millions of nodes) — the classic IDA* exponential blowup. Phase 3's
  cross-check (`analysis/ida_nodes_log.csv`: 60 scrambles, depth <= 8, all optimal) stays inside
  the feasible region, and the web app uses the exact BFS table as a trivially-admissible
  heuristic for interactive worst-case solving (a depth-9 state then solves in 56 nodes instead
  of hundreds of millions).

## 3. Total runtime profile
- Table build ~405 s (once, then cached). Encode/decode Bijection < 5 µs.
- BFS query ~2 µs vs IDA* 0.04 ms (d=2) ... 1.15 s (d=8) — classical space vs time trade-off:
  BFS trades 3.7 MB + 6.7 minutes (build) for instant queries; IDA* trades exponential time for
  constant memory.

## 4. Correctness cross-checks (final suite)
`python -m pytest solver/tests -q` → **37 passed in 30.94 s** (Phases 1-11; includes the
independent geometric verifier at depths 0,1,2,4,6,8,10,11 and the Flask contract suite).
Highlights:
- 18-move round trips; table-vs-direct-8-corner simulation equality; orientation invariant
  `sum(orient) == 0 (mod 3)` preserved by every move.
- BFS table: exactly 3,674,160 states, max 11, one state at distance 0.
- IDA* length == BFS distance on ≥50 random scrambles (depth <= 8) in the pytest suite plus the
  60-scramble logged run (0 mismatches).

## 5. Limitations / notes
- `h = ceil(m/4)` ignores orientation by design (admissible; adding an orientation bound would
  over-estimate and break admissibility).
- Random scrambles of length d usually have true distance < d (avg_opt_len at d=8 is 5.0), so
  depth-8 IDA* is fast for typical inputs; adversarial distance-11 states are the slow tail.
- The web `/solve` endpoint uses the exact BFS table as its heuristic so any state solves
  instantly; the `ceil(m/4)` heuristic remains the default algorithm-level choice and is what the
  benchmark exercises.

## 6. Two IDA* heuristic modes (both admissible, same optimal result)
- **Research default — `h = ceil(m/4)`**: pure position-only bound, no BFS table required.
  Exponential worst case by design (a distance-9 state exceeded 10 minutes in Phase 3 testing).
  This is the mode the §2 benchmark and `analysis/ida_nodes_log.csv` exercise.
- **Interactive mode — exact-BFS subtree**: uses `bfs_table` directly as a trivially-admissible
  heuristic; `h(state) = distance(state)` so the first bound is the answer. Used by the web
  `/solve` endpoint (any state in a few dozen nodes, e.g. 56 nodes for the pathological depth-9
  state) and by the end-to-end depth-category tests at 0, 1, 2, 4, 6, 8, 10, 11.
- Both produce identical optimal lengths; the choice is purely wall-clock.

## 7. Solver benchmark vs visual simulation (kept separate)
- The Phase 5 benchmark measures **only solver CPU work**: a fresh Python process per sample, no
  browser, no rendering — `time.perf_counter` around the IDA*/BFS call. Browser/3D-render time is
  deliberately not mixed in, so §2's numbers are reproducible without a browser on the path.
- Correctness of the *visualization layer* is asserted by the independent geometric verifier
  (apply scramble + apply solution ⇒ solved, depths 0–11) and the Flask contract suite
  (37 tests total), since an animation cannot be validated by wall-clock timings on a headless
  machine. The final visual gate (Phase 9-11) is a manual 30-second walk-through per README's
  "Manual visual check".