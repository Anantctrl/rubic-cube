"""Learning + complexity + viva-modes content for the dashboard.

These are *static educational panels* (concept, pseudocode ideas, complexity
table, viva Q&A) — clearly separated from the **measured** results in the
comparison tab.  The measured metrics are never invented; they come from the
benchmark runner and are labelled as such.
"""

from __future__ import annotations

CONCEPTS: dict[str, dict] = {
    "BFS": {
        "title": "Breadth-First Search",
        "idea": "Explore near states before far ones.  Uses a **queue (FIFO)**: "
                "every cube state at depth d is expanded before any state at "
                "depth d+1.  The first time the solved state is reached, the "
                "path taken is a **shortest (optimal) solution**.",
        "ds": "Queue + visited set (hash).",
        "pros": "Guarantees optimal solution.",
        "cons": "Memory O(b^d) — a level of ~3.7M states is the whole 2x2 graph.",
    },
    "DFS": {
        "title": "Depth-First Search",
        "idea": "Commit to one branch and descend as deep as possible before "
                "backtracking.  Uses a **stack (LIFO)**.  Very memory-light "
                "(O(d) path), but the first solution it finds is usually NOT "
                "shortest — it depends entirely on move ordering.",
        "ds": "Stack + visited set.",
        "pros": "Tiny memory; simple.",
        "cons": "Not optimal; can chase a long fruitless branch.",
    },
    "DLS": {
        "title": "Depth-Limited Search",
        "idea": "DFS with a hard **depth limit l**: branches longer than l are "
                "cut off.  This bounds worst-case work (O(b^l)) and prevents "
                "infinite descent, at the cost of missing any solution longer "
                "than l — hence the learner can pick an explicit limit.",
        "ds": "Stack + explicit depth counter.",
        "pros": "Bounded time; prevents infinite loops.",
        "cons": "Incomplete if the limit is below the true distance.",
    },
    "IDDFS": {
        "title": "Iterative Deepening Depth-First Search",
        "idea": "Run DLS for limit = 0, 1, 2, … until a solution is found.  "
                "Each pass is DFS with a slightly deeper ceiling, so the first "
                "successful pass finds a **shortest** solution while keeping "
                "DFS's O(d) memory.  The price is re-exploring the upper levels "
                "on every pass.",
        "ds": "Repeated DLS; visited set per pass.",
        "pros": "Optimal AND memory-light; the best of BFS+DFS.",
        "cons": "Upper levels are expanded again each iteration.",
    },
    "Bidirectional": {
        "title": "Bidirectional Search",
        "idea": "Two BFS frontiers race: the forward one from the scrambled "
                "cube, the backward one from the solved cube (using inverse "
                "moves).  When the two fronts **meet**, splicing the half-paths "
                "gives a shortest solution.  A ball of radius d covers the "
                "space; two balls of radius d/2 meet it far more cheaply — the "
                "documented reason this is the fastest of the blind searches.",
        "ds": "Two queues + two visited sets + parent maps.",
        "pros": "Exponential speedup on deep states; still optimal.",
        "cons": "Meet detection + parent bookkeeping; doubles the memory.",
    },
    "Greedy": {
        "title": "Greedy Best-First Search",
        "idea": "Always expand the state whose **heuristic h(n)** — estimated "
                "distance to solved — is smallest.  Hunts straight at the goal; "
                "very few states usually.  Because it ignores how many moves "
                "were already spent (g), it can overshoot around a detour and "
                "return a **longer-than-optimal** solution.",
        "ds": "Priority queue keyed by h.",
        "pros": "Few expansions; very fast on easy cubes.",
        "cons": "Not optimal; sensitive to heuristic quality.",
    },
    "A*": {
        "title": "A* Search",
        "idea": "Expand by **f(n) = g(n) + h(n)**: cost already paid plus an "
                "estimate of what remains.  With an **admissible** heuristic "
                "(h never overestimates), the first popped solution is "
                "**optimal** — A* is the heuristic version of BFS's guarantee. "
                "This project demonstrates the admissible menu vs "
                "estimate-only heuristics, and how the PDB massively reduces "
                "expanded states.",
        "ds": "Priority queue keyed by f; g-best reopen.",
        "pros": "Optimal with admissible h; far fewer states than BFS.",
        "cons": "Needs a good h; priority queue overhead.",
    },
    "Backtracking": {
        "title": "Backtracking",
        "idea": "Recursive generate-and-test: choose a move, apply it, recurse; "
                "if a branch fails, **undo** and try the next.  This project "
                "mirrors the recursion with an explicit stack and counts "
                "``recursive calls`` and ``backtracks``.  Returns the first "
                "solution found — completeness is traded against optimality.",
        "ds": "Explicit/recursive stack + current-branch set.",
        "pros": "Structural; easy to add constraints.",
        "cons": "Not optimal; exponential worst case.",
    },
    "Branch & Bound": {
        "title": "Branch and Bound",
        "idea": "Backtracking + **bounding**: keep the best solution known so "
                "far (upper bound U); any branch whose lower bound "
                "``g(n) + h(n)`` is already >= U is pruned — it cannot beat "
                "the incumbent.  With an admissible h this eventually *proves* "
                "optimality; the dashboard reports ``branches explored`` vs "
                "``branches pruned``.",
        "ds": "Bound-aware search tree + incumbent.",
        "pros": "Optimal with admissible h; prunes huge subtrees.",
        "cons": "Still exponential in the worst case; depends on h + ordering.",
    },
}

