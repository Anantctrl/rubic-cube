"""2D flat-net cube renderer for the dashboard (matplotlib).

Draws the 2x2x2 cube as an unwrapped net ("cross" layout):

        [B]
    [L] [U] [R]
        [F]
        [D]

Each face is a 2x2 grid of stickers.  A sticker's colour is the **home-face
colour of the piece covering that cell** (corners 0..7 in the canonical
enumeration: ``ULF URF ULB URB DLB DRB DLF DRF``).  Consequences:

* The solved cube renders as six uniform faces (tested).
* Scramble then inverse-scramble renders as solved again (tested).
* The net is intentionally *schematic*: it shows which piece sits where, which
  is what the DAA study needs.  The precise physical 3D cube is the
  cubing.js <twisty-player> in the main app; this dashboard prioritises
  honest per-piece visualisation without a 3D engine.

Orientation deltas are ignored on the flat net (positions dominate the DAA
discussion); the net is deterministic and stable across reruns.
"""

from __future__ import annotations

from matplotlib.patches import Rectangle

# corner index -> the three faces it touches (sticker colours of those pieces)
CORNERS = [
    ("U", "L", "F"),  # 0 ULF
    ("U", "R", "F"),  # 1 URF
    ("U", "L", "B"),  # 2 ULB
    ("U", "R", "B"),  # 3 URB
    ("D", "L", "B"),  # 4 DLB
    ("D", "R", "B"),  # 5 DRB
    ("D", "L", "F"),  # 6 DLF
    ("D", "R", "F"),  # 7 DRF
]

_ALL_FACES = ["U", "D", "L", "R", "F", "B"]

FACE_COLOR = {
    "U": "#ffffff",
    "D": "#ffd500",
    "F": "#009b48",
    "B": "#0046ad",
    "R": "#b71234",
    "L": "#ff5800",
}
# colours are the official Rubik's colour scheme (nice to look at).

# net cell -> (corner_index, which_sticker 0..2 in CORNERS[corner])
# Face grids are (row, col), row 0 = top of that face's net cell.
_LAYOUT = {
    "U": {(0, 0): (2, 0), (0, 1): (3, 0), (1, 0): (0, 0), (1, 1): (1, 0)},
    "D": {(0, 0): (6, 0), (0, 1): (7, 0), (1, 0): (4, 0), (1, 1): (5, 0)},
    "B": {(0, 0): (2, 2), (0, 1): (3, 2), (1, 0): (4, 2), (1, 1): (5, 2)},
    "F": {(0, 0): (0, 2), (0, 1): (1, 2), (1, 0): (6, 2), (1, 1): (7, 2)},
    "L": {(0, 0): (2, 1), (0, 1): (0, 1), (1, 0): (4, 1), (1, 1): (6, 1)},
    "R": {(0, 0): (3, 1), (0, 1): (1, 1), (1, 0): (5, 1), (1, 1): (7, 1)},
}

# net positions in "cross" coordinates (col, row) for matplotlib
_NET_POS = {
    "U": (0, 0),
    "D": (0, 2),
    "F": (0, 1),
    "B": (0, -1),
    "L": (-1, 0),
    "R": (1, 0),
}


def _full_perm(perm) -> tuple[int, ...]:
    """Canonical 7-corners + the fixed corner 7 = full 8-corner perm."""
    return tuple(perm) + (7,)


def sticker_grid(state) -> dict[str, list[str]]:
    """Return ``{face: [4 colours]}`` in (row, col) order for a CubeState."""
    full = _full_perm(state.perm)
    grids: dict[str, list[str]] = {f: [] for f in _ALL_FACES}
    for f in _ALL_FACES:
        for r in (0, 1):
            for c in (0, 1):
                corner, sticker = _LAYOUT[f][(r, c)]
                piece = full[corner]
                grids[f].append(FACE_COLOR[CORNERS[piece][sticker]])
    return grids


def render_state(state, ax, scale: float = 1.0) -> None:
    """Draw a :class:`~daa.cube.state.CubeState` on matplotlib Axes ``ax``."""
    grids = sticker_grid(state)
    for face, (cx, cy) in _NET_POS.items():
        stickers = grids[face]
        color_rows = [stickers[0:2], stickers[2:4]]
        for r, row in enumerate(color_rows):
            for c, color in enumerate(row):
                x = cx * 2 + c
                y = cy * 2 - r
                ax.add_patch(
                    Rectangle(
                        (x, y), 1, 1,
                        facecolor=color, edgecolor="#222", linewidth=1.0,
                    )
                )
    ax.set_xlim(-3.5, 3.5)
    ax.set_ylim(-3.5, 3.5)
    ax.set_aspect("equal")
    ax.axis("off")
    if scale != 1.0:
        ax.set_position([0.15, 0.1, scale, scale])