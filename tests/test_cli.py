import json

from rulekiln.cli import main


def test_bench_no_write(capsys):
    rc = main(["bench", "--no-write", "--correctness-bases", "20", "--quality-bases", "10", "--random-trials", "4"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "rulekiln benchmark" in out
    assert "dataset checksum" in out


def test_bench_writes_files(tmp_path):
    out_dir = tmp_path / "bench"
    rc = main(
        [
            "bench",
            "--out-dir",
            str(out_dir),
            "--correctness-bases",
            "20",
            "--quality-bases",
            "10",
            "--random-trials",
            "4",
        ]
    )
    assert rc == 0
    results = json.loads((out_dir / "results.json").read_text())
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert "correctness" in results and "quality" in results
    assert manifest["tool"] == "rulekiln"
    assert manifest["git_sha"]  # "n/a" or a real sha, never empty
    assert manifest["dataset_checksum"]
    assert "python" in manifest


def test_version_flag(capsys):
    import pytest

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
