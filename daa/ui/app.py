"""Streamlit dashboard: Rubik's Cube 2x2x2 — Comparative DAA Study.

Tabs
----
* **Solve & Compare** — run the selected algorithms on one scramble and compare
  the *measured* metrics (same start state for every algorithm).
* **Complexity** — text-book theoretical table (labelled separately from the
  measured numbers).
* **Benchmark** — many scrambles × algorithms, CSV + markdown export.

Run with:  ``streamlit run daa/ui/app.py``
"""

from __future__ import annotations

import json
import random
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from daa.algorithms.base import Limits, apply_alg, verify_solution
from daa.benchmark.registry import ALGORITHMS, run_algorithm
from daa.benchmark.reports import results_to_csv, results_to_markdown
from daa.benchmark.runner import run_benchmark, run_single
from daa.cube.state import CubeState
from daa.heuristics import HEURISTICS, default as default_heuristic
from daa.optimization.memoization import Memoizer
from daa.optimization.pruning import MovePruner
from daa.ui.charts import comparison_bar, iterations_plot
from daa.ui.cubenet import render_state
from daa.ui.panels import COMPLEXITY

st.set_page_config(page_title="2x2x2 — DAA Comparative Study", layout="wide")

ALG_KEYS = list(ALGORITHMS.keys())
HEUR_NAMES = list(HEURISTICS.keys())
VALID = set(
    "U U' U2 D D' D2 L L' L2 R R' R2 F F' F2 B B' B2".split(" ")
)

# The 3D page mirrors the case in its scramble input (Random click / manual
# typing) to this endpoint; this dashboard polls it so both views study the
# exact same scramble.  Server-side fetch, so no CORS / browser involvement.
EXTERNAL_SCRAMBLE_URL = "http://127.0.0.1:5000/current-scramble"


