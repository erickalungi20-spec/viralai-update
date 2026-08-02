from pathlib import Path

from viralai.security.plugin_scanner import is_clean, scan_plugin_directory, scan_plugin_source


def test_clean_file_has_no_findings(tmp_path):
    clean_file = tmp_path / "clean.py"
    clean_file.write_text(
        "from viralai.plugins.base import VirusPlugin\n\nclass Plugin(VirusPlugin):\n    pass\n"
    )

    findings = scan_plugin_source(clean_file)

    assert findings == []


def test_eval_call_is_flagged_high_severity(tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("x = eval(user_input)\n")

    findings = scan_plugin_source(bad_file)

    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert "eval" in findings[0].description


def test_exec_call_is_flagged(tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("exec('print(1)')\n")

    findings = scan_plugin_source(bad_file)

    assert any("exec" in f.description for f in findings)


def test_subprocess_import_is_flagged_medium_severity(tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("import subprocess\n")

    findings = scan_plugin_source(bad_file)

    assert len(findings) == 1
    assert findings[0].severity == "medium"


def test_from_import_of_dangerous_module_is_flagged(tmp_path):
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("from os import system\n")

    findings = scan_plugin_source(bad_file)

    assert any("os" in f.description for f in findings)


def test_json_and_pathlib_imports_are_allowed(tmp_path):
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("import json\nimport pathlib\nfrom typing import Any\n")

    findings = scan_plugin_source(clean_file)

    assert findings == []


def test_syntax_error_is_flagged_high_severity(tmp_path):
    bad_file = tmp_path / "broken.py"
    bad_file.write_text("def broken(:\n")

    findings = scan_plugin_source(bad_file)

    assert len(findings) == 1
    assert findings[0].severity == "high"


def test_scan_plugin_directory_covers_all_py_files(tmp_path):
    (tmp_path / "clean.py").write_text("x = 1\n")
    (tmp_path / "bad.py").write_text("eval('1')\n")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "also_bad.py").write_text("import subprocess\n")

    results = scan_plugin_directory(tmp_path)

    assert "clean.py" not in results
    assert "bad.py" in results
    assert "data/also_bad.py" in results


def test_is_clean_true_when_no_high_severity_findings():
    results = {"file.py": []}
    assert is_clean(results) is True


def test_is_clean_false_with_high_severity_finding(tmp_path):
    (tmp_path / "bad.py").write_text("eval('1')\n")
    results = scan_plugin_directory(tmp_path)
    assert is_clean(results) is False


def test_is_clean_true_with_only_medium_severity_findings(tmp_path):
    (tmp_path / "medium.py").write_text("import subprocess\n")
    results = scan_plugin_directory(tmp_path)
    assert is_clean(results) is True  # medium findings don't block, just flag for review


def test_real_hpv16_plugin_is_clean():
    """The actual shipped plugin should pass its own security scan."""
    hpv16_dir = Path(__file__).resolve().parents[2] / "plugins" / "hpv16"
    results = scan_plugin_directory(hpv16_dir)
    assert is_clean(results), f"HPV16 plugin has high-severity findings: {results}"
