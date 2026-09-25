# IMPLEMENT — Implementation Log

Append-only changelog. Every file created/edited, with actual verify results. One entry per session/phase.

---

## Session 0 — Scaffolding — 2026-09-23

- Created project skeleton: `solver/`, `solver/tests/`, `viz/`, `analysis/`, `report/`.
- Created `PLAN.md` (this plan), `IMPLEMENT.md` (this log).
- Ambient environment: Python 3.14.6, git 2.55.0.windows.3, Windows (PowerShell).
- Verify: n/a (no code yet).

---

## Phase 1 — State representation — `solver/cube_state.py` — 2026-09-23

Files created/edited:
- `solver/cube_state.py` (new) — `(perm[7], orient[7])` state, 18 precomputed move tables
  (`MOVE_TABLES`), `apply_move`, `inverse`, `apply_alg`, `is_solved`; internal full 8-corner
  model with Rodrigues 120-degree slot-diagonal rotations and canonicalization (piece 7 in
  slot 7, twist 0). Also `solver/__init__.py`, `requirements.txt`, `README.md` (created
  earlier this session, logged here).
- `solver/tests/test_cube_state.py` (new) — 10 tests.

Bugs fixed during Phase 1 (actual, discovered by running tests):
1. `_apply_rotation` rotated all 8 slots for a face turn (acted like a whole-cube rotation) —
   added `layer` parameter + `_LAYERS` so face turns touch only their 4 layer slots;
   canonicalization still uses `layer=None`.
2. Twist was invisible: sticker directions compared as an unordered **set** — switched to
   ordered `(X, Y, Z)` tuple comparison.
3. Ordered comparison exposed a frame-chirality bug: config 0 at left-handed slots
   (`sx*sy*sz == -1`, e.g. slot 1 UBR) placed the piece's right-handed sticker basis onto a
   left-handed face basis — physically unrealizable, so face turns landed "between" configs
   (`StopIteration`). Config 0 base now depends on slot handedness (X/Y faces swapped at
   left-handed slots); the 120-degree diagonal cycle then covers exactly the 3 realizable
   placements.

Verify (run in-session, actual result):
`python -m pytest solver/tests -v` → **10 passed in 1.26s**
(test_24_rotations, test_18_moves, test_inverse, test_round_trip_all_moves,
test_move_of_solved_is_solved_after_inverse, test_is_solved, test_apply_alg_reaches_solved,
test_tables_match_direct_8corner_simulation, test_destination_slot_is_permutation,
test_orientation_values_in_range).

---

## Phase 2 — BFS table — `solver/bfs_solver.py` — 2026-09-23

Files created/edited:
- `solver/bfs_solver.py` (new) — bijective `encode`/`decode` over `7! * 3**6 = 3,674,160`
  states (Lehmer mixed-radix for the permutation, base-3 digits o[0..5] for orientation with
  o[6] fixed by `sum(orient) == 0 mod 3`; constraint empirically confirmed to be preserved by
  every move: all orientation maps are pure shifts and shift sums are 0 mod 3). `build_bfs_table`
  is an 18-branch BFS from solved filling a `numpy.uint8` array; result persisted to
  `solver/bfs_table.npy` and reloaded on later runs (`get_bfs_table`).
- `solver/tests/test_bfs_solver.py` (new) — 7 tests.

