"""Dashboard support tests: flat-net renderer invariants + content modules.

The renderer is *schematic* (piece-identity colouring), so the honest
invariants to pin are exactly the ones promised in ``cubenet.py``:
solved renders uniform per face, and the net is deterministic.
"""

import matplotlib

matplotlib.use("Agg")
import pandas as pd

from daa.cube.state import CubeState
from daa.ui.charts import comparison_bar
from daa.ui.cubenet import FACE_COLOR, _ALL_FACES, _LAYOUT, sticker_grid
from daa.ui.panels import COMPLEXITY, CONCEPTS, VIVA_QA


def test_solved_net_is_uniform():
    grids = sticker_grid(CubeState.solved())
    for face in _ALL_FACES:
        assert grids[face] == [FACE_COLOR[face]] * 4


def test_net_blanket_covers_exactly_the_8_corners():
    used = {corner for face in _LAYOUT.values() for c in face.values()
            for corner in (c[0],)}
    assert used == set(range(8))
    # each corner appears on exactly 3 faces (3 stickers)
    from collections import Counter

    counts = Counter(
        corner for face in _LAYOUT.values() for c in face.values()
        for corner in (c[0],)
    )
    assert all(n == 3 for n in counts.values())


def test_net_deterministic():
    s = CubeState.from_alg(["R", "U", "F", "D'"])
    assert sticker_grid(s) == sticker_grid(s)


def test_scramble_then_inverse_is_uniform_again():
    from solver import cube_state as cs

    state = CubeState.from_alg(["R", "U", "F", "D'", "L2"])
    inv = [cs.inverse(m) for m in reversed(["R", "U", "F", "D'", "L2"])]
    back = state
    for m in inv:
        back = back.apply_move(m)
    for face in _ALL_FACES:
        assert sticker_grid(back)[face] == [FACE_COLOR[face]] * 4


def test_charts_build():
    fig = comparison_bar([("BFS", 0.1), ("A*", 0.3)], "time (s)")
    assert fig.layout.xaxis.title.text == "Algorithm"
    assert len(fig.data) == 2  # one coloured bar trace per value


def test_panels_cover_all_algorithms_and_viva():
    for key in COMPLEXITY:
        assert key in CONCEPTS, key
    assert len(VIVA_QA) >= 5
    assert all(q["q"] and q["a"] for q in VIVA_QA)
    df = pd.DataFrame(COMPLEXITY).T
    assert "optimal" in df.columns