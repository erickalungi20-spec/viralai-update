import json
from pathlib import Path

import pytest

from viralai.cli import build_parser, main


def test_detect_mutations_prints_json(capsys):
    exit_code = main(["detect-mutations", "--reference", "ATGCAATAA", "--query", "ATGCTATAA"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1
    assert output[0]["position"] == 4


def test_detect_mutations_writes_to_output_file(tmp_path, capsys):
    output_file = tmp_path / "result.json"

    exit_code = main(
        [
            "detect-mutations",
            "--reference",
            "ATGCAATAA",
            "--query",
            "ATGCTATAA",
            "--output",
            str(output_file),
        ]
    )

    assert exit_code == 0
    assert output_file.exists()
    data = json.loads(output_file.read_text())
    assert len(data) == 1
    assert "Wrote 1 mutation" in capsys.readouterr().out


def test_detect_mutations_accepts_json_genome_payloads(tmp_path, capsys):
    payload_path = tmp_path / "genome.json"
    payload_path.write_text(
        json.dumps(
            {
                "genome_id": "cli-test",
                "virus_species": "TestVirus",
                "sequence": "ACGTACGT",
                "gene_features": [{"name": "E6", "start": 0, "end": 3, "feature_type": "orf"}],
            }
        )
    )

    exit_code = main(["detect-mutations", "--reference", str(payload_path), "--query", "ACGTCCGT"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1
    assert output[0]["supporting_evidence"]["gene_feature"] == "E6"


def test_list_plugins_with_no_plugins_dir(tmp_path, capsys):
    exit_code = main(["list-plugins", "--plugins-dir", str(tmp_path / "nonexistent")])

    assert exit_code == 0
    assert "No plugins found" in capsys.readouterr().out


def test_list_plugins_lists_a_fixture_plugin(tmp_path, capsys):
    plugin_dir = tmp_path / "plugins" / "fixture-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "fixture-plugin",
                "version": "0.1.0",
                "supported_viruses": ["FixtureVirus"],
                "compatible_core_engine_versions": "*",
                "authors": ["Test"],
                "license": "Apache-2.0",
                "reference_genome_citations": ["Fixture Citation"],
            }
        )
    )

    exit_code = main(["list-plugins", "--plugins-dir", str(tmp_path / "plugins")])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "fixture-plugin" in output
    assert "experimental" in output


def test_prototype_train_command_creates_registered_model(tmp_path, capsys):
    output_dir = tmp_path / "prototype-output"

    exit_code = main(
        [
            "prototype-train",
            "--name",
            "demo-prototype",
            "--version",
            "0.1.0",
            "--output-dir",
            str(output_dir),
            "--samples",
            "40",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["model"]["name"] == "demo-prototype"
    assert payload["model"]["version"] == "0.1.0"
    assert payload["metrics"]["train_f1"] >= 0.0
    assert (output_dir / "models" / "demo-prototype" / "0.1.0" / "record.json").exists()


def test_no_command_raises_system_exit():
    with pytest.raises(SystemExit):
        main([])


def test_build_parser_has_expected_subcommands():
    parser = build_parser()

    args = parser.parse_args(["detect-mutations", "--reference", "A", "--query", "A"])
    assert args.command == "detect-mutations"

    args = parser.parse_args(["list-plugins"])
    assert args.command == "list-plugins"

    args = parser.parse_args(["serve"])
    assert args.command == "serve"
    assert args.port == 8000


def test_serve_command_invokes_uvicorn_with_expected_args(monkeypatch):
    calls = {}

    def fake_run(app_path, host, port):
        calls["app_path"] = app_path
        calls["host"] = host
        calls["port"] = port

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", fake_run)

    exit_code = main(["serve", "--host", "0.0.0.0", "--port", "9000"])

    assert exit_code == 0
    assert calls == {"app_path": "viralai.api.app:app", "host": "0.0.0.0", "port": 9000}


def test_issue_api_key_prints_raw_key_once(tmp_path, capsys):
    exit_code = main(
        ["issue-api-key", "--label", "cli-test", "--role", "admin", "--data-dir", str(tmp_path)]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "role=ADMIN" in output
    assert "cli-test" in output
    assert "Raw key" in output


def test_issue_api_key_persists_and_is_verifiable(tmp_path):
    from viralai.security.api_keys import APIKeyStore

    main(
        [
            "issue-api-key",
            "--label",
            "persisted-key",
            "--role",
            "researcher",
            "--data-dir",
            str(tmp_path),
        ]
    )

    store = APIKeyStore(storage_path=tmp_path / "api_keys.json")
    keys = store.list_keys()
    assert len(keys) == 1
    assert keys[0].label == "persisted-key"


def test_dashboard_command_prints_markdown_report(tmp_path, capsys):
    plugins_dir = Path(__file__).resolve().parents[2] / "plugins"

    exit_code = main(
        [
            "dashboard",
            "--plugins-dir",
            str(plugins_dir),
            "--data-dir",
            str(tmp_path),
            "--run-benchmarks",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "# ViralAI Development Dashboard" in output
    assert "hpv16" in output


def test_dashboard_command_without_running_benchmarks(tmp_path, capsys):
    empty_plugins_dir = tmp_path / "plugins"
    empty_plugins_dir.mkdir()

    exit_code = main(
        ["dashboard", "--plugins-dir", str(empty_plugins_dir), "--data-dir", str(tmp_path / "data")]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "0/0 datasets passing" in output