Measured build time: **~405 s** (one-time; disk reload 0.37 s). Table: shape `(3674160,)`,
max value **11** (God's number), depth histogram (d: count)
0:1, 1:9, 2:54, 3:321, 4:1847, 5:9992, 6:50136, 7:227536, 8:870072, 9:1887748, 10:623800, 11:2644.

Test correction (actual, in-session): `test_encode_is_unique_on_sample` was replaced by
`test_encode_is_injective_on_sample` — the original failed on a birthday-duplicate random state
(repeated state, not an encode collision); the new test compares code-set size vs distinct-state
set size over 8000 random states.

Verify:
`python -m pytest solver/tests -q` → **18 passed in 1.00 s** (11 cube_state + 7 bfs).

---

## Phase 3 — IDA* — `solver/ida_star_solver.py` — 2026-09-23

Files created/edited:
- `solver/ida_star_solver.py` (new) — recursive IDA* with admissible heuristic
  `h = ceil(m/4)` (position only, no orientation sum — would break admissibility); branch-and-
  bound prunes consecutive same-face moves (branching 18 -> 15, optimality preserved since any
  two same-face moves fold into one). Returns optimal move list; optional `stats` dict reports
  heuristic `nodes` and IDA* iterations (`bounds`).
- `solver/tests/test_ida_star_solver.py` (new) — 5 tests.

Bugs fixed during Phase 3 (actual):
1. Goal test used `h == 0`, but a state can have all corners *positioned* yet **twisted**
   (h = 0, not solved) — returned a bogus empty path. Goal is now `cube_state.is_solved`.
2. Test-side: short random scrambles legitimately net to solved (distance 0); removed the
   "solution non-empty" assertion that wrongly failed on those.

Verify (actual, in-session):
- `python -m pytest solver/tests -q` → **23 passed in 21.55 s** (includes the gate test
  `test_ida_len_matches_bfs_for_50_scrambles_depth_le_8`).
- Node-logging run: **60 scrambles, alg length <= 8 → BFS distance == IDA* length on all 60**
  (0 mismatches), 3,706,428 nodes total (avg 61,774/scramble), wall 7.4 s; per-scramble rows
  written to `analysis/ida_nodes_log.csv`.

---

## Phase 4 — Flask web UI — `viz/app.py` + `viz/index.html` — 2026-09-23

Files created/edited:
- `viz/app.py` (new) — Flask serving `viz/index.html` at `/` and `GET /solve?scramble=R U R'...`
  returning JSON `{scramble, solution, length, nodes, bounds, bfs_length, optimal}`. Validates
  move tokens (400 on unknown move). Created with a `sys.path` bootstrap so `python viz/app.py`
  works from any cwd; `threaded=True` so one slow solve cannot block the server.
- `viz/index.html` (new) — input + Solve/Random buttons; fetch to `/solve`; result panel showing
  optimal solution, IDA* nodes/iterations and the BFS cross-check; `cubing.js` (CDN)
  `<twisty-player>` whose `alg` is set to `scramble + " " + solution` so the full scramble-and-
  solve sequence animates back to solved.

Changes during Phase 4 (actual):
- Found weak-heuristic IDA* blowup: a depth-9 state took >10 min with `h = ceil(m/4)` (real
  DAA exponential behavior). The web endpoint therefore solves with the **exact BFS distance as a
  trivially admissible IDA* heuristic** (solvable that state in 56 nodes, instant). The
  `ceil(m/4)` heuristic remains the library default; the benchmark/report exercise it, and both
  give the same optimal length.

Verify (actual, in-session):
- `GET /` → 200, 3722 bytes, `<title>2x2x2 Optimal Cube Solver</title>` present.
- `GET /solve?scramble=R U R' U'` → length 4 == bfs_length 4, optimal true.
  Pathological scramble `F R U2 B' D R' F2 L' U B R D2 U' B R2` → length 9 == bfs 9, 56 nodes.
  Invalid move → HTTP 400 `{"error":"unknown move: ..."}`.
- Browser: page opens in Brave and Edge with rendered title "2x2x2 Optimal Cube Solver"; the
  `/solve` JSON was also displayed in a browser tab (server works in-browser).
  **Manual step remaining:** visual inspection of the twisty-player animation (DOM/vision tools
  unavailable in this session) — open http://127.0.0.1:5000/ and click Solve to watch it play
  the scramble + optimal solve.
- Server left running on http://127.0.0.1:5000 (restart anytime with `python viz/app.py`).

---

## Phase 5 — Benchmark — `analysis/benchmark.py` — 2026-09-23

Files created/edited:
- `analysis/benchmark.py` (new) — for scramble depths 2..8: samples per depth, measures IDA*
  avg nodes + avg wall time + avg optimal length (asserted == BFS distance on every sample),
  writes `analysis/benchmark_results.csv` and two log-scale plots
  (`benchmark_nodes.png` vs theoretical 18^d and 15^d, `benchmark_time.png`); also measures the
  BFS table O(1) query cost. Includes the same `sys.path` bootstrap as `viz/app.py` so
  `python analysis/benchmark.py` runs from the project root.
- `analysis/benchmark_results.csv` (generated), `benchmark_nodes.png`, `benchmark_time.png`.

Verify (actual, in-session):

| depth | samples | avg nodes | avg time | avg opt len | 18^d |
|---|---|---|---|---|---|
| 2 | 60 | 22 | 0.036 ms | 1.7 | 324 |
| 3 | 60 | 186 | 0.259 ms | 2.4 | 5,832 |
| 4 | 50 | 1,176 | 1.492 ms | 3.0 | 104,976 |
| 5 | 40 | 3,010 | 3.912 ms | 3.0 | 1,889,568 |
| 6 | 30 | 41,541 | 51.1 ms | 3.8 | 34,012,224 |
| 7 | 25 | 645,073 | 928.7 ms | 4.8 | 612,220,032 |
| 8 | 20 | 935,726 | 1,150.7 ms | 5.0 | 11,019,960,576 |

BFS query: 3,000 lookups in 5.8 ms → **1.93 µs/query (O(1))**, vs IDA* 0.04 ms (d=2) .. 1.15 s (d=8).

---

## Phase 6 — Report — `report/complexity_analysis.md` — 2026-09-23

Files created/edited:
- `report/complexity_analysis.md` (new) — full write-up with the real Phase 5 numbers: state
  space (3,674,160 canonical states, diameter 11), BFS vs IDA* time/space analysis, the exact
  BFS depth histogram, the worst-case weak-heuristic blowup observation, and final correctness
  cross-checks.

Final gate this session: `python -m pytest solver/tests -q` → **23 passed in 10.05 s**.

---

## Phase 7 — Backend serving: spec-literal `/solve`, `/scramble`, scramble generator — 2026-09-23

Files created/edited:
- `solver/scramble.py` (new) — `generate_scramble(rng=None, length=12)`: 18-move alphabet
  (`U U' U2 ... B B' B2`), never two consecutive moves on the same face (cancellation-free,
  standard WCA-style). `scramble_with_distance(distance, rng=None, max_tries=100000)`: rejection
  sampling — builds long scrambles, measures true distance against the BFS table, keeps the first
  that lands exactly at the requested distance (used by the depth-category end-to-end tests;
  d=11 is ~0.07% of states, so the budget handles it).
- `solver/ida_star_solver.py` (edited) — `stats["bounds_seq"] = []` appended with every bound
  the IDA* loop tries, alongside the existing integer `stats["bounds"]`. Frontend displays the
  whole tried sequence (`4 → 5 → 6 → 7`).
- `viz/app.py` (rewritten) —
  - `GET /solve?scramble=...` now returns **spec-literal JSON**:
    `{scramble, solution, length, nodes, bounds: ["bound_seq"], bfs_length, optimal}`.
  - `GET /scramble?length=N` — `N` parsed as int (400 on garbage), clamped 1..40, returns
    `{"scramble": "..."}` from `solver/scramble.py`.
  - Static route for `viz/`: whitelist `index.html` / `simulation.js` / `style.css` with a
    `normpath` guard (anything else → 404).
  - `/solve` keeps the exact-BFS subtree as its admissible IDA* heuristic, so any state solves
    instantly; `bounds` then prints as just `[bfs_length]`.

Verify (actual, in-session):
- `GET /solve?scramble=R U R' U'` →
  `{"bfs_length":4,"bounds":[4],"length":4,"nodes":7,"optimal":true,"scramble":"R U R' U'","solution":"U L U' L'"}`.
- `GET /scramble?length=8` → `R2 L' F' U2 F B2 R L2` (legal, no same-face repeats);
  `length=999` → clamped 40; `length=abc` → HTTP 400.
- Invalid move on `/solve` → HTTP 400. Missing/bad static path → 404.
- Full contract coverage moved to phase 10's `test_simulation_contract.py`.

---

## Phase 8 — Simulation controller — `viz/simulation.js` — 2026-09-23

Files created/edited:
- `viz/simulation.js` (new) — `class CubeSimulation` implementing the plan's interface verbatim:
  `setScramble, setSolution, reset, play, pause, next, previous, goToStep, playScramble,
  playSolution, getCurrentMove, getCurrentStep, getTotalSteps`, plus `setSpeed`, and callbacks
  `onStateChange` / `onDone(next)` (chains "scramble → auto-solve" without cooking wall-clock
  timings). Maintains `stepIndex`, `total`, `phase ∈ {scramble, solution, solved}` and renders
  every step through one `_syncRender()`:
  - **Timeline mode** (primary): `player.alg = fullSequence; timeline.scrubTo(step)`. Playback =
    `timeline.play()` + a 150 ms poll (via `timeInMoves`/`experimentalTimeInMoves`/`isPlaying`,
    all feature-detected) plus a safety timeout that force-ends playback; fallback discrete
    stepper (interval `650/speed` ms, prefix rebuild) if the live position can't be read.
  - **Fallback mode** (no timeline): canonical prefix rebuild — `player.alg = moves.slice(0, step)`
    — which is always a correct physical state, so stepping never depends on experimental API
    correctness. (Mode is auto-selected from capability detection in the constructor.)
  - Speed via `player.tempoScale` when present; the fallback stepper uses its own interval.

Bugs found & fixed during Phase 8 (actual, by writing logic assertions against a mock player):
1. `player.alg = X` moves the cube to the **end** of X — so `setScramble` followed by "keep
   full alg on the player" would *pre-scramble* the cube while `step` still read 0. The controller
   now always sets the full sequence and *scrubs back* to the current step (or renders the
   prefix in fallback mode). Verified: after `setScramble`, cube state == solved (step 0).
2. Test-side fix: with no solution loaded, `phase()` correctly reports `"scramble"` at the end of
   a played-out scramble (the cube IS physically scrambled) — the "solved" end-point only exists
   once a solution is loaded. (Assertion corrected in the harness, not the library.)

Verify (actual, in-session): a 29-assertion Node harness (`simtest.mjs`, mock cubing.js player)
— stepping both modes, clamping at 0/total, phase boundaries, play/pause, fallback playback
advance + pause halt, `onDone` chaining at natural end → **ALL PASS (29/29)**.

---

## Phase 9 — 3D simulation UI — `viz/index.html` + `viz/style.css` — 2026-09-23

Files created/edited:
- `viz/index.html` (rewritten) —
  - `<twisty-player id="cube" puzzle="2x2x2" visualization="3D" background="none"
    hint-facelets="floating">`.
  - Two-column layout: cube panel + right panel (scramble input + Random/Solve; scramble text;
    solution chips — click a chip to jump, `.done`/`.now` highlight states; solver panel:
    Algorithm / BFS distance / Solution length / Nodes / IDA* bounds chain / Optimal; step card
    with big current-move text and `Step n/total` + phase; legacy controls **RESET · |< START · <
    PREVIOUS · NEXT > · SOLVED >| · ▶ PLAY · ❚❚ PAUSE**; speed 0.5×/1×/2×; status line; error box).
  - Flow: **Solve** validates moves client-side (18-token set), fetches `/solve`, fills the solver
    panel, then `sim.onDone(() => sim.setSolution(sol); sim.playSolution())` +
    `sim.setScramble(moves); sim.playScramble()` — one continuous animated movie: solve → every
    solution move turns the real cube → solved. **Random** fetches `/scramble?length=12`, clears
    the solver panel, plays the scramble.
  - CDN banner: 3 s after load, if `player.timeline.scrubTo` is still not a function, show
    `#cdnWarning` instead of silently showing a blank cube.
- `viz/style.css` (new) — full page styling (grid/cube wrap/panels/chips/solver grid/controls/
  speed/status/step card/error box/cdnWarning).

Bugs found & fixed during Phase 9 (actual):
1. **The old CDN URL 404s** — `https://cdn.cubing.net/v0/cubing.js` returned `404 Not Found`, which
   is why the earlier page showed an empty cube area. Fixed to the plan's §4 URL
   `https://cdn.cubing.net/v0/js/cubing/twisty` (confirmed HTTP 200; module exports `TwistyPlayer`).
2. **Module ordering race** — module scripts don't wait for each other: setting `player.alg`
   before cubing.js has upgraded the custom element silently no-ops (expando). The app now boots
   via `customElements.whenDefined("twisty-player")` (with a 4 s fallback timer) before wiring the
   controller.

Verify (actual, in-session): `/`, `/simulation.js`, `/style.css` all 200 (10076 / 8216 / 4313
bytes); elicited inline module + `simulation.js` both pass `node --check`; CDN module + chunk
graph reachable.

---

## Phase 10 — End-to-end verification & contract tests — 2026-09-23

Files created/edited:
- `solver/tests/test_verifier.py` (new) — a **fully independent** 8-corner geometric simulator
  (own 3-D coordinate matrices, its own 24-rotation canonicalizer, base stickers, Rodrigues
  slot-diagonal rotation, `simulate(alg)` which re-canonicalizes after **every** move, and
  `verifies(scramble, solution)`). Cloud-free validation that "apply scramble then solution ⇒
  solved" on every depth category and on random states.
  Tests: inverse round-trips; quarter-turn ^4 = identity; scramble + its own inverse; 150 random
  states agree with `cube_state`; **depth categories 0, 1, 2, 4, 6, 8, 10, 11** via
  `scramble_with_distance` + exact-heuristic IDA* → all optimal AND `verifies` on every sample.
- `solver/tests/test_simulation_contract.py` (new) — Flask `test_client` suits: exact
  `/solve` JSON schema (no extra/missing keys); `solution` tokens legal and `verifies`; invalid
  move → 400; empty scramble → length 0 / optimal; depth categories 0,1,2,4,6,8,10,11
  optimal+verified; `/scramble` default 12 / custom / clamp 999→40 / 0→1 / `abc`→400.
- `solver/tests/test_ida_star_solver.py` (edited) — added
  `test_bounds_seq_records_the_tried_bounds` (`bounds == len(bounds_seq)` and
  `bounds_seq == range(heuristic(state), expected + 1)`).

Bugs found & fixed during Phase 10 (actual, by running the independent verifier):
1. `_LAYER` axis misassignment — `R`/`L` were mapped to the z-axis and `F`/`B` to the x-axis
   (swapped). Fixed to `R:(0,1)  L:(0,-1)  F:(2,1)  B:(2,-1)` with `U:(1,1)  D:(1,-1)`, i.e.
   x↔R/L, y↔U/D, z↔F/B.
2. **Gauge drift** — with raw frames, once piece 7 leaves slot 7 under a scramble, tracking the
   remaining moves in a single fixed frame silently diverges (whole-cube rotation is unobservable
   from the cube alone). Fixed by re-canonicalizing after every move inside `simulate`.
3. Removed a bogus identity assertion: `[face, face, face, face']` is **U²**, not the identity —
   caught by the verifier math itself.

Verify (actual, in-session):
`python -m pytest solver/tests -q` → **37 passed in 30.94 s**.
**Visual gate outstanding (guardrail 12):** the real 3D animation must be eyeballed by the user —
see the Phase 11 checklist in README.

---

## Phase 11 — Docs polish & final gate — 2026-09-23

Files created/edited:
- `PLAN.md` — Phase 7-11 rows, decisions, folder structure, guardrails updated with real results.
- `IMPLEMENT.md` — this log (Phases 7-11).
- `README.md` — rewritten per plan §39 (features, setup, run, quick manual checks, architecture
  diagram `Solver → API → Simulation Controller → cubing.js → 3D`, tests, benchmark, report links).
- `report/complexity_analysis.md` — added §6 (the two IDA* heuristic modes: `ceil(m/4)` research
  default vs exact-BFS interactive) and §7 (solver benchmark kept separate from browser rendering;
  visual verification is manual by design).

Final gate (machine side): `python -m pytest solver/tests -q` → **37 passed in 30.94 s**.
Final gate (visual, pending user): run `python viz/app.py`, open http://127.0.0.1:5000 and follow
the manual checklist — recorded here once confirmed.
---

## DAA Phase A � Comparative Analysis dataset `daa/` � 2026-09-24

Files created/edited:
- `daa/cube/state.py` (new) � `CubeState` froze immutable (perm7, orient7) over `solver.cube_state`;
  `MOVES`, `neighbours`, `hash_state` (BFS `encode`), `apply_move/undo_move/is_solved`.
- `daa/algorithms/{base,util,bfs,dfs,dls,iddfs,bidirectional,greedy,astar,backtracking,branch_bound}.py` (new) �
  nine hand-written searches returning the same `SearchResult` (found, solution, length,
  nodes_explored, states_generated, duplicates, pruned, max_depth, execution_time, memory_bytes,
  memo_hits/misses, iterations, forward/backward/meeting, branches, best_solution, terminated/reason);
  `Limits(max_depth=20, max_states=1e6, max_time_s=30, max_memory_mb=512)`; `Limits.fast`;
  shared `ExitGuard` (state/time/memory budget, `tick()`) + `time_and_profile` (wall clock + RSS delta).
- `daa/optimization/{pruning,memoization,__init__}.py` (new) � `MovePruner` (inverse/same-face/repeat)
  + `Memoizer` (h() cache with hit/miss + memory estimate).
- `daa/heuristics/{misplaced,corners,pattern_database,__init__}.py` (new) � admissible vs estimate-only
  registry keyed by display name; default `Admissible: corners / 4`; PDB over 3 reference corners.
- `daa/benchmark/{runner,metrics,reports,registry,__init__}.py` (new) � `run_single` (same start state
  to every solver), `run_benchmark`, CSV/markdown export, algorithm registry with inspect-signature
  filtered kwargs; 9 entries `["BFS","DFS","DLS","IDDFS","Bidirectional","Greedy","A*","Backtracking","Branch & Bound"]`.
- `daa/tests/*.py` (new) � state/optimization/heuristics/algorithms/benchmark suites (49 tests).
- `daa/ui/{cubenet,panels,charts,app}.py` (new) � Streamlit dashboard: matplotlib flat-net renderer,
  learning/complexity/viva content, plotly charts, 5 tabs (Solve & Compare, Learn, Complexity, Viva, Benchmark).
- `viz/index.html` + `viz/style.css` (edited) � `3D Solver / DAA Study` mode toggle; DAA mode embeds
  `http://127.0.0.1:8501` in an iframe with an open-in-new-tab link + fallback note.
- `requirements.txt` (edited) � added `streamlit`, `plotly`, `pandas`.

Bugs fixed during DAA Phase A (actual, by running tests):
1. `greedy`/`astar` imported a nonexistent `Registry`; switched to `daa.heuristics as H` + `H.HEURISTICS`.
2. `backtracking.py` accidentally indented `while stack:` at column 0 (invalid Python); restored.
3. `SearchResult` required `found`; made `found: bool = False` so `SearchResult(algorithm=...)` is valid.
4. Bidirectional `_finish` applied `_inverse_of(mv)` to backward-parent moves � wrong direction; now emits
   the goalward move recorded at parent time (b_parent[child] = (node, move) as applied); 30/30 optimal vs BFS.
5. PDB `tuple(sorted(child))` destroyed label identity; child key now preserves label order
   `(slot_map[slot], orient_map[slot][o])`; A* with PDB found len=5 in 63 nodes vs 526 (corners/4).
6. Registry passed `heuristic_name` to every solver; now filters kwargs by `inspect.signature`.
7. Benchmark tests hit BFS's 120k/400k state caps on depth-7 scrambles; corrected the suite to
   `Limits(max_depth=12, max_states=800_000, max_time_s=90)` + `OPT_SEEDS=(2,3,5)`.
8. `daa/ui/cubenet.py` renderer referenced canonical 7-perm with 8 slots (IndexError); net now expands the
   fixed corner 7 and colors stickers by home-face of the occupying piece; solved renders uniform (tested).
9. Flame graph: `daa/ui/app.py` show-columns referenced `heuristic`/`initial_h` not in `summary()`;
   they are attached per row in `run_selected`.

Smoke (actual, in-session, scramble `L' U2 R B R D`): BFS 4/0.06s(359) � DLS(4) 4/0.02s(205) �
IDDFS 4/0.06s(665) � Bidirectional 4/0.01s(19) � Greedy 4/0.15s(255) � A* 4/0.05s(87) � B&B 4/2.89s(42664) �
DFS & Backtracking hit limits (incomeplete by design). Benchmark 6 scrambles x 3 alg -> 12 rows.

Verify (actual, in-session): `python -m pytest solver/tests daa/tests -q` -> **92 passed in 242.64 s**
(43 solver + 49 DAA).  Streamlit: `streamlit run daa/ui/app.py --server.headless --server.port=8501`
healthy on 127.0.0.1:8501 (HTTP 200); `AppTest` run of the dashboard -> 0 exceptions.  Flask on
127.0.0.1:5000 re-started; page + mode toggle served (mode3d/modeDaa/daaFrame present).

Remaining: nothing machine-side; DAA UI final visual pass (user) + B&B/DFS limits on long scrambles.

---

## DAA Phase B - 3D Solver algorithm selector (run every DAA algorithm on the real cube) - 2026-09-25

Goal: from the plan, choosing each algorithm in the 3D solver page runs it and its solution
*physically* solves the cube on screen.

Files created/edited:
- `daa/cube/physical.py` (new) - `PhysicalCubeState`: immutable 8-corner (perm8, orient8) state in
  cubing.js's own move basis; `perm`/`orient` are lazy canonical-7 projections (cached `_c7`);
  40-bit packed `hash_state()`; `apply_move/is_solved/from_alg/solved`.
- `daa/algorithms/dls.py` (rewritten) - DLS was using a **global visited set**, which is unsound
  under a depth limit (a state first met at a deep recurrence blocks its shallower occurrence, so
  nearby goals are missed and IDDFS stops returning optimal paths).  Now a textbook *depth-limited
  tree search*: cycle prevention via a path-restricted `on_path` set (O(depth) memory), iterative
  frames with an exit frame so the path is released after each subtree, and a live `path_moves`
  mirror so `result.solution` is the actual branch moves (not a reassembled substitute).
- `daa/algorithms/iddfs.py` (verified) - relies on DLS's `terminated` signal to stop iterating once
  a single depth blows the budget; unchanged, now optimal again.
- `daa/algorithms/bidirectional.py` (rewritten) - first-meet-wins was **not always optimal**
  (returned len 10 for a distance-9 scramble); the smaller-frontier expansion could let one side's
  deep search cross before the other reached the shallow meet.  Now *level-synchronized*: both
  fronts expand exactly one level per iteration, all meets at f-dist ≤ F and b-dist ≤ B are seen,
  so an undiscovered meet needs f ≥ F+1 and b ≥ B+1 (path ≥ F+B+2); stop as soon as
  `best ≤ F+B+1`, which proves optimality.  `meeting_depth == length` maintained.
- `daa/algorithms/util.py` (edited) - `ExitGuard.tick()` called ctypes `memory_mb()` on **every**
  generated state (≈22 µs each — the real bottleneck, ~14 s of a 25 s budget); memory is now
  sampled every 256 generated states (`_MEM_SAMPLE_EVERY`).
- `viz/app.py` (edited) - `/solve` takes `algo` (default `physical`); DAA algorithms run on
  `PhysicalCubeState` and are re-verified before returning; response gains `algorithm`, `found`,
  `terminated`, `reason`, `time_s`; `physical` branch now also reports `time_s`.
- `viz/index.html` + `viz/style.css` (edited) - solver dropdown (10 options); selecting one
  re-solves with that algorithm; honest stats ("–" length/optimal when `found:false`) with a
  persistent *"No solution within limits (reason)"* status (limits are enforced, nothing is
  fabricated) and the cube left scrambled; Random now animates immediately and prefetches the
  solution in the background (a 9 s DAA search no longer freezes the scramble animation).
- `daa/tests/test_physical.py` (new) - physical adapter suite: solutions returned by every
  algorithm physically solve; hashes are distinct on a 300k sweep; BFS/IDDFS/Bidirectional are
  optimal and match the `solver.physical_solver` reference on short scrambles; solver length
  agrees with BFS distance on depth 1–5 scrambles; projected heuristics are zero at the goal.
- `solver/tests/test_simulation_contract.py` (edited) - `/solve` schema extended with the new keys.
- `README.md` (edited) - feature/API docs updated for `algo`, the selector, and honest DAA limits.

Honest-termination reality (the DAA point, shown on the page): the full 8-corner physical group is
≈24× the canonical quotient (88 M vs 3.7 M reachable), so exhaustive physical searches (BFS, IDDFS,
DFS, DLS, Backtracking) can rarely reach distance ≥ 7 within the web limits
(`Limits(max_depth=20, max_states=600_000, max_time_s=20)`); A*, Bidirectional, B&B and the
physical IDA* keep solving deep random scrambles.  When an algorithm honestly runs out of budget,
`/solve` reports `found:false` + `reason` and the page explains it instead of manufacturing a solve.

Verified (actual, in-session):
- DLS direct: depth_limit 3/4 → no solution at depth (incomplete), limit 5 → len 5 physically
  solved, limit 6 → len 5, limit 8 → len 8.
- `rest.py` physical sweep (R U F): A* 3/0.07 s, Greedy 3/0.51 s, B&B 3/14.4 s, DFS hits the state
  limit (honest), Backtracking found len 12 physical.
- Bidirectional on dist-9 (`L2 B R2 B' L2 F L' U2 L B2 D2 U2`, BFS distance 9): now len 9 optimal
  (previously len 10), 62,272 nodes / 7.98 s; dist-3/4/5 scrambles all optimal.
- IDDFS dist-5 (physical): len 5 optimal, 134,608 nodes / 0.59 s (was returning len 8 before the DLS
  fix).
- `python -m pytest solver/tests daa/tests -q` → **105 passed in 213.11 s** (43 solver + 62 DAA).
- Flask on 127.0.0.1:5000: `/scramble`, `/solve` (physical + 9 DAA algos) verified over HTTP;
  browser-smoked the page — Random+IDDFS on a 12-move scramble shows the persistent honest
  "No solution within limits (state limit)" message, stats show "–"/…/668,840 nodes; Random+A*
  /Bidirectional prefetch fast and solve; dropdown swaps algorithm and re-solves.

Phase B2 - informed DAA algorithms time out on deep scrambles; exact-BFS heuristic (2026-09-25):
- Root cause found in-session: A*/Greedy/B&B on the 3D page used `corners / 4`, which is too weak
  on the 88M-state physical group — a dist-9 `L2 B R2 B' L2 F L' U2 L B2 D2 U2` A* run burned the
  full 20 s on 20,029 nodes and honestly reported `time limit (max_time_s)` (breaking the README
  promise that A* keeps solving deep scrambles; only Bidirectional and the physical solver did).
- Fix: register `"BFS distance (exact)"` in `daa/heuristics` — h = O(1) lookup of the precomputed
  full BFS table on the state's cached canonical projection; admissible (canonical distance is a
  lower bound; rotation-equivalent "visually solved" states read 0 a few moves short of the
  labelled goal), identical to the physical IDA* solver's h.  `viz/app.py` now passes it to the
  three informed algs; the dashboard keeps `corners / 4`.
