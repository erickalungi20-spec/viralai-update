"""
Reproducibility testing (Blueprint Ch.32.5: "every official release shall verify that
identical analyses produce identical outputs when executed using the same dataset,
parameters, plugin, software version, and random seed").

A small, reusable harness: run the same callable twice with the same inputs, compare
outputs for exact equality. Phase 5's `DigitalLaboratoryManager.replay()` already proved
this property for simulations specifically; this generalizes the same check so it can be
applied to any deterministic operation (mutation detection, AI prediction, etc.) as part
of the formal Sci-CI gate, not just tested ad hoc per-module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ReproducibilityReport:
    operation_name: str
    reproducible: bool
    first_result_repr: str
    second_result_repr: str


def check_reproducibility(operation_name: str, func: Callable[[], Any]) -> ReproducibilityReport:
    """Call `func` twice (with no arguments -- bind any inputs via a closure/partial
    before passing it in) and compare the two results for exact equality.
    """
    first = func()
    second = func()

    reproducible = first == second
    return ReproducibilityReport(
        operation_name=operation_name,
        reproducible=reproducible,
        first_result_repr=repr(first),
        second_result_repr=repr(second),
    )


def assert_reproducible(operation_name: str, func: Callable[[], Any]) -> None:
    """Same as check_reproducibility, but raises AssertionError with a useful message
    on failure -- the form most useful directly inside a pytest test.
    """
    report = check_reproducibility(operation_name, func)
    if not report.reproducible:
        raise AssertionError(
            f"'{operation_name}' is not reproducible: two calls with identical inputs "
            f"produced different results.\nFirst:  {report.first_result_repr}\n"
            f"Second: {report.second_result_repr}"
        )
