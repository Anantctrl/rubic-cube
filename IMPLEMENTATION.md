# 2×2×2 Rubik's Cube — Implementation Guide

How the project is built: the cube model, every solving method we use, the web
UI, the 3D solver, and the comparative Design & Analysis of Algorithms (DAA)
study dashboard.

## 1. One-paragraph summary

We solve a 2×2×2 Rubik's cube optimally. The core is a **BFS full-graph
precomputation**: solve every one of the 3,674,160 reachable cube states by
breadth-first search from the solved state and store the distances in a
`numpy.uint8` lookup table, making the *optimal length* of any scramble an
O(1) table lookup. That table is also an admissible heuristic for **IDA*** and
for the **physical 3D solver** that animates real face turns in the browser.
A theory-styled **DAA study** ships nine hand-written search algorithms (BFS,
DFS, DLS, IDDFS, Bidirectional, Greedy, A*, Backtracking, Branch & Bound),
all compared live on the same cube state in a Streamlit dashboard embedded in
the same web page as the interactive 3D solver.

## 2. Architecture

```
run_app.py  (launcher + watchdog, restarts dead servers every 3 s)
 |
 +-- Flask server  :5000      (viz/app.py)
 |     serves  index.html  simulation.js  style.css
 |     API:  GET /solve?scramble=..&algo=..
 |           GET /scramble?length=N
 |           GET/POST /current-scramble
 |     3D solver: cubing.js <twisty-player> in a browser tab.
 |
 +-- Streamlit     :8501      (daa/ui/app.py)
       DAA comparative study dashboard (Solve & Compare / Complexity / Benchmark)
       embedded in the web page under the "DAA Study" tab (or opened in a tab)
```

Rules of thumb that keep the design simple:

- **The backend solves; the browser renders.** All cube logic and every search
  run on the Python side. The browser only animates the moves it is handed.
- **The 3D page and the DAA dashboard study the same scramble.** Random / typed
  scrambles are POSTed to `/current-scramble`; the dashboard polls it and runs
  its study on the exact same case.

## 3. The cube model (source of truth: cubing.js)

The hardest correctness problem in a 2×2 solver is that a "solution" must
*undo the cube the browser actually displays*. We therefore define the state
algebra from the **same KPuzzle definition cubing.js uses** for the 2×2x2
(`solver/cube_state.py`), instead of a hand-rolled basis.

### 3.1 Physical 8-corner state

State = `(pieces, orient)`, two length-8 tuples:

- `pieces[i]` = which corner cubie occupies slot `i` (0..7),
- `orient[i]` = twist of that piece, `0/1/2` mod 3.

A move is an action `(perm, delta)` and is applied as:

```python
new_pieces[i] = pieces[perm[i]]
new_orient[i] = (orient[perm[i]] + delta[i]) % 3
```

The definition declares only **U**, **x**, **y** directly; every other move is a
**derived move** expressed as a conjugation `[g: h] = g h g^-1`:

```python
"z": "[x: y]",  "L": "[z: U]",  "F": "[x: U]",
"R": "[z': U]", "B": "[x': U]", "D": "[x2: U]",
```

Composition, inversion and conjugation are implemented algebraically in
`_compose`, `_inverse`, `_conjugate`, so the 18 face turns (`U U' U2 … B2`)
are *computed*, never hand-typed. This guarantees the Python state space is
byte-for-byte the same group the `<twisty-player>` animates.

### 3.2 Canonical 7-corner quotient

The full 8-corner physical space has 8!·3⁷ legal states (≈ 88 MP), but the
solver needs only the **rotation-class** distances. Because rotating the whole
cube never changes the minimum number of face turns, we quotient by the 24
whole-cube rotations:

