# PLAN — 2x2x2 Rubik's Cube DAA Solver

Optimal solver for the 2x2x2 Pocket Cube (DAA mini-project). Two independent algorithms, both
guaranteeing optimal solution length:

1. **BFS** — one-time full-graph precomputation of distance-to-solved (3,674,160 states), O(1) queries.
2. **IDA*** — iterative-deepening backtracking with branch-and-bound pruning and an admissible heuristic.

Visualization: `cubing.js` `<twisty-player>` (CDN, no build step). Backend: Flask (live `/solve` endpoint).

## Decisions locked
- Phase 4 uses **Flask** (`viz/app.py`) + `viz/index.html` — any scramble, live solve.
- **PLAN.md** — this file; status updated after each phase verify.
- **IMPLEMENT.md** — append-only changelog; every file created/edited + actual verify results.
- Phases 7-11 turn the visualizer into a **real 3D move-by-move simulation** (cubing.js
  `<twisty-player puzzle="2x2x2" visualization="3D">`) where each scramble/solution move is
  physically animated one layer turn at a time, with legacy step controls + speed, and solver
  metadata synced to the cube state.
- `/solve` returns **spec-literal JSON**: `{scramble, solution, length, nodes, bounds (the tried
  IDA* bound sequence), bfs_length, optimal}` — extended with `algorithm, found, terminated,
  reason, time_s` (Phase 14); `algo` selects `physical` (default) or one of the nine DAA
  algorithms, which run on the on-screen physical cube state. Random Scramble comes from the
  backend (`GET /scramble?length=N`, `solver/scramble.py`), not from JS.
- DAA algorithms honour their limits and report bounded failures honestly (`found:false` +
  `reason`); the 3D page explains this instead of fabricating a solve. Bidirectional must be
  optimal (level-synchronized BFS, stop when `best ≤ F+B+1`).
- All experimental cubing.js APIs are confined to `viz/simulation.js`, feature-detected, with a
  guaranteed-correct fallback (canonical prefix rebuild via `player.alg`).
- Final gate = **manual visual verification of the 3D animation by the user** (guardrail 12);
  machine-side equivalence is proven by an independent verifier test suite instead.

## Environment
| Item | Requirement |
|---|---|
| Python | 3.10+ (actual: 3.14.6) |
| Browser | Chrome/Firefox for twisty-player |
| Node.js | not required |

## Dependencies (requirements.txt)
```
numpy>=1.26
matplotlib>=3.8
flask>=3.0
```

## Folder Structure
```
rubiks-2x2-solver/
├── solver/
│   ├── __init__.py
│   ├── cube_state.py        # state, 18-move tables, apply_move, inverse, is_solved
│   ├── bfs_solver.py        # BFS → uint8 table, encode/decode
│   ├── ida_star_solver.py   # IDA* + ceil(m/4); stats.bounds_seq = tried bounds
│   ├── scramble.py          # random scramble generator (backend /scramble source)
│   └── tests/               # cube_state, bfs, ida_star, verifier, simulation contract
├── viz/
│   ├── index.html           # 3D twisty-player + step controls + solver panel (UI)
│   ├── simulation.js        # CubeSimulation controller (all experimental cubing.js API here)
│   ├── style.css            # page styles
│   └── app.py               # Flask: serves viz/, /solve (spec JSON), /scramble
├── analysis/benchmark.py    # both solvers, matplotlib plots
├── daa/                     # DAA comparative study (9 hand-written search algorithms)
│   ├── cube/state.py        # CubeState wrapper (frozen, hashable) over solver.cube_state
│   │   └── physical.py      # PhysicalCubeState (8-corner, on-screen cubing.js move basis)
│   ├── algorithms/          # bfs dfs dls iddfs bidirectional greedy astar backtracking branch_bound + util/base
│   ├── optimization/        # MovePruner + Memoizer
│   ├── heuristics/          # admissible + estimate-only registry; PDB (3 corners)
│   ├── benchmark/           # runner, metrics, reports (CSV/markdown), registry
│   ├── tests/               # 62 tests
│   └── ui/                  # Streamlit dashboard (app, cubenet, panels, charts) — tab 2 switcher
├── report/complexity_analysis.md
├── requirements.txt
├── PLAN.md
├── IMPLEMENT.md
└── README.md
```

## Core Conventions (non-negotiable, from spec)
- State = `(permutation: tuple[7], orientation: tuple[7])`; 8th corner fixed to remove whole-cube
  rotational symmetry — never represented or moved.
- 18-move set: `U U' U2 D D' D2 L L' L2 R R' R2 F F' F2 B B' B2`. Move tables precomputed once at
  import time, never recomputed per call.
- BFS table = `numpy.uint8`, bijective `encode(perm, orient) -> int`, ~3.7 MB. No Python dict for the
  final table.
- IDA* heuristic `h(n) = ceil(m/4)`, m = corners not in correct position (orientation is separate).
  Do NOT sum with a separate orientation bound (inadmissible). First version may use exact BFS table
  as a trivially-admissible placeholder, noted in code comments.
- Every IDA* solution must be cross-checked against the BFS table for the same state.
- BFS build and IDA* heuristic logic stay independent code paths.

## Phases

