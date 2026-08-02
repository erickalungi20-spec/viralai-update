"""
Development Dashboard (engineering review Recommendation 10; Blueprint Ch.34 process
visibility). Aggregates: module completion, test coverage, plugin certification status,
AI model performance, documentation coverage, and benchmark/release readiness into one
snapshot -- the project's own "are we actually ready to release" status page.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ModuleStatus(BaseModel):
    phase: int
    name: str
    complete: bool


class PluginStatus(BaseModel):
    name: str
    version: str
    certification_tier: str
    security_scan_clean: bool


class ModelStatus(BaseModel):
    name: str
    version: str
    latest_metrics: dict[str, float]


class DashboardSnapshot(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    software_version: str

    modules: list[ModuleStatus] = Field(default_factory=list)
    test_count: int | None = None
    test_coverage_percent: float | None = None

    plugins: list[PluginStatus] = Field(default_factory=list)
    models: list[ModelStatus] = Field(default_factory=list)

    benchmark_datasets_total: int = 0
    benchmark_datasets_passing: int = 0

    documentation_gap_count: int | None = None

    @property
    def modules_complete_count(self) -> int:
        return sum(1 for m in self.modules if m.complete)

    @property
    def release_ready(self) -> bool:
        """A conservative, explicit definition of "ready": every tracked module
        complete, every plugin's security scan clean, and (if benchmarks have been run)
        every benchmark dataset passing. Coverage/documentation gaps are visible on the
        snapshot but don't block this flag on their own -- those are quality signals a
        human should weigh, not a hard release gate by themselves.
        """
        if not self.modules or self.modules_complete_count != len(self.modules):
            return False
        if any(not p.security_scan_clean for p in self.plugins):
            return False
        if (
            self.benchmark_datasets_total > 0
            and self.benchmark_datasets_passing != self.benchmark_datasets_total
        ):
            return False
        return True
