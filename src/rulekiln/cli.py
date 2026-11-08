"""Command-line interface.

``rulekiln bench`` runs the full offline benchmark and, unless ``--no-write`` is
given, writes ``benchmarks/results.json`` and ``benchmarks/manifest.json``. The
manifest records the git SHA (``n/a`` when unavailable), the Python version and
the dataset checksum so a run can be reproduced and audited.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .benchmark import BenchmarkConfig, run_benchmark


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        sha = out.stdout.strip()
        return sha if out.returncode == 0 and sha else "n/a"
    except Exception:
        return "n/a"


def _print_summary(report: Any) -> None:
    print("\n=== rulekiln benchmark ===\n")
    print("Correctness (engine vs brute-force reference, differential):")
    for name, r in report.correctness.items():
        print(f"  {name:32s}  {r['agree']}/{r['bases']} agree  (rate {r['agreement_rate']:.4f})")
    q = report.quality
    print("\nConflict-resolution quality (firings-to-goal, lower is better):")
    print(f"  scenarios: {q['bases']}  random trials/scenario: {q['random_trials_per_base']}")
    print(f"  ordered (priority+spec+recency) mean : {q['ordered_firings_mean']:.3f}")
    print(f"  unordered (definition order)   mean  : {q['unordered_firings_mean']:.3f}")
    print(f"  random                         mean  : {q['random_firings_mean']:.3f}")
    lo, hi = q["reduction_vs_random_ci95"]
    print(
        f"  reduction vs random: {q['reduction_vs_random_mean']:.3f} firings "
        f"(95% CI [{lo:.3f}, {hi:.3f}], p={q['reduction_vs_random_pvalue']:.4g})"
    )
    lo, hi = q["reduction_vs_unordered_ci95"]
    print(
        f"  reduction vs unordered: {q['reduction_vs_unordered_mean']:.3f} firings "
        f"(95% CI [{lo:.3f}, {hi:.3f}], p={q['reduction_vs_unordered_pvalue']:.4g})"
    )
    print(f"  ordered beats random in {q['ordered_beats_random_rate']*100:.1f}% of scenarios")
    print(f"\ndataset checksum: {report.dataset_checksum}\n")


def _cmd_bench(args: argparse.Namespace) -> int:
    cfg = BenchmarkConfig(
        correctness_bases=args.correctness_bases,
        quality_bases=args.quality_bases,
        quality_random_trials=args.random_trials,
    )
    report = run_benchmark(cfg)
    _print_summary(report)

    if args.no_write:
        print("(--no-write: results not written to disk)")
        return 0

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "correctness": report.correctness,
        "quality": report.quality,
        "config": report.config,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True))

    manifest = {
        "tool": "rulekiln",
        "version": __version__,
        "git_sha": _git_sha(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dataset_checksum": report.dataset_checksum,
        "config": report.config,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"wrote {out_dir/'results.json'} and {out_dir/'manifest.json'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rulekiln", description=__doc__)
    parser.add_argument("--version", action="version", version=f"rulekiln {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    bench = sub.add_parser("bench", help="run the offline benchmark")
    bench.add_argument("--no-write", action="store_true", help="print only; do not write files")
    bench.add_argument("--out-dir", default="benchmarks", help="output directory (default: benchmarks)")
    bench.add_argument("--correctness-bases", type=int, default=300)
    bench.add_argument("--quality-bases", type=int, default=80)
    bench.add_argument("--random-trials", type=int, default=24)
    bench.set_defaults(func=_cmd_bench)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