def _fetch_external_scramble() -> str:
    """Read the 3D page's current scramble; "" when unavailable (standalone)."""
    try:
        with urllib.request.urlopen(EXTERNAL_SCRAMBLE_URL, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(data.get("scramble", "")).strip()
    except Exception:
        return ""


@st.fragment(run_every=2.0)
def _poll_external_scramble() -> None:
    """Live-sync the 3D page's case into this app (no reload, no resets)."""
    value = _fetch_external_scramble()
    if not value:
        return
    applied = st.session_state.get("_daa_synced_scramble", "")
    if value != applied:
        st.session_state["_daa_synced_scramble"] = value
        st.session_state["manual_scramble"] = value
        st.session_state["scramble_source"] = "Manual"
        st.rerun()


def parse_input(text: str) -> list[str] | None:
    tokens = text.strip().split()
    for t in tokens:
        if t not in VALID:
            st.error(f"Unknown move: {t!r}")
            return None
    return tokens


@st.cache_data(show_spinner=False)
def _cached_moves(seed: int, length: int) -> list[str]:
    rng = random.Random(seed)
    faces = "UDLRFB"
    out: list[str] = []
    last = None
    for _ in range(length):
        while True:
            f = faces[rng.randrange(6)]
            if f != last:
                break
        last = f
        out.append(f + rng.choice(("", "'", "2")))
    return out


def build_state_from_sidebar() -> tuple[CubeState, list[str]]:
    mode = st.sidebar.radio("Scramble source", ["Random", "Manual"],
                            horizontal=True, key="scramble_source")
    moves: list[str] | None
    if mode == "Random":
        length = st.sidebar.slider("Scramble length", 2, 12, 7)
        seed = st.sidebar.number_input("Seed", 0, 1_000_000, 1,
                                       key="scramble_seed")
        moves = _cached_moves(seed, length)
    else:
        text = st.sidebar.text_input(
            "Move sequence (spaces)",
            value="L' U2 R B R D",
            key="manual_scramble",
            help="U D L R F B each with '', '2' or plain suffix.",
        )
        moves = parse_input(text)
        if moves is None:
            st.stop()
    start = CubeState.solved()
    for m in moves:
        start = start.apply_move(m)
    return start, moves


def build_pipeline() -> dict:
    left, mid, right = st.sidebar.columns(3)
    with left:
        p_inverse = st.checkbox("Inverse pruning", value=True)
        p_face = st.checkbox("Same-face pruning", value=True)
    with mid:
        p_repeat = st.checkbox("Repeat pruning", value=True)
        use_memo = st.checkbox("Memoization", value=True)
    with right:
        max_depth = st.number_input("Max depth", 1, 40, 20)
        max_states = st.number_input("Max states (k)", 1, 5000, 1000) * 1000
    max_time = st.sidebar.slider("Max time (s)", 1.0, 120.0, 60.0)

    limits = Limits(max_depth=max_depth, max_states=int(max_states),
                    max_time_s=max_time)
    pruner = MovePruner(inverse_move=p_inverse, same_face=p_face,
                        consecutive_repeat=p_repeat)
    return {
        "limits": limits,
        "pruner": pruner,
        "use_memo": use_memo,
        "heuristic_name": st.sidebar.selectbox("Heuristic", HEUR_NAMES,
                                               index=HEUR_NAMES.index(
                                                   default_heuristic())),
    }


def make_memo(heuristic_name: str):
    return Memoizer(HEURISTICS[heuristic_name].fn)


def run_selected(alg_names: list[str], start: CubeState, pipe: dict,
                 with_dht_limit: int | None = None) -> pd.DataFrame:
    rows = []
    pbar = st.progress(0.0, "running…")
    for i, key in enumerate(alg_names):
        entry = ALGORITHMS[key]
        memo = make_memo(pipe["heuristic_name"]) if (
            use_memo := pipe["use_memo"]) else None
        res = run_algorithm(
            key,
            start,
            limits=pipe["limits"],
            pruner=pipe["pruner"],
            memoizer=memo,
            heuristic_name=pipe["heuristic_name"]
            if entry["needs_heuristic"] else None,
            depth_limit=with_dht_limit,
        )
        d = res.summary()
        d["class"] = "informed" if entry["needs_heuristic"] else "blind"
        d["admissible"] = (
            HEURISTICS[pipe["heuristic_name"]].admissible
            if entry["needs_heuristic"] else None
        )
        d["solution"] = " ".join(res.solution)
        d["verified"] = bool(res.solution) and verify_solution(
            _last_scramble, res.solution)
        d["memo_hit_rate"] = (
            res.memo_hits / max(1, res.memo_hits + res.memo_misses)
            if memo is not None else None
        )
        d["iterations"] = res.iterations
        d["forward_states"] = res.forward_states
        d["backward_states"] = res.backward_states
        d["meeting_depth"] = res.meeting_depth
        d["branches_explored"] = res.branches_explored
        d["branches_pruned"] = res.branches_pruned
        d["best_solution"] = " ".join(res.best_solution)
        d["lower_bound"] = res.lower_bound
        d["initial_h"] = res.initial_h
        d["heuristic"] = res.heuristic
        rows.append(d)
        pbar.progress((i + 1) / len(alg_names))
    pbar.empty()
    return pd.DataFrame(rows)


_last_scramble: list[str] = []


def _store_scramble(moves: list[str]) -> None:
    global _last_scramble
    _last_scramble = moves


# ------------------------------------------------------------------ sidebar
st.sidebar.title("2×2×2 Solver — DAA Study")
st.sidebar.caption("Nine hand-written search algorithms compared on identical "
                   "start states.  All metrics are measured at runtime.")
# Live-sync from the 3D page BEFORE the sidebar widgets instantiate, so a
# synced case lands in the Manual box (source forced to Manual) this run.
_poll_external_scramble()
start, moves = build_state_from_sidebar()
_store_scramble(moves)
pipe = build_pipeline()

selection = st.sidebar.multiselect(
    "Algorithms", ALG_KEYS, default=["BFS", "IDDFS", "Bidirectional", "A*"],
    format_func=lambda k: ALGORITHMS[k]["label"],
)

with_dht = None
if "DLS" in selection:
    with_dht = st.sidebar.number_input("DLS depth limit", 1, 20, 4,
                                       key="dls_limit", help="DLS runs with "
                                       "this explicit limit (per depth).")

tabs = st.tabs(["Solve & Compare", "Complexity", "Benchmark"])

# --------------------------------------------------------------- 1. compare
with tabs[0]:
    st.subheader("Scrambled cube")
    col_net, col_info = st.columns([1, 1])
    with col_net:
        fig, ax = plt.subplots(figsize=(4, 4))
        render_state(start, ax)
        st.pyplot(fig, clear_figure=True)
    with col_info:
        st.markdown("**Algorithms selected:**")
        for k in selection:
            entry = ALGORITHMS[k]
            st.markdown(f"- **{entry['label']}** — {entry['short']}")
        st.markdown(f"**Scramble:** `{' '.join(moves)}`")

    if not selection:
        st.info("Tick at least one algorithm on the left.")
        st.stop()

    df = run_selected(selection, start, pipe, with_dht)

    st.subheader("Measured results")
    show = ["algorithm", "found", "length", "nodes", "generated",
            "duplicates", "pruned", "max_depth", "time_s", "memory_mb",
            "terminated", "verified"]
    if any(df["class"] == "informed"):
        show += ["heuristic", "initial_h", "memo_hit_rate"]
    st.dataframe(df[show], use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(comparison_bar(list(zip(df.algorithm, df.time_s)),
                                       "time (s)"), use_container_width=True)
    with c2:
        st.plotly_chart(comparison_bar(list(zip(df.algorithm, df.nodes)),
                                       "nodes"), use_container_width=True)

    st.subheader("Per-algorithm detail")
    for _, row in df.iterrows():
        with st.expander(
                f"{row['algorithm']} — "
                f"{'solved' if row['found'] else ('TERMINATED' if row['terminated'] else 'no solution')}"
                f" · {row['length']} moves" if not row["terminated"] else
                f"{row['algorithm']} — terminated: {row['reason']}"):
            st.write({
                "found": row["found"],
                "length": int(row["length"]) if row["found"] else "-",
                "solution": row["solution"] or "-",
                "verified": row["verified"],
                "nodes": int(row["nodes"]),
                "generated": int(row["generated"]),
                "duplicates": int(row["duplicates"]),
                "pruned": int(row["pruned"]),
                "max_depth": int(row["max_depth"]),
                "time_s": round(float(row["time_s"]), 6),
                "memory_mb": round(float(row["memory_mb"]), 3),
                "terminated": row["terminated"],
                "reason": row["reason"],
            })
            if row["iterations"]:
                st.markdown("**IDDFS per-depth iteration table:**")
                st.dataframe(pd.DataFrame(row["iterations"]),
                             use_container_width=True)
                it_df = pd.DataFrame(row["iterations"])
                st.plotly_chart(
                    iterations_plot(list(it_df.depth), list(it_df.time_s)),
                    use_container_width=True)
            if row["forward_states"]:
                st.markdown(f"**Bidirectional:** forward {row['forward_states']}"
                            f" · backward {row['backward_states']}"
                            f" · meet depth {row['meeting_depth']}")
            if row["branches_explored"]:
                st.markdown(f"**Branch & Bound:** explored "
                            f"{row['branches_explored']} · pruned "
                            f"{row['branches_pruned']} · lower bound "
                            f"{row['lower_bound']} · best `{row['best_solution']}`")
            if row["initial_h"] is not None:
                st.markdown(f"**Heuristic:** {row['heuristic']} (admissible: "
                            f"{row['admissible']}), h(start) = {row['initial_h']}")

# ---------------------------------------------------------------- 2 complexity
with tabs[1]:
    st.subheader("Theoretical complexity (textbook — NOT measured)")
    st.caption("b ≈ branching factor after pruning (~12), d = solution depth, "
               "m = max depth, l = depth limit for DLS.  These are the "
               "*asymptotic* classes; the measured values live in the Solve tab.")
    cx = pd.DataFrame(COMPLEXITY).T.rename_axis("algorithm")
    st.dataframe(cx, use_container_width=True)

# -------------------------------------------------------------- 3 benchmark
with tabs[2]:
    st.subheader("Benchmark: N scrambles × algorithms")
    b_left, b_mid, b_right = st.columns(3)
    with b_left:
        n_scrambles = st.number_input("Scrambles per length", 1, 20, 3)
    with b_mid:
        lengths = st.multiselect("Scramble lengths", [2, 4, 6, 8], [4, 6])
    with b_right:
        b_seed = st.number_input("Benchmark seed", 0, 1_000_000, 42)
    b_algs = st.multiselect(
        "Algorithms for benchmark", ALG_KEYS,
        default=["BFS", "A*", "Bidirectional"],
        format_func=lambda k: ALGORITHMS[k]["label"],
    )
    if st.button("Run benchmark") and b_algs and lengths:
        with st.spinner("running benchmark…"):
            rows = run_benchmark(
                n_scrambles=int(n_scrambles),
                scramble_lengths=[int(x) for x in lengths],
                algorithms=b_algs,
                limits=pipe["limits"],
                pruner=pipe["pruner"],
                heuristic_name=pipe["heuristic_name"],
                use_memo=pipe["use_memo"],
                seed=int(b_seed),
            )
        st.session_state["bench_rows"] = rows
        st.session_state["bench_csv"] = results_to_csv(rows)
        st.session_state["bench_md"] = results_to_markdown(rows)

    if "bench_rows" in st.session_state:
        rows = st.session_state["bench_rows"]
        st.write(f"**{len(rows)} runs recorded.**")
        st.download_button("Download CSV", st.session_state["bench_csv"],
                           "benchmark.csv", "text/csv")
        st.download_button("Download markdown", st.session_state["bench_md"],
                           "benchmark.md", "text/markdown")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.markdown(st.session_state["bench_md"])

st.sidebar.caption("Limits honoured by every algorithm: depth / states / time.")