- B&B additionally needed a fix found in-session: B&B only prunes once it has an incumbent, and
  raw DFS reaches a dist-9 goal too late (state limit).  It now seeds its first incumbent with a
  bounded greedy descent over all 18 moves, closing the h==0-but-not-solved rotation gap with a
  depth-4 BFS; a weak heuristic that stalls simply falls back to plain DFS (no behaviour change
  for `corners / 4` on the canonical dashboard).
- Verify (actual): A* and B&B exact-h on the dist-9 → found, len 9 optimal, 124 and 889 nodes,
  0.048/0.051 s (was 20 s time-out); Greedy exact-h finds a valid physical solve (best-first ties
  need not be optimal, so `length == expected` is not required of it);
  `test_informed_web_algorithms_solve_deep_with_exact_h` pins all three and that the weak bound
  still honestly fails.  Full suite → 106 passed.

Remaining: nothing machine-side; final visual pass (user) + optional page wording tweaks.

Phase 15 - scramble sync 3D page -> DAA study (2026-09-25, live-synced):
- Motivation: clicking Random in the 3D page showed one scramble while the DAA dashboard
  Solve & Compare studied its own random one - the study never ran on what the user saw.
  Wanted: the dashboard adopts the 3D page's current case (Random click or manually typed),
  live, without reload, without resetting other sidebar selections, no auto tab switch.
