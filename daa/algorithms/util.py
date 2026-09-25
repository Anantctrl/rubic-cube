"""Shared runtime helpers: execution timing, memory, and the exit guard.

CPU-time vs wall-clock: for reporting we use ``time.perf_counter`` (wall clock,
honest for a UI demo) but keep theoretical complexity figures *out* of the
measured numbers — the dashboard labels them separately.
"""

from __future__ import annotations

import time

from daa.algorithms.base import Limits

try:
    import resource as _resource
except ImportError:  # Windows
    _resource = None


class ExitGuard:
    """Enforces the DAA safety budget during a search.

    The search loop calls :meth:`tick` after every node expansion; if the
    budget is exceeded it returns ``True`` and the algorithm must stop, mark
    ``terminated=True`` and attach ``reason`` — mirroring the spec's
    "Search terminated due to configured resource limit."
    """

    #: number of generated states between peak-memory samples.  Sampling the
    #: Windows ctypes query on every tick costs ~20us/state and dominates
    #: search time; sampling every N states measures the same RSS trend at
    #: negligible cost (enforcement is still checked at this resolution).
    _MEM_SAMPLE_EVERY = 256

    def __init__(self, limits: Limits):
        self.limits = limits
        self._start = time.perf_counter()
        self.generated = 0
        self._mem_checked_at = 0

    def tick(self) -> tuple[bool, str]:
        """Return ``(stop, reason)``; call once per generated state."""
        self.generated += 1
        if self.generated > self.limits.max_states:
            return True, "state limit (max_states)"
        if time.perf_counter() - self._start > self.limits.max_time_s:
            return True, "time limit (max_time_s)"
        if self.generated - self._mem_checked_at >= self._MEM_SAMPLE_EVERY:
            self._mem_checked_at = self.generated
            if self.memory_mb() > self.limits.max_memory_mb:
                return True, "memory limit (max_memory_mb)"
        return False, ""

    @staticmethod
    def memory_mb() -> float:
        """Peak resident memory of the current process, best-effort."""
        if _resource is None:  # Windows: no rusage; sample process memory instead
            try:
                import ctypes

                class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                    _fields_ = [
                        ("cb", ctypes.c_ulong),
                        ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t),
                    ]

                ctr = _PROCESS_MEMORY_COUNTERS()
                if ctypes.windll.psapi.GetProcessMemoryInfo(
                    ctypes.windll.kernel32.GetCurrentProcess(),
                    ctypes.byref(ctr),
                    ctypes.sizeof(ctr),
                ):
                    return ctr.PeakWorkingSetSize / 1024.0 / 1024.0
            except Exception:
                pass
            return 0.0
        return _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss / 1024.0


def time_and_profile(fn):
    """Run ``fn() -> result`` with wall-clock timing + peak memory sampling.

    Returns ``(result, seconds, peak_memory_mb_at_exit)`` — the memory figure
    is sampled before/after (delta of process RSS growth attributable to the
    search structures), which is the honest "how much did this search cost"
    number the report wants.
    """
    rss_before = ExitGuard.memory_mb()
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    rss_after = ExitGuard.memory_mb()
    return result, elapsed, max(0.0, rss_after - rss_before)