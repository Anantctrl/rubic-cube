"""Algorithms package.  Each module exports ``solve(start, limits, ...)``.

Common experience notes used across modules:

- Every search works on the *implicit graph*: neighbours are generated only
  when a node is expanded (never a full adjacency list in memory).
- Duplicate detection uses the cube state's native hash in a Python ``set``/
  ``dict`` (the memoiseable/duplicate count is reported).
- ``MovePruner`` implements inverse-move + same-face + consecutive-repeat
  pruning (safe for optimality) and is configurable.
- Time/memory limits are enforced by ``ExitGuard`` (see ``base``) so the UI
  can never hang.
"""