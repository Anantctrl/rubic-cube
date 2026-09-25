# rubic-cube

## How to run

```bash
python -m venv venv
# Windows: venv\Scripts\activate    |    Unix: source venv/bin/activate
pip install -r requirements.txt

python viz/app.py                          # Web app (3D solver + API)  → http://127.0.0.1:5000
python -m streamlit run daa/ui/app.py --server.port=8501   # DAA study dashboard → http://127.0.0.1:8501
python -m pytest solver/tests daa/tests -q # run the test suite (109 tests)
```

The 3D page embeds the dashboard (tab "DAA Study"); the dashboard also runs standalone at
127.0.0.1:8501. The BFS distance table auto-builds on first use (~6-7 min) and is cached.

## Project overview

2×2×2 Rubik's Cube — optimal solver & 3D simulation.

Optimal solver for the Pocket Cube using two independent algorithms, plus a **real 3D
move-by-move simulation** that visually performs every scramble and solution move on a live
`cubing.js` cube — one layer turn at a time.

## Features

- **Two independent optimal algorithms**, cross-checked against each other:
  - **BFS** — one-time full-graph precomputation of distance-to-solved over all 3,674,160
    canonical states (diameter 11); O(1) lookup.
  - **IDA*** — iterative-deepening branch-and-bound DFS with an admissible `h = ceil(m/4)`
    heuristic (position-only), plus an exact-BFS variant used for instant interactive solving.
- **Flask API** — `GET /solve?scramble=...&algo=...` returns `{scramble, solution, length, nodes,
  bounds, bfs_length, optimal, algorithm, found, terminated, reason, time_s}` and
  `GET /scramble?length=N` returns random WCA-style scrambles.  The `algo` parameter selects the
  solver: `physical` (default; BFS + exact-h IDA*) or one of the nine DAA algorithms
  (`BFS`, `DFS`, `DLS`, `IDDFS`, `Bidirectional`, `Greedy`, `A*`, `Backtracking`,
  `Branch & Bound`), which run on the real 8-corner physical group so their solutions truly
  undo the cube on screen.
- **Real 3D simulation** — `<twisty-player puzzle="2x2x2" visualization="3D">`; the scramble and
  each algorithm's solution are animated turn-by-turn with legacy step controls
  (`RESET · START · PREVIOUS · NEXT · SOLVED · PLAY · PAUSE`) and playback speed (0.5×/1×/2×).
- **Algorithm selector** — the 3D solver has a dropdown; choosing an algorithm re-solves the
  current scramble with that algorithm and animates its solution.  DAA algorithms honour their
  real resource limits: if one honestly runs out of budget without solving, the page says so
  (`found:false` + `reason`) and leaves the cube scrambled rather than fabricating a solve.
  Deep random scrambles (≥ distance ~7) can exceed the exhaustive searches — the informed
  algorithms and Bidirectional keep solving them.  Online, A*, Greedy and Branch & Bound are
  driven by the **exact BFS-distance heuristic** (same admissible h as the physical IDA*
  solver), so they reach — and optimally solve — any scramble up to the diameter at interactive
  speed; the DAA dashboard keeps the hand-computed `corners / 4` default for the comparative
  study.
- **Solver↔simulation sync** — solution chips highlight the current move; the step card shows the
  move, `Step n/total` and the current phase (scramble / solution / solved); clicking a chip
  jumps the cube to that exact state.
- **Independent verification** — a standalone geometric 8-corner simulator proves
  `apply(scramble) then apply(solution) = solved` at depths 0, 1, 2, 4, 6, 8, 10, 11.
- **DAA comparative study (Streamlit)** — nine hand-written search algorithms (`daa/`): BFS, DFS,
  DLS, IDDFS, Bidirectional, Greedy, A*, Backtracking, Branch & Bound — all with
  **measured** (never invented) metrics on the *same* start state: solution length, nodes
  explored, states generated, duplicates, pruned, depth, wall-clock time, memory, memo hit-rate,
  plus algorithm-specific detail (IDDFS per-depth table, bidirectional meet stats, B&B
  branches/lower bound). Admissible vs estimate-only heuristics are labelled in the UI; resource
  limits (depth / states / time) are enforced by every algorithm.
- **Dashboard modes** — `viz/index.html` has a **3D Solver / DAA Study** toggle: the DAA tab embeds
  the Streamlit app (`127.0.0.1:8501`) with an open-in-new-tab fallback.
- **Scramble sync (3D page → DAA study)** — whatever case is in the 3D-page input (Random click or
  manually typed) is mirrored to `POST /current-scramble`; the dashboard polls it (a hidden
  1-second `st.fragment`) and runs its Solve & Compare on that same scramble, flipping the sidebar
  source to *Manual* with the synced move string — live, with no reload and no reset of the other
  sidebar selections.

## Architecture

