"""
Knowledge Base store (Blueprint Ch.18).

Phase 3 implementation: a JSON-file-backed store with an in-memory index for querying.
This is the same pragmatic pattern as Phase 0's Event Bus/Task Scheduler — a real,
working, fully-tested implementation with zero external database dependency, behind an
interface that a Postgres/JSONB-backed store (per the Commercial Development Workflow's
tech stack) can later implement without touching call sites. See ADR-006.
"""

from __future__ import annotations

import json
from pathlib import Path

from viralai.common.errors import ValidationError
from viralai.common.logging import get_logger
from viralai.knowledge.models import (
    KnowledgeQuery,
    LiteratureReference,
    MutationKnowledge,
    ProteinKnowledge,
)

logger = get_logger("knowledge.store")


class KnowledgeBase:
    """In-memory knowledge store with optional JSON-file persistence.

    Construct with `persist_path=None` (default) for an ephemeral, test-friendly store, or
    pass a directory path to load-on-init and save-on-write.
    """

    def __init__(self, persist_path: Path | str | None = None) -> None:
        self._persist_dir = Path(persist_path) if persist_path else None
        self._references: dict[str, LiteratureReference] = {}
        self._mutation_knowledge: list[MutationKnowledge] = []
        self._protein_knowledge: list[ProteinKnowledge] = []

        if self._persist_dir is not None:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    # -- Literature references --------------------------------------------------------

    def add_reference(self, reference: LiteratureReference) -> None:
        if reference.reference_id in self._references:
            raise ValidationError(f"Reference '{reference.reference_id}' already exists")
        self._references[reference.reference_id] = reference
        self._save()

    def get_reference(self, reference_id: str) -> LiteratureReference:
        if reference_id not in self._references:
            raise ValidationError(f"No reference with id '{reference_id}'")
        return self._references[reference_id]

    # -- Mutation knowledge --------------------------------------------------------------

    def add_mutation_knowledge(self, entry: MutationKnowledge) -> None:
        self._validate_references_exist(entry.reference_ids)
        self._mutation_knowledge.append(entry)
        self._save()
        logger.info(
            "mutation knowledge added: virus=%s gene=%s position=%d",
            entry.virus,
            entry.gene,
            entry.position,
        )

    def query_mutation_knowledge(self, query: KnowledgeQuery) -> list[MutationKnowledge]:
        return [
            entry for entry in self._mutation_knowledge if query.matches_mutation_knowledge(entry)
        ]

    def get_mutation_knowledge_at(
        self, virus: str, gene: str, position: int
    ) -> list[MutationKnowledge]:
        return [
            entry
            for entry in self._mutation_knowledge
            if entry.virus == virus and entry.gene == gene and entry.position == position
        ]

    # -- Protein knowledge -----------------------------------------------------------------

    def add_protein_knowledge(self, entry: ProteinKnowledge) -> None:
        self._validate_references_exist(entry.reference_ids)
        self._protein_knowledge.append(entry)
        self._save()

    def query_protein_knowledge(
        self, *, virus: str | None = None, protein_id: str | None = None
    ) -> list[ProteinKnowledge]:
        results = self._protein_knowledge
        if virus:
            results = [e for e in results if e.virus == virus]
        if protein_id:
            results = [e for e in results if e.protein_id == protein_id]
        return results

    # -- internals ----------------------------------------------------------------------

    def _validate_references_exist(self, reference_ids: list[str]) -> None:
        missing = [rid for rid in reference_ids if rid not in self._references]
        if missing:
            raise ValidationError(
                f"Cannot add knowledge entry citing unknown reference id(s): {missing}. "
                f"Add the LiteratureReference first."
            )

    def _save(self) -> None:
        if self._persist_dir is None:
            return
        (self._persist_dir / "references.json").write_text(
            json.dumps([r.model_dump(mode="json") for r in self._references.values()], indent=2),
            encoding="utf-8",
        )
        (self._persist_dir / "mutation_knowledge.json").write_text(
            json.dumps([m.model_dump(mode="json") for m in self._mutation_knowledge], indent=2),
            encoding="utf-8",
        )
        (self._persist_dir / "protein_knowledge.json").write_text(
            json.dumps([p.model_dump(mode="json") for p in self._protein_knowledge], indent=2),
            encoding="utf-8",
        )

    def _load(self) -> None:
        assert self._persist_dir is not None
        refs_file = self._persist_dir / "references.json"
        if refs_file.exists():
            for raw in json.loads(refs_file.read_text(encoding="utf-8")):
                ref = LiteratureReference(**raw)
                self._references[ref.reference_id] = ref

        mutations_file = self._persist_dir / "mutation_knowledge.json"
        if mutations_file.exists():
            self._mutation_knowledge = [
                MutationKnowledge(**raw)
                for raw in json.loads(mutations_file.read_text(encoding="utf-8"))
            ]

        proteins_file = self._persist_dir / "protein_knowledge.json"
        if proteins_file.exists():
            self._protein_knowledge = [
                ProteinKnowledge(**raw)
                for raw in json.loads(proteins_file.read_text(encoding="utf-8"))
            ]

        logger.info(
            "knowledge base loaded from %s: %d references, %d mutation entries, %d protein entries",
            self._persist_dir,
            len(self._references),
            len(self._mutation_knowledge),
            len(self._protein_knowledge),
        )
