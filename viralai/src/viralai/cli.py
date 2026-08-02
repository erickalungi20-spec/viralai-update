"""
CLI (Commercial Development Workflow Phase 8 item: "Python SDK, CLI").

argparse-based, standard library only -- no new dependency for command-line automation.
Operates directly against the engines (not over HTTP), so it works without a running API
server; `serve` is the one command that starts one, via uvicorn.

Scope decision: covers the operations most useful for scripting/CI (detect mutations,
list plugins, run the API server) rather than exhaustively wrapping every API endpoint --
add subcommands as real automation needs emerge.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

from viralai.ai.features import FeatureContext
from viralai.ai.registry import ModelRegistry
from viralai.ai.training_pipeline import AITrainingPipelineManager, LabeledExample
from viralai.benchmarking.repository import BenchmarkRepository
from viralai.core.idm import Genome, Mutation, MutationType
from viralai.dashboard.builder import build_snapshot, to_markdown
from viralai.engines.mutation_engine import MutationEngine
from viralai.plugins.loader import list_plugin_manifests
from viralai.security.api_keys import APIKeyStore
from viralai.security.roles import Role
from time import monotonic
from datetime import datetime, timezone


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="viralai", description="ViralAI command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser("detect-mutations", help="Detect mutations between two genomes")
    detect.add_argument("--reference", required=True, help="Reference genome sequence")
    detect.add_argument("--query", required=True, help="Query genome sequence")
    detect.add_argument(
        "--output", type=Path, default=None, help="Write JSON output to this file instead of stdout"
    )

    list_plugins_cmd = subparsers.add_parser("list-plugins", help="List available plugins")
    list_plugins_cmd.add_argument(
        "--plugins-dir",
        type=Path,
        default=Path("plugins"),
        help="Directory containing plugin packages",
    )

    serve = subparsers.add_parser("serve", help="Run the ViralAI API server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    issue_key = subparsers.add_parser(
        "issue-api-key",
        help="Issue a new API key directly (bootstrap -- no HTTP/auth required). "
        "Use this to create the first admin key before any API-based key management "
        "is possible.",
    )
    issue_key.add_argument("--label", required=True, help="Human-readable label for this key")
    issue_key.add_argument(
        "--role",
        required=True,
        choices=["viewer", "researcher", "admin"],
        help="Role to grant this key",
    )
    issue_key.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("VIRALAI_DATA_DIR", ".viralai_api_data")),
        help="Same directory the API server's VIRALAI_DATA_DIR points at",
    )

    dashboard = subparsers.add_parser(
        "dashboard", help="Print the Development Dashboard (module/plugin/model/benchmark status)"
    )
    dashboard.add_argument("--plugins-dir", type=Path, default=Path("plugins"))
    dashboard.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.environ.get("VIRALAI_DATA_DIR", ".viralai_api_data")),
        help="Directory containing the model registry and benchmark repository",
    )
    dashboard.add_argument(
        "--run-benchmarks",
        action="store_true",
        help="Run the benchmark suite before generating the report",
    )

    prototype_train = subparsers.add_parser(
        "prototype-train",
        help="Train a tiny synthetic hotspot model as a working prototype and persist it locally",
    )
    prototype_train.add_argument("--name", required=True, help="Model name to register")
    prototype_train.add_argument("--version", required=True, help="Model version to register")
    prototype_train.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".viralai_prototype"),
        help="Directory where the prototype registry and artifacts will be written",
    )
    prototype_train.add_argument(
        "--samples",
        type=int,
        default=40,
        help="Number of synthetic training examples to generate",
    )

    evaluate = subparsers.add_parser(
        "evaluate-fasta",
        help="Evaluate mutation detection on FASTA inputs (single or batch).",
    )
    evaluate.add_argument("--reference", required=True, help="Reference FASTA filepath or genome payload")
    evaluate.add_argument("--query", required=True, help="Query FASTA filepath or a directory of FASTA files")
    evaluate.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".viralai_evaluation"),
        help="Directory to write evaluation reports",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "detect-mutations":
        return _run_detect_mutations(args)
    if args.command == "list-plugins":
        return _run_list_plugins(args)
    if args.command == "serve":
        return _run_serve(args)
    if args.command == "issue-api-key":
        return _run_issue_api_key(args)
    if args.command == "dashboard":
        return _run_dashboard(args)
    if args.command == "prototype-train":
        return _run_prototype_train(args)
    if args.command == "evaluate-fasta":
        return _run_evaluate_fasta(args)

    parser.print_help()
    return 1


def _run_detect_mutations(args: argparse.Namespace) -> int:
    engine = MutationEngine()
    reference = _coerce_genome_input(args.reference)
    query = _coerce_genome_input(args.query)
    mutations = engine.detect_mutations(reference, query)
    payload = [m.model_dump(mode="json") for m in mutations]
    output_text = json.dumps(payload, indent=2)

    if args.output:
        args.output.write_text(output_text, encoding="utf-8")
        print(f"Wrote {len(mutations)} mutation(s) to {args.output}")
    else:
        print(output_text)
    return 0


def _coerce_genome_input(value: str | Path) -> str | Genome:
    if isinstance(value, Path):
        text = value.read_text(encoding="utf-8")
        # FASTA single-record detection: header lines start with '>'
        if text.strip().startswith(">"):
            seq_lines = [line.strip() for line in text.splitlines() if line and not line.startswith(">")]
            return "".join(seq_lines).upper()
        try:
            data = json.loads(text)
        except Exception:
            # Not JSON — return raw text trimmed (plain sequence string)
            return text.strip()
        if isinstance(data, str):
            return data
        return Genome.model_validate(data)
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.startswith("{"):
            return Genome.model_validate(json.loads(candidate))
        path = Path(candidate)
        if path.exists() and path.is_file():
            text = path.read_text(encoding="utf-8")
            if text.strip().startswith(">"):
                seq_lines = [line.strip() for line in text.splitlines() if line and not line.startswith(">")]
                return "".join(seq_lines).upper()
            try:
                data = json.loads(text)
            except Exception:
                return text.strip()
            if isinstance(data, str):
                return data
            return Genome.model_validate(data)
        return candidate
    return value


def _run_list_plugins(args: argparse.Namespace) -> int:
    manifests = list_plugin_manifests(args.plugins_dir)
    if not manifests:
        print(f"No plugins found in {args.plugins_dir}")
        return 0
    for manifest in manifests:
        print(
            f"{manifest.name} v{manifest.version} "
            f"[{manifest.certification_tier.value}] -- {', '.join(manifest.supported_viruses)}"
        )
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    import uvicorn  # local import -- only needed for this subcommand

    uvicorn.run("viralai.api.app:app", host=args.host, port=args.port)
    return 0


def _run_issue_api_key(args: argparse.Namespace) -> int:
    store = APIKeyStore(storage_path=args.data_dir / "api_keys.json")
    role = Role[args.role.upper()]
    raw_key, record = store.issue_key(args.label, role)

    print(f"Issued API key '{record.key_id}' (role={role.name}, label={args.label!r})")
    print(f"Raw key (shown once, store it securely): {raw_key}")
    return 0


def _run_dashboard(args: argparse.Namespace) -> int:
    registry = ModelRegistry(storage_dir=args.data_dir / "models")
    benchmarks = BenchmarkRepository(storage_path=args.data_dir / "benchmarks.json")

    if args.run_benchmarks:
        benchmarks.run_and_record()

    snapshot = build_snapshot(
        plugins_dir=args.plugins_dir, model_registry=registry, benchmark_repository=benchmarks
    )
    print(to_markdown(snapshot))
    return 0


def _run_prototype_train(args: argparse.Namespace) -> int:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = ModelRegistry(storage_dir=output_dir / "models")
    pipeline = AITrainingPipelineManager(registry)
    examples = _build_prototype_examples(samples=args.samples)

    report = pipeline.run(
        name=args.name,
        version=args.version,
        training_examples=examples,
        notes="CLI prototype training run",
    )

    payload = {
        "model": {
            "name": report.model_record.name,
            "version": report.model_record.version,
            "model_type": report.model_record.model_type,
            "registered_at": report.model_record.registered_at.isoformat(),
        },
        "metrics": report.training_metrics,
        "feature_importances": report.feature_importances,
        "output_dir": str(output_dir),
    }
    print(json.dumps(payload, indent=2))
    return 0


def _build_prototype_examples(samples: int) -> list[LabeledExample]:
    examples: list[LabeledExample] = []
    for index in range(samples):
        position = index * 10
        genome_length = max(samples * 10, 100)
        mutation = Mutation(
            position=position,
            reference_base="A",
            observed_base="G",
            mutation_type=MutationType.SUBSTITUTION,
            confidence_score=0.9,
        )
        context = FeatureContext(
            genome_length=genome_length,
            entropy_at_position=(index % max(samples, 1)) / max(samples, 1),
        )
        label = int((position / genome_length) > 0.5)
        examples.append(LabeledExample(mutation=mutation, context=context, label=label))
    return examples


def _run_evaluate_fasta(args: argparse.Namespace) -> int:
    out_dir = args.output_dir.resolve()
    reports_dir = out_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    engine = MutationEngine()
    reference = _coerce_genome_input(args.reference)

    qpath = Path(args.query)
    query_files: list[Path] = []
    if qpath.is_dir():
        for p in sorted(qpath.iterdir()):
            if p.is_file() and p.suffix.lower() in {".fasta", ".fa", ".txt"}:
                query_files.append(p)
    else:
        query_files = [qpath]

    summary = []
    for q in query_files:
        start = monotonic()
        query_seq = _coerce_genome_input(q)
        mutations = engine.detect_mutations(reference, query_seq)
        elapsed = monotonic() - start
        positions = [m.position for m in mutations]
        report = {
            "reference": str(args.reference),
            "query": q.name,
            "mutation_count": len(mutations),
            "positions": positions,
            "runtime_seconds": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        (reports_dir / f"{q.stem}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Processed {q.name}: {len(mutations)} mutations in {elapsed:.3f}s")
        summary.append(report)

    index_path = out_dir / "evaluation_index.json"
    index_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {len(summary)} report(s) to {reports_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
