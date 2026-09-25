"""Benchmark runner + report export tests."""

import pytest

from daa.algorithms.base import Limits, verify_solution
from daa.benchmark.registry import available, run_algorithm, run_algorithm_by_label
from daa.benchmark.reports import results_to_csv, results_to_markdown
from daa.benchmark.runner import run_benchmark, run_single
from daa.cube.state import CubeState, from_alg, scramble

L = Limits(max_depth=8, max_states=40_000, max_time_s=30.0)


def test_available_and_registry_coverage():
    names = available()
    assert len(names) == 9
    assert "A*" in names and "Bid" not in names
    assert "Branch & Bound" in names


def test_run_algorithm_dispatches_all():
    s = from_alg(["R", "U", "F"])
    for name in available():
        r = run_algorithm(name, s, limits=L, heuristic_name="Admissible: corners / 4")
        assert r.algorithm
        if r.found:
            assert verify_solution(["R", "U", "F"], r.solution)


def test_run_algorithm_by_label():
    s = from_alg(["R"])
    r = run_algorithm_by_label("A*", s, limits=L, heuristic_name="Admissible: corners / 4")
    assert r.algorithm == "A*"
    with pytest.raises(KeyError):
        run_algorithm_by_label("nope", s)


def test_run_single_returns_rows():
    rows = run_single(
        ["R", "U", "F"], ["BFS", "A*"], limits=L, use_memo=True
    )
    assert len(rows) == 2
    assert rows[0]["algorithm"] == "BFS"
    assert "scramble" in rows[0]


def test_run_benchmark_produces_csv_and_md():
    rows = run_benchmark(
        n_scrambles=2,
        scramble_lengths=[3, 5],
        algorithms=["BFS", "IDDFS"],
        limits=L,
        use_memo=False,
    )
    assert len(rows) == 2 * 2 * 2  # 2 lengths * 2 scrambles * 2 algorithms
    csv_text = results_to_csv(rows)
    assert csv_text.startswith("algorithm,")
    assert csv_text.count("\n") == len(rows) + 1
    md = results_to_markdown(rows)
    assert "| Algorithm |" in md
    assert md.count("BFS") >= 2


def test_verify_solution_true_for_roundtrip():
    alg = scramble(5)
    from solver import cube_state as cs

    inv = [cs.inverse(m) for m in reversed(alg)]
    assert verify_solution(alg, inv) is True


def test_verify_solution_false_for_garbage():
    assert verify_solution(["R"], ["U"]) is False