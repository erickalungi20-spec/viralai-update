"""
Plugin Manifest Specification (Blueprint Ch.31.4) and Certification Tiers (Ch.16, 31.5,
Addition 3/23).

Every plugin ships a `manifest.json` conforming to `PluginManifest`. The manifest is what
the Plugin Manager validates *before* it ever imports the plugin's code — a malformed or
incompatible manifest should fail loudly and early, not surface as a mysterious runtime
error three engines downstream.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CertificationTier(str, Enum):
    """Blueprint Ch.16.6 / Ch.31.5 — trust tiers for plugins.

    - EXPERIMENTAL: newly added, not yet through the validation pipeline. Usable, but every
      report generated with it must visibly disclose that status.
    - COMMUNITY: passed automated validation (schema, reference genome checksum, unit
      tests) but has not been through scientific review by the (eventual) AI/Scientific
      Review Committee.
    - OFFICIAL: passed automated validation AND scientific review. This is the only tier
      that should be default-loaded in a production/clinical-research deployment.
    """

    EXPERIMENTAL = "experimental"
    COMMUNITY = "community"
    OFFICIAL = "official"


class PluginManifest(BaseModel):
    """Blueprint Ch.31.4 manifest fields, plus the certification/versioning metadata
    needed to make the Plugin Manager's compatibility checks meaningful.
    """

    name: str
    version: str
    supported_viruses: list[str] = Field(min_length=1)
    compatible_core_engine_versions: str  # a PEP 440-style version specifier, e.g. ">=0.1.0,<0.2.0"
    authors: list[str] = Field(min_length=1)
    license: str
    certification_tier: CertificationTier = CertificationTier.EXPERIMENTAL
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)

    # Reference data provenance — Blueprint's "gene coordinates sourced from published
    # references only" standard. A plugin without at least one citation for its reference
    # genome is not eligible for COMMUNITY or OFFICIAL certification.
    reference_genome_accession: str | None = None
    reference_genome_citations: list[str] = Field(default_factory=list)

    def is_compatible_with(self, core_engine_version: str) -> bool:
        """Minimal PEP 440-lite compatibility check.

        Phase 1 keeps this intentionally simple (exact-prefix / '>=' lower-bound check)
        rather than pulling in `packaging` as a dependency for one comparison. Revisit if
        the version specifiers used in practice get more complex than 'x.y.z' bounds.
        """
        spec = self.compatible_core_engine_versions.strip()
        if spec == "*":
            return True
        # Support the common single-clause cases used across the launch plugins.
        if spec.startswith(">="):
            return _version_tuple(core_engine_version) >= _version_tuple(spec[2:].split(",")[0])
        if spec.startswith("=="):
            return core_engine_version == spec[2:]
        return core_engine_version == spec


def _version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.strip().split("."))