- **canonical representative**: the unique rotation (built from the
  definition's `x`/`y` moves) that puts **piece 7 in slot 7 with twist 0**;
- the remaining 7 pieces form `(perm7, orient7)` with `orient[6]` forced by
  `sum(orient) == 0 (mod 3)` — a **bijective** code to
  **7! × 3⁶ = 3,674,160** canonical states → `solver/bfs_solver.encode()`.

`apply_move` on the quotient uses precomputed 7-corner **effects tables**
(`MOVE_TABLES`): for each move, a slot map + orientation map, verified
state-independent at build time. This is much faster than physical apply +
re-canonicalise per move.

### 3.3 Two state classes

| Class | Space | Used by |
|---|---|---|
| `solver.cube_state` (plain tuples + `apply_move`) | canonical 7-corner | BFS table build, IDA*, shape of the table |
| `daa.cube.physical.PhysicalCubeState` | **real** 8-corner physical | all nine DAA algorithms — their returned moves genuinely undo the on-screen cube |
| `daa.cube.state.CubeState` | canonical 7-corner wrapper | DAA study when running standalone (heuristic projection) |

Both DAA classes expose the same tiny duck-typed search interface
(`apply_move`, `is_solved`, `hash_state`) so every algorithm works unchanged on
either.

## 4. Solving methods — "what methods do we use?"

There are four layers, from the foundation up.

### 4.1 BFS full-graph precomputation (`solver/bfs_solver.py`)

Breadth-first search from the solved state:

- every state stores its **optimal distance** in a `numpy.uint8` array of
  length 3,674,160 (value 255 = unvisited during build),
- asserts: all states reached, **diameter = 11** (God's number for the 2×2×2),
  exactly one state at distance 0,
- built once (~6–7 min) and cached to `solver/bfs_table.npy`,
- `bfs_distance(state)` = **O(1) index lookup**.

This single table is the load-bearing piece: it answers "is this scramble
optimal?" instantly, and it doubles as the heuristic for the other solvers.

### 4.2 IDA* with an admissible heuristic (`solver/ida_star_solver.py`)

Optimality for arbitrary scrambles *without* the 4 MB table hashing:

- **h(n) = ceil(m / 4)**, `m` = number of misplaced corners (position only).
  A quarter-turn moves exactly four corners, so it fixes at most 4 misplaced
  corners per move → never overestimates → **admissible**.
- **Iterative deepening**: bounds `h(start), h(start)+1, …` up to 11, plain DFS
  per bound, first success is proven optimal.
- **Same-face pruning**: never turn the same face twice in a row (any two
  same-face turns collapse into one), dropping the branching factor **18 → 15**
  without losing optimality.

Benchmark (`analysis/benchmark_results.csv`, depths 2–8):

| depth | avg nodes | avg time (ms) | avg optimal len |
|---|---|---|---|
| 2 | 22 | 0.04 | 1.7 |
| 4 | 1,176 | 1.5 | 3.0 |
| 6 | 41,541 | 51 | 3.8 |
| 8 | 935,726 | 1,151 | 5.0 |

vs. the theoretical 18^d tree — the admissible h plus pruning keeps measured
nodes dramatically below the full tree (log-scale plots in `analysis/`).

### 4.3 Physical optimal solver (`solver/physical_solver.py`) — the default

Solves in the **8-corner cubing.js basis** so the moves really turn the cube:

- **h(n) = BFS distance of the canonical representative** of the physical
  state — admissible (a physical move induces a canonical move of length 1),
  and near-exact, which makes the search collapse to near the optimal path.
- **Fast path**: a greedy exact-h descent (follow moves that drop h by exactly
  1) usually walks most of the way.
- **Guarantee**: if the greedy path doesn't finish, a plain IDA* from the
  original state (same admissible h, per-iteration transposition cut) proves
  optimality.
- Deterministic: moves are tried in lexicographic order.

This is `algo=physical`, the default in the UI dropdown.

### 4.4 Scramble generation (`solver/scramble.py`)

- `generate_scramble(length)` — 18-move alphabet, no face repeated twice in a
  row (avoids trivially-reducible scrambles). Purely Python-side, so the
  browser never reimplements cube logic.
- `scramble_with_distance(d)` — rejection sampling (draw long near-uniform
  scrambles until the BFS distance matches) used by tests/benchmarks for
  exact-depth cases. Distance-11 states are only ~0.07% of the space, hence
  the `max_tries` budget.

## 5. Flask web API (`viz/app.py`)

| Endpoint | Behaviour |
|---|---|
| `GET /` | serves `index.html` (no-store — the page is tiny and re-developed often) |
| `GET /solve?scramble=R U R' .. &algo=..(&depth=..)` | JSON solve result |
| `GET /scramble?length=N` (1..40) | `{ "scramble": "..." }` |
| `GET/POST /current-scramble?scramble=..` | latest case shared with the DAA dashboard |

`/solve` response contract:

```json
{
  "scramble": "R U R' U2",
  "solution": "R' U R U' ...",   // empty if not found
  "length": 8,
  "nodes": 1234,
  "bounds": [1, 2, 3],           // IDA* bound sequence (physical path only)
  "algorithm": "...",
  "bfs_length": 8,               // optimal length from the table (ground truth)
  "optimal": true,
  "found": true,
  "terminated": false,
  "reason": null,
  "time_s": 0.0123
}
```

Key design points:

- `algo=physical` uses layers 4.1–4.3 above.
- Any other `algo` is one of the **nine DAA algorithms**, run through
  `daa.benchmark.registry.run_algorithm` on a **`PhysicalCubeState`** — so the
  returned moves really undo the displayed scramble.
- **Physical-correctness is a hard guarantee**: after running, the start state
  is re-walked with the returned solution and the API only reports
  `found:true` if the cube literally returns to solved.
- **Honesty under limits**: `Limits(max_depth=20, max_states=600_000,
  max_time_s=20.0)` bound every DAA run; if a search exhausts its budget it
  returns `found:false, terminated:true, reason:"..."` — nothing is ever
  fabricated, and the UI says so to the user.
- Informed DAA algorithms (A*, Greedy, Branch & Bound) are offered the
  **exact BFS distance** as their heuristic so they can finish deep scrambles
  inside the web time budget.

## 6. The 3D solver UI (browser)

### 6.1 Rendering

- A single `<twisty-player puzzle="2x2x2" visualization="3D" control-panel="none">`
  element loads **cubing.js from the CDN** (`https://cdn.cubing.net/v0/js/cubing/twisty`).
- `viz/simulation.js` — `CubeSimulation`, a controller that **drives every move
  visibly**. It knows nothing about BFS/IDA*; it receives `(scramble, solution,
  metadata)` and plays them.
- Modern cubing.js API: `player.play()/pause()`, `tempoScale`, and the
  experimental-model scrub via `timestampRequest.set(ms)` /
  `detailedTimelineInfo` / `coarseTimelineInfo`.
- **Two robustness guarantees** independent of API drift:
  1. *Stepping* (PREVIOUS/NEXT/jump/chip-click) always ends on an exact state —
     via timestamp scrub when the timeline API works, else prefix rebuild.
  2. *Playback* (`play()`) animates the full sequence; a poll on
     `coarseTimelineInfo` detects the end and a **safety timeout** guarantees
     the `scramble → solve` chain never hangs.

### 6.2 Solve flow (`index.html`)

The `Solve` button handles five cases so the cube never flashes/reset and
extra clicks are harmless:

- **Case A — resumable**: cube already paused at the scrambled pose with a
  matching prefetched solution → just `playSolution()` (route through re-scrub
  + play; a bare `play()` on an already-loaded paused timeline was observed to
  no-op).
- **Case B — already solved**: same scramble + algorithm already solved →
  no-op (solving a solved cube changes nothing; no rebuild, no flash).
- **Case C — attachable**: solution was prefetched but arrived mid-scramble and
  never attached → attach it at the *current* scrambled pose, play only the
  solution.
- **Case D — scramble pose**: scramble still animating → **defer** via
  `sim.onDone(attachAndSolve)` so the solve plays seamlessly at scramble end;
  paused already → attach + solve in place. This is the fix for the old "the
  face changes when I press Solve" bug: the timeline is never reset mid-scramble.
- **Fresh**: build the single `scramble + solution` timeline once and animate
  the whole thing.

Idempotency guards at the top of `solve()` ignore a second SOLVE press while a
solve is queued/deferred or a solution is already animating — fixing the "it
solves, then solves again" bug (a double press used to rebuild the timeline,
which flashed the cube to solved and re-scrambled).

`Random` animates the scramble **immediately** and prefetches the solution in
the background; the timeline is only extended once the scramble playback has
paused, so a slow DAA search never blocks the animation. If the solution lands
mid-scramble it is attached quietly via `onDone`.

The status line derives from live sim state (`phase`, `playing`, step vs
scramble length) and explicitly reports `SOLVING…` during solution playback,
plus an honest orange warning ("No solution within limits (…) — nothing is
fabricated") when a bounded DAA search gives up, with suggested alternatives.

### 6.3 Mode tab

- **▧ 3D Solver** vs **▣ DAA Study** tabs; the dashboard `<iframe>` loads
  lazily each time the tab is entered (avoids background-throttling the
  Streamlit session), with an "open in a new tab" fallback.
- The dashboard URL is derived from `window.location.hostname`, so it also
  works under port forwarding / LAN — not just literal `127.0.0.1`.

## 7. The DAA study — nine algorithms, measured honestly

### 7.1 What it studies

`daa/` is a self-contained Design & Analysis of Algorithms project comparing
nine hand-written searches on **identical start states**, all metrics measured
at runtime:

| Algorithm | Idea | Optimal? | Asymptotics vs b≈12, d=m |
|---|---|---|---|
| **BFS** | FIFO queue, level order | Yes | time O(b^d), space O(b^d) |
| **DFS** | LIFO stack, go deep first | No | time O(b^m), space O(bm) |
| **DLS** | DFS with explicit depth limit `l` | No | O(b^l), incomplete if l too small |
| **IDDFS** | DLS for limit 0,1,2,… | Yes | O(b^d) time, O(bd) space |
| **Bidirectional** | forward + backward BFS meeting mid-way | Yes | time/space O(b^(d/2)) |
| **Greedy** | best-first by f(n)=h(n) only | No | fast, may detour |
| **A\*** | best-first by f(n)=g(n)+h(n) | Yes (admissible h) | O(b^d) time, O(b^d) space |
| **Backtracking** | recursive generate-and-test, undo on fail | No | O(b^m), space O(m) |
| **Branch & Bound** | backtracking + prune by `g+h ≥ best` | Yes (admissible h) | O(b^m), space O(m) |

### 7.2 Shared contract (`daa/algorithms/base.py`)

Every algorithm returns the **same `SearchResult`** so the dashboard renders
one table: `found`, `solution/length`, `nodes_explored`, `states_generated`,
`duplicates`, `pruned`, `max_depth`, `execution_time`, `memory_bytes`,
`memo_hits/misses`, plus algorithm-specific extras (IDDFS `iterations` table,
bidirectional `forward/backward/meeting`, B&B `branches_explored/pruned` and
`best_solution`) and the honest `terminated / reason`.

A single `Limits(max_depth, max_states, max_time_s, max_memory_mb)` budget is
honoured by every algorithm ("never freeze / never run forever"). `ExitGuard`
checks it during expansion so even a deep search stops cleanly.

### 7.3 Shared optimisations (`daa/optimization/`)

- **Move pruning** (`MovePruner`): inverse-move (skip `R R'`), same-face (skip
  `R R`, `R R2` → collapses to one turn), and consecutive-repeat. All three are
  *complete* — for the 2×2 group the pruned edges are dominated, so shortest
  paths are never lost. Effective branching ≈ 15 → ≈ 12.
- **Memoization** (`Memoizer`): wraps `h()` calls, caching by state hash
  (hits/misses reported).
- **Hashing** (`_pack`): collision-free 40-bit code for physical states (24-bit
  permutation + 16-bit orientation); canonical states use the dense
  `bfs_solver.encode` rank directly.

### 7.4 Heuristics (`daa/heuristics/`)

Six pluggable `CubeState -> int` heuristics, each with an **admissibility**
flag so the UI can tell an "estimate" from a proven lower bound:

1. Misplaced Stickers *(estimate)*
2. Misplaced Corners *(estimate)*
3. `ceil(misplaced/4)` — **admissible**
4. `ceil(stickers/12)` — **admissible** (weak, safe)
5. Pattern database (3 corners) — **admissible** by construction
   (projection distance; cached in `daa/.cache/pdb_3corners.pkl`)
6. **BFS distance (exact)** — the perfect h, O(1) from the table; informed
   searches with it expand (near) only the optimal path.

Default for the study: `ceil(misplaced/4)`.

### 7.5 Bidirectional optimality (the interesting proof)

`daa/algorithms/bidirectional.py` expands **level by level** on both fronts.
After levels (F, B), any *undiscovered* meeting node has `f_dist ≥ F+1` and
`b_dist ≥ B+1`, so its path is `≥ F+B+2`. The search therefore keeps the
shortest meeting found and **stops as soon as `best ≤ F+B+1`** — no better
solution can exist. This is provably-optimal bidirectional search, unlike a
naive "first meet wins". The DAA point: two balls of radius d/2 cover what one
ball of radius d does, exponentially cheaper on deep scrambles.

### 7.6 The dashboard (`daa/ui/app.py` + `panels.py` + `charts.py` + `cubenet.py`)

Streamlit, three tabs:

1. **Solve & Compare** — draws the scrambled cube (matplotlib net via
   `render_state`), lists the selected algorithms, and runs them all on the
   same start state. One results table, bar charts for time and nodes, and a
   per-algorithm expander with the full detail, IDDFS per-depth iteration
   table/plot, bidirectional meet info, B&B "explored vs pruned vs lower bound
   vs best", and h(state) + admissibility. Every solution is **verified** by
   re-applying `scramble + solution` and checking it hits solved.
2. **Complexity** — the textbook asymptotic table, explicitly labelled
   "NOT measured".
3. **Benchmark** — N scrambles × algorithms with a seed, limits and heuristic;
   exports CSV + markdown. Stored in `daa/benchmark/reports.py`.

Sidebar: scramble source (Random with seed/length, or Manual), the three
pruning toggles, memoization toggle, max depth / max states / max time, the
active heuristic, and the algorithm multiselect (with a DLS depth-limit input
when DLS is selected).

**Live sync with the 3D page**: `@st.fragment(run_every=2.0)` polls
`http://127.0.0.1:8501/../5000/current-scramble`; when the value changes it
drops it into the manual-scramble box and reruns — so a Random click on the 3D
page re-targets the whole study. Server-side fetch ⇒ no CORS.

### 7.7 Physical correctness for the study

The quotient `CubeState` is perfect for studying algorithms, but a canonical
solution may be correct only *up to a whole-cube rotation*. The dashboard and
the web API therefore run every DAA algorithm on **`PhysicalCubeState`** (the
real 8-corner group), so the moves an algorithm returns genuinely solve the
cube on screen — while heuristics stay admissible by computing them on
the rotation-invariant canonical projection.

## 8. Launcher / watchdog (`run_app.py`)

One command (`python run_app.py`) starts both servers and keeps them alive:

- Flask `viz/app.py` (:5000), Streamlit :8501 headless on IPv4 loopback
  (`--server.address 127.0.0.1` — avoids a WinError-64 IPV6 dual-stack death
  when the hotspot blips).
- Every 3 s each server is health-checked (`/_stcore/health` for Streamlit);
  a dead one is restarted, after `free_port()` kills any wedged process still
  holding the port (`netstat -ano -p tcp` → `taskkill /PID /F`) — a failed
  child would otherwise keep 8501/5000 "in use" while being unresponsive.
- Logs: `.run_app_flask.log`, `.run_app_streamlit.log` (gitignored). Ctrl+C
  stops both children.

## 9. Tests

`python -m pytest solver/tests daa/tests -q` → **109 tests passing**:

- `solver/tests`: cube-state/move algebra, BFS table (encode/decode bijection,
  distances, diameter), IDA* optimality vs table, scramble generation, the
  sim/page contract, and the physical-solver verifier.
- `daa/tests`: the state interface, physical state, all algorithm behaviours
  (including bounded termination and honesty), heuristics admissibility,
  pruning/optimization, the benchmark runner, and the UI helpers.

## 10. Project layout

```
rubiks-2x2-solver/
├─ run_app.py               launcher + watchdog (ports 5000/8501)
├─ requirements.txt         numpy, matplotlib, flask, pytest, streamlit, plotly, pandas
├─ analysis/                benchmark.py + results (csv/png) for IDA* vs 18^d
├─ solver/                  the real solving core
│  ├─ cube_state.py         2×2 group (cubing.js KPuzzle ground truth) + move tables
│  ├─ bfs_solver.py         full-graph BFS table (3,674,160 states) + encode/decode
│  ├─ ida_star_solver.py    IDA* with ceil(m/4) admissible h
│  ├─ physical_solver.py    greedy exact-h descent + optimal IDA* in 8-corner basis
│  ├─ scramble.py           scramble generation
│  └─ tests/
├─ daa/                     Design & Analysis of Algorithms study
│  ├─ cube/                 PhysicalCubeState + canonical CubeState (search interface)
│  ├─ algorithms/           bfs dfs dls iddfs bidirectional greedy astar
│  │                        backtracking branch_bound + base contract
│  ├─ heuristics/           misplaced, corners, pattern_database (3-corners PDB)
│  ├─ optimization/         MovePruner, Memoizer, hashing
│  ├─ benchmark/            registry, runner, reports, metrics
│  ├─ ui/                   Streamlit app + panels/concepts/complexity + charts + cubenet
│  └─ tests/
└─ viz/                     the web UI
   ├─ app.py                Flask server + /solve /scramble /current-scramble API
   ├─ index.html            3D solver page + DAA tab + solve-flow logic
   ├─ simulation.js         CubeSimulation controller (moves the <twisty-player>)
   └─ style.css
```

## 11. How to run

```bash
pip install -r requirements.txt
python run_app.py
# web app / 3D solver: http://127.0.0.1:5000
# DAA dashboard:       http://127.0.0.1:8501  (also embedded via the "DAA Study" tab)
python -m pytest solver/tests daa/tests -q      # 109 tests
```

The first `/solve` call builds the BFS table (~6–7 min, one time), then caches
it in `solver/bfs_table.npy`.