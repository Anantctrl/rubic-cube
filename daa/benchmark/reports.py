"""Export benchmark rows to CSV and markdown (report-ready tables)."""

from __future__ import annotations

import csv
import io


CSV_FIELDS = [
    "algorithm",
    "found",
    "length",
    "nodes",
    "generated",
    "duplicates",
    "pruned",
    "max_depth",
    "time_s",
    "memory_mb",
    "terminated",
    "scramble",
]


def results_to_csv(rows: list[dict]) -> str:
    """Return the CSV payload (string) for all benchmark rows."""
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in CSV_FIELDS})
    return buf.getvalue()


def results_to_markdown(rows: list[dict]) -> str:
    """Render rows grouped by algorithm as a markdown comparison table."""
    if not rows:
        return "_no benchmark rows yet_"
    header = (
        "| Algorithm | Solved | Moves | Nodes | Generated | Dupes | Pruned | MaxD | Time (s) | Mem (MB) |\n"
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    out = [header]
    for row in rows:
        out.append(
            "| {alg} | {found} | {length} | {nodes} | {generated} | {duplicates} | {pruned} | {max_depth} | {time_s} | {memory_mb} |".format(
                alg=str(row.get("algorithm", "")).replace("|", r"\|"),
                found="y" if row.get("found") else "n",
                length=row.get("length", 0),
                nodes=row.get("nodes", 0),
                generated=row.get("generated", 0),
                duplicates=row.get("duplicates", 0),
                pruned=row.get("pruned", 0),
                max_depth=row.get("max_depth", 0),
                time_s=row.get("time_s", 0),
                memory_mb=row.get("memory_mb", 0),
            )
        )
    return "\n".join(out)