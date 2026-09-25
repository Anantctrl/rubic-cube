"""Optimisation layer: hashing, move pruning, memoization.

These are pure *computation-reduction* helpers — they never change what a
correct search must return.  The pruning rules implemented here are *safe*
for shortest paths: inverse-move pruning and same-face pruning both remove
only states whose best-solution length is at least as short via the remaining
moves, so optimal solutions are never lost.  (Run ``tests`` to prove it.)
"""

from .hashing import StateHasher
from .pruning import MovePruner
from .memoization import Memoizer

__all__ = ["StateHasher", "MovePruner", "Memoizer"]