```
                 ┌──────────────┐
  BFS table ─────►│   Solver     │◄──── IDA* (h = ceil(m/4) | exact-BFS)
  (3,674,160)     └──────┬───────┘
                         │ solution + stats
                         ▼
                 ┌──────────────┐
                 │  Flask API   │   viz/app.py — /solve (spec JSON), /scramble, static
                 └──────┬───────┘
                         │ JSON (scramble, solution, bounds, …)
                         ▼
                 ┌──────────────┐
                 │ Simulation   │   viz/simulation.js — CubeSimulation (step/play/phase)
                 │  Controller  │   experimental cubing.js APIs isolated + feature-detected
                 └──────┬───────┘
                         │ player.alg / timeline.scrubTo
                         ▼
                 ┌──────────────┐
                 │   cubing.js  │   <twisty-player puzzle="2x2x2" visualization="3D">
                 └──────┬───────┘
                         ▼
                 ┌──────────────┐
                 │  3D Cube     │   every move is a visible layer turn
                 └──────────────┘
```

## Setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate    |    Unix: source venv/bin/activate
pip install -r requirements.txt
```

The BFS table is cached at `solver/bfs_table.npy`; first rebuild takes ~6-7 minutes, after that
it reloads in <0.5 s automatically.

## Run the web app

```bash
python viz/app.py
```

Open http://127.0.0.1:5000. Everything runs locally except the `cubing.js` library (CDN).

### API quick checks

```text
GET /solve?scramble=R U R' U'
  → {"scramble":"R U R' U'","solution":"U L U' L'","length":4,"nodes":7,
     "bounds":[4],"bfs_length":4,"optimal":true,"algorithm":"BFS + IDA* (physical, optimal)",
     "found":true,"terminated":false,"reason":null,"time_s":0.001}

GET /solve?scramble=R U F&algo=A*     → DAA algorithm run on the physical cube state
GET /scramble?length=12               → {"scramble":"…"}
GET/POST /current-scramble            → {"scramble":"…"} — last case entered in the 3D-page
                                         input (Random/typing push it; DAA study polls it)
GET /solve?scramble=Foo               → HTTP 400 {"error":"unknown move: Foo"}
GET /solve?scramble=R&algo=Nope       → HTTP 400 {"error":"unknown algo: 'Nope'"}
GET /style.css or /simulation.js       → 200 (whitelisted static routes)
```

## Benchmarks

```bash
python analysis/benchmark.py
```

Writes `analysis/benchmark_results.csv`, `benchmark_nodes.png`, `benchmark_time.png`:
IDA* avg nodes/time vs scramble depth (22 nodes @ d=2 … 935,726 nodes @ d=8, all optimal) versus
the theoretical `18^d` growth, plus BFS table O(1) query cost (~2 µs).

> The benchmark times are solver-only (pure Python, `time.perf_counter` around the search) —
> browser/render time of the 3D page is deliberately **not** mixed into complexity measurements.

## Tests

```bash
python -m pytest solver/tests daa/tests -q
```

**109 tests** over: cube-state tables, BFS table (3,674,160 states, max 11), IDA* optimality vs BFS,
independent geometric verifier (depth categories 0,1,2,4,6,8,10,11), the Flask API contract
(including `/current-scramble`), and the DAA suite (state, optimization, heuristics, all nine
search algorithms, benchmark).

## DAA study dashboard

```bash
python -m streamlit run daa/ui/app.py --server.port=8501
```

Open http://127.0.0.1:8501 (tab 2 of http://127.0.0.1:5000 embeds it). Five tabs:

- **Solve & Compare** — run any subset of the nine algorithms on one scramble; comparison table,
  plotly time/nodes bars, matplotlib cube net, per-algorithm detail.
- **Learn** — algorithm concepts (idea, data structure, pros/cons, DAA angle).
- **Complexity** — textbook asymptotic table (labelled *not measured*).
- **Viva** — likely examiner Q&A.
- **Benchmark** — N scrambles × algorithms with CSV + markdown export.

Same-state rule: every algorithm receives the identical `CubeState`; pruning/memo limits are shared
so the comparison is fair.

## Manual visual check (~30 s)

1. `python viz/app.py` and open http://127.0.0.1:5000 (an Edge app window is fine).
2. Press **Random** — the cube physically scrambles move-by-move.
3. Press **Solve** — the scramble animates, then every solution move turns the cube until solved;
   the chips highlight the current move and the step card counts `Step n/total`.
4. Step with **PREVIOUS / NEXT** (exactly one move each way), jump with **RESET / SOLVED(END)**,
   then **PLAY / PAUSE** and try **0.5× / 1× / 2×**.
5. Confirm `F2` turns are 180° and the cube ends fully solved.

## Documentation

- `PLAN.md` — project plan and phase status.
- `IMPLEMENT.md` — append-only implementation log (every bug found by running things, with fixes).
- `report/complexity_analysis.md` — complexity analysis with real benchmark numbers, the two IDA*
  heuristic modes, and the BFS-depth histogram.