COMPLEXITY: dict[str, dict] = {
    "BFS": {
        "time_avg": "O(b^d)",
        "time_worst": "O(b^d)",
        "space": "O(b^d)",
        "complete": "Yes",
        "optimal": "Yes",
        "note": "b = branching (~12 with safe pruning).",
    },
    "DFS": {
        "time_avg": "O(b^m)",
        "time_worst": "O(b^m)",
        "space": "O(bm)",
        "complete": "Yes (with cycle/limit guard)",
        "optimal": "No",
        "note": "m = deepest reachable depth.",
    },
    "DLS": {
        "time_avg": "O(b^l)",
        "time_worst": "O(b^l)",
        "space": "O(bl)",
        "complete": "Only if l >= true distance",
        "optimal": "No",
        "note": "l = chosen depth limit.",
    },
    "IDDFS": {
        "time_avg": "O(b^d)",
        "time_worst": "O(b^d)",
        "space": "O(bd)",
        "complete": "Yes",
        "optimal": "Yes",
        "note": "Repeated frontier rows cost a constant factor.",
    },
    "Bidirectional": {
        "time_avg": "O(b^(d/2))",
        "time_worst": "O(b^(d/2))",
        "space": "O(b^(d/2))",
        "complete": "Yes",
        "optimal": "Yes",
        "note": "Two half-balls — the blind-search winner.",
    },
    "Greedy": {
        "time_avg": "O(b^m)",
        "time_worst": "O(b^m)",
        "space": "O(b^m)",
        "complete": "Yes (with guards)",
        "optimal": "No",
        "note": "f = h only; no accumulated cost.",
    },
    "A*": {
        "time_avg": "O(b^d)",
        "time_worst": "O(b^m)",
        "space": "O(b^d)",
        "complete": "Yes",
        "optimal": "Yes",
        "note": "Optimal iff h admissible.",
    },
    "Backtracking": {
        "time_avg": "O(b^m)",
        "time_worst": "O(b^m)",
        "space": "O(m)",
        "complete": "Yes (bounded)",
        "optimal": "No",
        "note": "First solution wins.",
    },
    "Branch & Bound": {
        "time_avg": "O(b^m)",
        "time_worst": "O(b^m)",
        "space": "O(m)",
        "complete": "Yes",
        "optimal": "Yes (with admissible h)",
        "note": "Pruned with g+h bound.",
    },
}

VIVA_QA: list[dict] = [
    {
        "q": "Why is BFS optimal but memory-hungry on a Rubik's cube?",
        "a": "BFS expands states in increasing distance order, so the first "
             "reach of solved is shortest.  Memory is the size of the frontier "
             "(~O(b^d)) which for the 2x2 graph becomes the whole 3.67M states "
             "as d approaches God's number (11).",
    },
    {
        "q": "When does A* reduce to Dijkstra / to Greedy?",
        "a": "h(n)=0 makes f=g — plain Dijkstra/uniform cost.  f=h only "
             "(ignoring g) is greedy best-first.  A* sits between: g keeps it "
             "optimal, h keeps it focused.",
    },
    {
        "q": "What makes a heuristic admissible, and why does it matter?",
        "a": "h(n) never exceeds the true remaining cost.  Any move can fix at "
             "most 4 corners, so h = misplaced/4 and stickers/12 are provably "
             "admissible; with an admissible h A* and Branch&Bound return "
             "proven-optimal solutions.",
    },
    {
        "q": "What is the point of a bidirectional search?",
        "a": "A ball of radius d is enormous, two balls of radius d/2 meet "
             "cheaply; the product of two half-sizes beats one full size "
             "exponentially — visible in the measured 'nodes expanded' "
             "difference vs BFS on the same state.",
    },
    {
        "q": "Why does IDDFS 'waste' work yet stay optimal?",
        "a": "Each DFS pass re-walks shallower levels, but the deepest level "
             "dominates the total, giving O(b^d) time with only O(d) memory — "
             "comparable to BFS time, far better space.",
    },
    {
        "q": "How does the pattern database stay admissible?",
        "a": "It ignores most pieces and precomputes exact distances in the "
             "smaller projected space.  Ignoring pieces cannot make solving "
             "harder, so the projected distance is always <= true distance.",
    },
    {
        "q": "Branch and Bound vs A*: when is one better?",
        "a": "B&B keeps an incumbent U and prunes by g+h >= U, so it explores "
             "in depth-first order with low memory; A* orders everything by f "
             "in a priority queue (more memory) but typically expands fewer "
             "nodes.  The benchmark tab shows both on identical scrambles.",
    },
    {
        "q": "What happens when resource limits are hit?",
        "a": "The search stops and reports 'terminated' with the reason "
             "(time / states / depth / memory).  Every algorithm honours the "
             "same Limits object, so the comparison is fair and the UI never "
             "freezes.",
    },
]


def concept_panel(alg_name: str) -> dict:
    return CONCEPTS[alg_name]


def complexity_panel(alg_name: str) -> dict:
    return COMPLEXITY[alg_name]