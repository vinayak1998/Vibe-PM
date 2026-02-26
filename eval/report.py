"""Eval report generator: writes a timestamped markdown report after each full eval run."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Allow running from project root
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from eval.assertions import AssertionResult

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%d_%H%M%S")


def _ts_human(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def _yesno(value) -> str:
    return "Yes" if value else "No"


def _assertion_rows(results: List[AssertionResult]) -> str:
    lines = []
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        line = f"- [{mark}] `{r.name}`"
        if not r.passed and r.detail:
            line += f" — {r.detail}"
        lines.append(line)
    return "\n".join(lines)


def _model_metadata() -> str:
    """Return model routing info from config, with graceful fallback."""
    try:
        from config import MODELS
        parts = ", ".join(f"{k}={v}" for k, v in MODELS.items())
        return parts
    except Exception:
        return "unavailable"


def generate_report(
    scenario_results: List[dict],
    run_timestamp: datetime,
) -> Path:
    """
    Write eval/reports/eval_{timestamp}.md and return the path.

    Each entry in scenario_results must have:
        scenario: str
        state_dict: dict
        assertions: List[AssertionResult]
        transcript_path: Path  (may be None if the scenario errored)
        error: str | None      (set if the scenario raised an exception)
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"eval_{_ts(run_timestamp)}.md"

    lines: List[str] = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
    lines += [
        f"# Eval Report — {_ts_human(run_timestamp)}",
        "",
        "## Run Metadata",
        "",
        f"- **Models:** {_model_metadata()}",
        f"- **Scenarios run:** {len(scenario_results)}",
        f"- **Timestamp:** {_ts_human(run_timestamp)}",
        "",
    ]

    # -----------------------------------------------------------------------
    # Summary table
    # -----------------------------------------------------------------------
    lines += [
        "## Summary",
        "",
        "| Scenario | Assertions | Turns | Reached Done | Spec Length | Transcript |",
        "|---|---|---|---|---|---|",
    ]

    total_passed = 0
    total_checks = 0

    for sr in scenario_results:
        name = sr["scenario"]
        error = sr.get("error")
        if error:
            lines.append(f"| {name} | ERROR | — | — | — | — |")
            continue

        state = sr.get("state_dict", {})
        assertions: List[AssertionResult] = sr.get("assertions", [])
        passed = sum(1 for a in assertions if a.passed)
        total = len(assertions)
        total_passed += passed
        total_checks += total

        turns = state.get("turn_count", "—")
        reached_done = _yesno(state.get("reached_done", False))
        spec_length = state.get("spec_length", 0)
        tp = sr.get("transcript_path")
        transcript_link = f"[transcript]({tp.name})" if tp else "—"

        lines.append(
            f"| {name} | {passed}/{total} | {turns} | {reached_done} | {spec_length} | {transcript_link} |"
        )

    # Totals row
    lines.append(
        f"| **Total** | **{total_passed}/{total_checks}** | | | | |"
    )
    lines.append("")

    # -----------------------------------------------------------------------
    # Layer 2: Deterministic Assertions
    # -----------------------------------------------------------------------
    lines += [
        "## Layer 2: Deterministic Assertions",
        "",
        "> Programmatic pass/fail checks on transcript and final state.",
        "> Each check is either universal (all scenarios) or scenario-specific.",
        "",
    ]

    for sr in scenario_results:
        name = sr["scenario"]
        error = sr.get("error")
        assertions: List[AssertionResult] = sr.get("assertions", [])
        passed = sum(1 for a in assertions if a.passed)
        total = len(assertions)

        lines.append(f"### {name} ({passed}/{total} passed)")
        lines.append("")

        if error:
            lines.append(f"> **ERROR:** {error}")
        elif assertions:
            lines.append(_assertion_rows(assertions))
        else:
            lines.append("> No assertions recorded.")

        lines.append("")

    # -----------------------------------------------------------------------
    # Footer placeholder for future layers
    # -----------------------------------------------------------------------
    lines += [
        "---",
        "",
        "*Generated by eval/report.py — add Layer 3+ sections here as new eval layers are introduced.*",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
