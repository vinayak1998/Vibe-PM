"""Layer 2 eval: deterministic pass/fail assertions on transcript and final state."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AssertionResult:
    name: str
    passed: bool
    detail: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DISCOVERY_FIELDS = [
    "target_user",
    "core_problem",
    "current_alternatives",
    "why_now",
    "feature_wishlist",
    "success_metric",
    "revenue_model",
    "constraints",
]

_SOCIAL_KEYWORDS = ("social", "analytics", "admin", "dashboard")

_SPEC_HEADERS = ("## problem", "## mvp", "## core", "## user", "## feature", "## open")


def _turns_in_phase(transcript: List[dict], phase: str) -> int:
    return sum(1 for t in transcript if t.get("phase") == phase)


def _has_error_turn(transcript: List[dict]) -> bool:
    for t in transcript:
        if t.get("phase") == "error":
            return True
        assistant = t.get("assistant", "")
        if isinstance(assistant, str) and "[ERROR" in assistant:
            return True
    return False


def _nonempty(value) -> bool:
    """True if value is a non-empty string or non-empty list."""
    if isinstance(value, list):
        return len(value) > 0
    return bool(value and str(value).strip())


def _discovery_fill_count(discovery: dict) -> int:
    """Count how many of the 8 DiscoverySummary fields are non-empty."""
    return sum(1 for field in _DISCOVERY_FIELDS if _nonempty(discovery.get(field)))


# ---------------------------------------------------------------------------
# Universal assertions (all scenarios)
# ---------------------------------------------------------------------------

def universal_assertions(transcript: List[dict], state_dict: dict) -> List[AssertionResult]:
    results: List[AssertionResult] = []
    phases = state_dict.get("phases_visited", [])
    discovery = state_dict.get("discovery_summary") or {}
    scoping = state_dict.get("scoping_output") or {}
    spec = state_dict.get("spec_markdown", "")

    # ------------------------------------------------------------------
    # Pipeline completion
    # ------------------------------------------------------------------

    # reached_done
    reached_done = state_dict.get("reached_done", False)
    results.append(AssertionResult(
        name="reached_done",
        passed=reached_done,
        detail="" if reached_done else f"final phase was '{state_dict.get('phase')}'",
    ))

    # reached_scoping (standalone — distinct from all_phases_visited)
    reached_scoping = "scoping" in phases
    results.append(AssertionResult(
        name="reached_scoping",
        passed=reached_scoping,
        detail="" if reached_scoping else f"phases seen: {phases}",
    ))

    # spec_generated
    spec_length = state_dict.get("spec_length", 0)
    spec_ok = spec_length > 0
    results.append(AssertionResult(
        name="spec_generated",
        passed=spec_ok,
        detail="" if spec_ok else "spec_markdown is empty or missing",
    ))

    # all_phases_visited (discovery → scoping → spec, in order)
    required = ["discovery", "scoping", "spec"]
    all_present = all(p in phases for p in required)
    if all_present:
        indices = [phases.index(p) for p in required]
        in_order_ok = indices == sorted(indices)
    else:
        in_order_ok = False
    phases_ok = all_present and in_order_ok
    results.append(AssertionResult(
        name="all_phases_visited",
        passed=phases_ok,
        detail="" if phases_ok else f"phases seen: {phases}",
    ))

    # no_errors
    no_errors = not _has_error_turn(transcript)
    results.append(AssertionResult(
        name="no_errors",
        passed=no_errors,
        detail="" if no_errors else "at least one turn has phase=error or [ERROR in assistant text",
    ))

    # ------------------------------------------------------------------
    # Discovery quality
    # ------------------------------------------------------------------

    # target_user_extracted
    target_user = discovery.get("target_user", "")
    has_target = _nonempty(target_user)
    results.append(AssertionResult(
        name="target_user_extracted",
        passed=has_target,
        detail="" if has_target else "discovery_summary.target_user is empty",
    ))

    # core_problem_extracted
    core_problem = discovery.get("core_problem", "")
    has_problem = _nonempty(core_problem)
    results.append(AssertionResult(
        name="core_problem_extracted",
        passed=has_problem,
        detail="" if has_problem else "discovery_summary.core_problem is empty",
    ))

    # discovery_completeness — pass if >= 6/8 fields filled (project threshold: 75%)
    filled = _discovery_fill_count(discovery)
    completeness_ok = filled >= 6
    results.append(AssertionResult(
        name="discovery_completeness",
        passed=completeness_ok,
        detail="" if completeness_ok else f"{filled}/8 fields filled — need >= 6",
    ))

    # min_discovery_turns — universal floor of 4 turns in discovery
    discovery_turns = _turns_in_phase(transcript, "discovery")
    min_turns_ok = discovery_turns >= 4
    results.append(AssertionResult(
        name="min_discovery_turns",
        passed=min_turns_ok,
        detail="" if min_turns_ok else f"only {discovery_turns} discovery turn(s) — need >= 4",
    ))

    # no_multi_question — heuristic: any discovery assistant message with 2+ "?" is a violation
    multi_q_violations = [
        i
        for i, t in enumerate(transcript)
        if t.get("phase") == "discovery"
        and isinstance(t.get("assistant"), str)
        and t["assistant"].count("?") >= 2
    ]
    no_multi_q = len(multi_q_violations) == 0
    results.append(AssertionResult(
        name="no_multi_question",
        passed=no_multi_q,
        detail=(
            ""
            if no_multi_q
            else f"turns {multi_q_violations} each contain 2+ '?' (heuristic: may be asking multiple questions)"
        ),
    ))

    # ------------------------------------------------------------------
    # Scoping quality
    # ------------------------------------------------------------------

    mvp_features = scoping.get("mvp_features", []) or []
    cut_features = scoping.get("cut_features", []) or []
    comparable_products = scoping.get("comparable_products", []) or []
    core_user_flow = scoping.get("core_user_flow", "")

    # has_p0_features
    p0_features = [f for f in mvp_features if (f.get("priority") if isinstance(f, dict) else None) == "P0"]
    has_p0 = len(p0_features) > 0
    results.append(AssertionResult(
        name="has_p0_features",
        passed=has_p0,
        detail="" if has_p0 else "no P0 features found in scoping_output.mvp_features",
    ))

    # has_cut_features (universal floor: >= 1)
    has_cuts = len(cut_features) >= 1
    results.append(AssertionResult(
        name="has_cut_features",
        passed=has_cuts,
        detail="" if has_cuts else "scoping_output.cut_features is empty — agent cut nothing",
    ))

    # has_comparable_products
    has_comps = len(comparable_products) >= 1
    results.append(AssertionResult(
        name="has_comparable_products",
        passed=has_comps,
        detail="" if has_comps else "scoping_output.comparable_products is empty — web search returned nothing",
    ))

    # social_not_p0 — P0 features must not contain forbidden keywords
    def _feature_text(f) -> str:
        if isinstance(f, dict):
            return f"{f.get('name', '')} {f.get('description', '')}".lower()
        return ""

    social_violations = [
        f.get("name", str(f))
        for f in p0_features
        if any(kw in _feature_text(f) for kw in _SOCIAL_KEYWORDS)
    ]
    social_ok = len(social_violations) == 0
    results.append(AssertionResult(
        name="social_not_p0",
        passed=social_ok,
        detail=(
            ""
            if social_ok
            else f"P0 feature(s) contain forbidden keywords (social/analytics/admin/dashboard): {social_violations}"
        ),
    ))

    # has_core_user_flow
    has_flow = _nonempty(core_user_flow)
    results.append(AssertionResult(
        name="has_core_user_flow",
        passed=has_flow,
        detail="" if has_flow else "scoping_output.core_user_flow is empty",
    ))

    # ------------------------------------------------------------------
    # Spec quality
    # ------------------------------------------------------------------

    # spec_no_hallucination_check — target_user string should appear in spec
    if _nonempty(target_user) and _nonempty(spec):
        spec_contains_user = target_user.strip().lower()[:40] in spec.lower()
        results.append(AssertionResult(
            name="spec_no_hallucination_check",
            passed=spec_contains_user,
            detail=(
                ""
                if spec_contains_user
                else f"spec does not contain target_user '{target_user[:40]}' (weak consistency proxy)"
            ),
        ))
    else:
        # Skip rather than false-fail when prerequisites are missing
        results.append(AssertionResult(
            name="spec_no_hallucination_check",
            passed=False,
            detail="skipped — target_user or spec is empty (prerequisite missing)",
        ))

    # spec_has_sections — at least 2 expected ## headers present
    spec_lower = spec.lower()
    matched_headers = [h for h in _SPEC_HEADERS if h in spec_lower]
    sections_ok = len(matched_headers) >= 2
    results.append(AssertionResult(
        name="spec_has_sections",
        passed=sections_ok,
        detail=(
            ""
            if sections_ok
            else f"only {len(matched_headers)} expected section header(s) found — need >= 2"
        ),
    ))

    # spec_no_empty_tbd — TBD count should be <= 3
    tbd_count = spec.upper().count("TBD")
    tbd_ok = tbd_count <= 3
    results.append(AssertionResult(
        name="spec_no_empty_tbd",
        passed=tbd_ok,
        detail="" if tbd_ok else f"{tbd_count} TBD(s) in spec — expected <= 3",
    ))

    return results


# ---------------------------------------------------------------------------
# Scenario-specific assertions
# ---------------------------------------------------------------------------

def _assert_over_scoper(transcript: List[dict], state_dict: dict) -> List[AssertionResult]:
    scoping = state_dict.get("scoping_output") or {}
    cut_features = scoping.get("cut_features", []) or []
    n_cut = len(cut_features)
    passed = n_cut >= 3
    return [AssertionResult(
        name="features_cut",
        passed=passed,
        detail="" if passed else f"only {n_cut} feature(s) cut — expected >= 3 for over_scoper",
    )]


def _assert_clear_thinker(transcript: List[dict], state_dict: dict) -> List[AssertionResult]:
    turn_count = state_dict.get("turn_count", 0)
    passed = turn_count <= 15
    return [AssertionResult(
        name="finished_efficiently",
        passed=passed,
        detail="" if passed else f"took {turn_count} turns — expected <= 15 for clear_thinker",
    )]


def _assert_arguer(transcript: List[dict], state_dict: dict) -> List[AssertionResult]:
    negotiation_rounds = state_dict.get("negotiation_rounds", 0)
    passed = negotiation_rounds > 0
    return [AssertionResult(
        name="negotiation_rounds_nonzero",
        passed=passed,
        detail="" if passed else "negotiation_rounds == 0 — pushback was not registered by the scoping agent",
    )]


def _assert_pivoter(transcript: List[dict], state_dict: dict) -> List[AssertionResult]:
    turn_count = state_dict.get("turn_count", 0)
    passed = turn_count >= 6
    return [AssertionResult(
        name="handled_pivot",
        passed=passed,
        detail="" if passed else f"only {turn_count} turns — expected >= 6 to handle a mid-conversation pivot",
    )]


def _assert_vague_founder(transcript: List[dict], state_dict: dict) -> List[AssertionResult]:
    discovery_turns = _turns_in_phase(transcript, "discovery")
    passed = discovery_turns >= 5
    return [AssertionResult(
        name="probed_vague_answers",
        passed=passed,
        detail="" if passed else f"only {discovery_turns} discovery turn(s) — expected >= 5 for vague_founder",
    )]


_SCENARIO_ASSERTIONS = {
    "over_scoper": _assert_over_scoper,
    "clear_thinker": _assert_clear_thinker,
    "arguer": _assert_arguer,
    "pivoter": _assert_pivoter,
    "vague_founder": _assert_vague_founder,
}


def scenario_assertions(
    scenario_name: str,
    transcript: List[dict],
    state_dict: dict,
) -> List[AssertionResult]:
    fn = _SCENARIO_ASSERTIONS.get(scenario_name)
    if fn is None:
        return []
    return fn(transcript, state_dict)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_assertions(
    scenario_name: str,
    transcript: List[dict],
    state_dict: dict,
) -> List[AssertionResult]:
    """Run universal + scenario-specific assertions; return all results."""
    return universal_assertions(transcript, state_dict) + scenario_assertions(
        scenario_name, transcript, state_dict
    )


def print_checklist(scenario_name: str, results: List[AssertionResult]) -> None:
    """Print a formatted pass/fail checklist to stdout."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"--- Assertions: {scenario_name} [{passed}/{total} passed] ---")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        line = f"  [{mark}] {r.name}"
        if not r.passed and r.detail:
            line += f"  ({r.detail})"
        print(line)
    print()
