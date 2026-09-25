"""Metrics aggregation: averages + success rate over a benchmark batch."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean


@dataclass
class Metrics:
    """Collects per-algorithm observations over many scrambles."""

    algorithm: str
    times_s: list[float] = field(default_factory=list)
    lengths: list[int] = field(default_factory=list)
    nodes: list[int] = field(default_factory=list)
    generated: list[int] = field(default_factory=list)
    duplicates: list[int] = field(default_factory=list)
    pruned: list[int] = field(default_factory=list)
    memory_mb: list[float] = field(default_factory=list)
    successes: int = 0
    runs: int = 0

    def add(
        self,
        *,
        time_s: float,
        length: int,
        nodes: int,
        generated: int,
        duplicates: int,
        pruned: int,
        memory_mb: float,
        found: bool,
    ) -> None:
        self.runs += 1
        if found:
            self.successes += 1
        self.times_s.append(time_s)
        self.lengths.append(length if found else None)
        self.nodes.append(nodes)
        self.generated.append(generated)
        self.duplicates.append(duplicates)
        self.pruned.append(pruned)
        self.memory_mb.append(memory_mb)

    @property
    def success_rate(self) -> float:
        return self.successes / self.runs if self.runs else 0.0

    def summarize(self) -> dict:
        def avg(xs, skip_none=False):
            xs = [x for x in xs if x is not None]
            if not xs:
                return 0.0
            return mean(xs)

        return {
            "algorithm": self.algorithm,
            "runs": self.runs,
            "success_rate": round(self.success_rate, 3),
            "avg_time_s": round(avg(self.times_s), 6),
            "avg_length": round(avg(self.lengths), 2),
            "avg_nodes": round(avg(self.nodes, True), 1),
            "avg_generated": round(avg(self.generated, True), 1),
            "avg_duplicates": round(avg(self.duplicates, True), 1),
            "avg_pruned": round(avg(self.pruned, True), 1),
            "avg_memory_mb": round(avg(self.memory_mb, True), 3),
        }


def summarize(metrics_list: list[Metrics]) -> list[dict]:
    return [m.summarize() for m in metrics_list]