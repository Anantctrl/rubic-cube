"""DAA (Design & Analysis of Algorithms) comparative solver package.

Educational layer over ``solver.cube_state``'s canonical 2x2x2 engine.  Every
search algorithm is written by hand from the textbook definition (queue, stack,
priority queue, recursion, branch-and-bound pruning, ...) and reports honest
measured metrics: states explored/generated, duplicates, pruned branches,
max depth, wall time, peak memory, memo cache hits/misses.

Conventions
-----------
- States are :class:`~daa.cube.state.CubeState` (canonical 7-corner
  ``(perm, orient)`` immutable objects); ``hash(state)`` / ``encode`` are the
  duplicate-detection keys.
- ``parent`` traversal reconstructs solutions; inverse-move + same-face
  pruning is configurable and *safe* (never removes a shortest solution).
- Every algorithm lives in ``daa.algorithms`` and returns a
  :class:`~daa.algorithms.base.SearchResult` with identical fields so the UI
  comparisons are apples-to-apples.
"""