| # | Deliverable | Verify gate (run pytest, report real result) | Status |
|---|---|---|---|
| 1 | `solver/cube_state.py` | round-trip `apply_move(state, m)` then `inverse(m)` == state, all 18 moves | done — 10 passed |
| 2 | `solver/bfs_solver.py` | table = exactly 3,674,160 filled entries, max value = 11 | done — 18 passed, max 11, build ~405s cached to `bfs_table.npy` |
| 3 | `solver/ida_star_solver.py` | >=50 scrambles depth <=8: IDA* len == BFS table len; log nodes | done — 60/60 match, nodes in analysis/ida_nodes_log.csv |
| 4 | `viz/index.html` + `viz/app.py` | page renders scramble; `/solve` returns optimal alg; animation plays | done — /solve verified (incl. 400 guard); page rendered in Edge/Brave; animation = manual step |
| 5 | `analysis/benchmark.py` | plots saved; measured nodes/time depths 2-8 vs b^d | done — CSV + 2 plots; 22..935k nodes, 0.04..1151 ms vs 18^d |
| 6 | `report/complexity_analysis.md` | filled with real Phase 5 numbers | done — full analysis, real numbers |
| 7 | Backend serving: `solver/scramble.py`; `/solve` returns **spec-literal JSON** (bounds = tried sequence); `GET /scramble?length=`; whitelisted static routes | `/solve` JSON matches spec exactly; `/scramble` legal (no same-face repeats), clamps + 400s; contract test suite | done — 37 passed |
| 8 | `viz/simulation.js` — `CubeSimulation` (spec interface; timeline-first stepping, prefix-rebuild fallback; experimental APIs isolated + feature-detected) | node harness: stepping, clamps, phases, play/pause, onDone chaining in both timeline and fallback modes | done — 29/29 assertions |
| 9 | 3D UI — `viz/index.html` + `viz/style.css` (twisty-player 3D, scramble/solution chips, solver panel, step card, legacy controls, speed) | page + assets served 200; inline + module scripts parse; cubing.js CDN reachable (and the *correct* URL is used) | done — HTTP + parse checks |
| 10 | End-to-end verification — `test_verifier.py` (independent geometric 8-corner simulator) + `test_simulation_contract.py` (Flask contract); depth categories 0,1,2,4,6,8,10,11 | every depth: apply scramble then solution → solved (independent simulator); API schema/limits tests | done — 37 passed; **manual 3D visual gate = user (pending)** |
| 11 | Docs polish — README rewrite, report (two IDA* heuristic modes; solver benchmark kept separate from browser rendering), final gate | all docs updated with real numbers; full pytest; manual visual check | done — docs done, final visual pass pending |
| 12 | DAA comparative study — `daa/` nine hand-written algorithms, heuristics (admissible + estimate), pruning/memoization, benchmark + CSV, tests | `python -m pytest solver/tests daa/tests -q` → 92 passed (243 s); smoke solve `L' U2 R B R D` length 4 for BFS/DLS/IDDFS/Bidir/Greedy/A*/B&B | done — suite green, dashboard verified in-session |
| 13 | DAA dashboard — Streamlit `daa/ui/app.py` (Solve & Compare, Learn, Complexity, Viva, Benchmark tabs; matplotlib net + plotly charts) + `viz/index.html` mode toggle (3D Solver / DAA Study iframe) | `streamlit run` → 127.0.0.1:8501 healthy (HTTP 200); AppTest 0 exceptions; Flask 5000 serves toggle | done — machine-side verified; visual pass pending |
| 14 | Algorithm selector on the 3D page — DAA algorithms run on the physical cube (`daa/cube/physical.py`); dropdown + honest limits (`found/terminated/reason/time_s`); non-blocking Random prefetch; A*/Greedy/B&B use the exact-BFS admissible heuristic (B&B also seeds its incumbent via greedy descent), BFS/IDDFS/DLS/DFS/Backtracking exhaustive | `python -m pytest solver/tests daa/tests -q` → 106 passed (89 s); API + browser smoke (dist-9 Bidirectional len 9 optimal; A* & B&B exact-h len 9/0.05s; Greedy physical solve; IDDFS honest state-limit message) | done — suite green, browser-verified |
| 15 | Scramble sync 3D page → DAA study — `POST /current-scramble` on Flask (mirrored by the page on Random click / manual typing); dashboard polls it via a hidden 1 s `st.fragment` and forces its sidebar source to *Manual* with the synced move string so Solve & Compare studies the same random case (live, no reload/reset) | `python -m pytest solver/tests daa/tests -q` → 109 passed (179.6 s, +3 `/current-scramble` contract tests); live browser: Random → Flask holds the new scramble → dashboard sidebar shows Manual = same string; idle CPU confirms the poll converged (no rerun loop) | done — suite green + live browser-verified |

## Commands
```bash
python -m venv venv
# Windows: venv\Scripts\activate    |    Unix: source venv/bin/activate
pip install -r requirements.txt
python -m pytest solver/tests daa/tests -q
python analysis/benchmark.py
python viz/app.py                  # http://localhost:5000 (viz + /solve API)
python -m streamlit run daa/ui/app.py --server.port=8501   # DAA dashboard
```

## Guardrails
- Never report a phase done without actually running its verify step in-session.
- Don't start a phase's files while the previous phase's test is failing (unless isolating a bug).
- Keep BFS and IDA* independent — Phase 3 verifies by comparing the two.
- Notation (U U' U2 ... B B' B2) is the sync contract between solver output, the tests and the
  3D cube; no cube-solving logic is ever duplicated in JS.
- All experimental cubing.js APIs stay inside `viz/simulation.js` with runtime feature detection
  and a prefix-rebuild fallback; `player.alg` always equals the full sequence and the controller
  scrubs back to the current step.
- Never write PASS for the Phase-10/11 visual gate until the user has confirmed the animation by
  hand.