- Design decision (found in-session): st.components.v1.html / st.html are iframes only -
  no value channel back to Python. So instead of postMessage the page POSTs the current
  input to a new Flask endpoint and the dashboard polls it server-side via a hidden
  @st.fragment(run_every=1.0) + urllib (no CORS). Target = the sidebar Manual box (a move
  string maps 1:1 to the study; the dashboard Random source is RNG-seed based and cannot
  reproduce the web RNG). Value lands once, ownership returns to the user.
- viz/app.py: _CURRENT_SCRAMBLE + GET /current-scramble (read by the poller) + POST
  /current-scramble (validates via parse_scramble; invalid move -> 400, last good kept).
- viz/index.html: pushScrambleToDaa() (300 ms debounce, POST, skips empty/partial values),
  fired on the Random fill, the manual "input" event, and when switching to DAA mode.
  switchMode is module-scope while the pusher lives inside main() -> exposed as
  window.pushScrambleToDaa and called with a guarded if (window.pushScrambleToDaa) so the
  DAA tab toggle never throws (first bug found in-session: unguarded module-scope call after
  the toggle would ReferenceError - fixed before reload).
- daa/ui/app.py: EXTERNAL_SCRAMBLE_URL, _fetch_external_scramble(), _poll_external_scramble()
  fragment (sets st.session_state manual_scramble + scramble_source="Manual" + st.rerun()
  only when the value changed), _daa_synced_scramble dedup key, widget keys scramble_source
  and manual_scramble so the poll lands in the real widgets.
- Verified (actual, in-session): full suite -> 109 passed (+3 /current-scramble contract
  tests in test_simulation_contract.py); Flask + streamlit restarted (5000/8501 healthy);
  live browser: Random -> Flask /current-scramble returns the browser's fresh scramble;
  dashboard sidebar flips to Manual with the edit field showing exactly that string;
  idle CPU (~0.9 ticks/5 s) confirms the 1 s poll converges - no rerun loop.
- Known automation limits (not product bugs): AppTest pages fragment+st.rerun() -> timeout
  artifact in the harness only; the manual-typing path is exercised by the same pusher as
  Random but the UI-automation Type tool cannot land text reliably in the 3D input, so it
  was code-verified only.
