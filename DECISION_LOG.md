# Decision Log

Chronological log of architectural and product decisions for the AI PM Agent (Vibe-PM). Updated when changes are reviewed and confirmed.

Format per entry:

- **Context**: Why this came up
- **Decision**: What was decided
- **Alternatives considered**: What else was on the table
- **Tradeoffs**: What we gain/lose
- **Status**: Accepted | Superseded by [reference]

---

## Foundation Decisions (Feb 22)

### 2026-02-22: Multi-agent vs single agent

**Context**: Need to validate whether specialized agents (Discovery, Scoping, Spec Writer) outperform one well-prompted PM agent. A single mega-prompt would handle discovery, scoping, and spec in one flow, but risks prompt dilution and makes per-phase evaluation impossible.

**Decision**: Build with 3 specialized agents and a simple phase manager (orchestrator). Each agent gets a focused system prompt and a model suited to its task.

**Alternatives considered**: Single mega-prompt agent handling all phases in one conversation flow.

**Tradeoffs**: Gain separation of concerns, clearer state boundaries, per-phase testability, and model-per-task optimization. Lose some cross-phase conversational nuance and add routing/orchestration code.

**Status**: Accepted

---

### 2026-02-22: Open-source models only

**Context**: Project goal is zero vendor lock-in and cost-effective inference. Using proprietary models (GPT-4, Claude) would create provider dependency and make the project expensive to demo.

**Decision**: Use only open-source models (Llama, GPT-OSS) via Groq/Together/LiteLLM. No proprietary models in the main pipeline.

**Alternatives considered**: Proprietary models for quality; hybrid approach (e.g., GPT-4 for conversation, OSS for extraction).

**Tradeoffs**: Gain portability and cost control. Accept possible quality/reliability gaps vs top proprietary models. Mitigated by using task-specific models (MoE) rather than one model for everything.

**Status**: Accepted

---

### 2026-02-22: Groq as primary inference provider

**Context**: Need fast, free-tier-friendly inference for development and demos. Latency matters for a conversational agent -- users expect near-instant responses.

**Decision**: Use Groq as primary provider (via LiteLLM abstraction). Backup options: Together AI, OpenRouter.

**Alternatives considered**: OpenAI, Anthropic, local inference (Ollama), other OSS hosts.

**Tradeoffs**: Gain best-in-class speed (LPU hardware, 280-1000 tokens/sec) and a generous free tier. Accept dependency on Groq's availability and model catalog.

**Status**: Accepted

---

### 2026-02-22: Task-based model routing (Mixture of Experts)

**Context**: Different tasks have different cost/quality tradeoffs. Discovery and Scoping need nuanced multi-turn dialogue (reasoning model). Spec generation needs quality long-form writing (large model). Extraction and classification are simple structured tasks (small fast model).

**Decision**: Route by task type: `conversation` -> GPT-OSS 20B (reasoning model), `spec` -> Llama 3.3 70B, `extraction`/`classification` -> Llama 3.1 8B. Single `llm_call(task_type, messages)` API. Routing is a static lookup in `config.MODELS`.

**Alternatives considered**: One model for everything (simpler but wasteful); dynamic router based on content analysis (complex, another LLM call).

**Tradeoffs**: Gain efficiency (most turns use cheap 8B + 20B, only spec uses 70B) and quality per task (reasoning improves conversation, 70B improves spec). Lose simplicity of a single model.

**Status**: Accepted

---

## Discovery Agent Evolution (Feb 22-23)

### 2026-02-22: Per-aspect discovery confirmation (V1)

**Context**: Discovery covers 8 aspects but had no per-aspect confirmation. The agent could move from target user to pain points without formalizing and confirming the persona. Users never got to say "that's right" or "change that" for individual aspects.

**Decision**: Add a formalize-then-confirm loop per aspect. Before moving to the next aspect, the agent summarizes what it learned, asks the user to confirm or revise. An intent classifier (CONFIRM/CORRECT/OTHER) gates progression. State tracks `discovery_confirmed_aspects` list and `awaiting_discovery_confirmation` flag.

**Alternatives considered**: Keep end-of-discovery-only confirmation; add completeness-based checkpoint without per-aspect gates.

**Tradeoffs**: Gain granular user control per aspect. Add significant complexity: per-aspect state machine, intent classifier per turn, hardcoded aspect ordering.

**Status**: Superseded by "Simplify pipeline" (2026-02-23). The per-aspect FSM created rigid behavior, dead loops, and premature formalization.

---

### 2026-02-22: Fix discovery agent flow (extraction timing + turn counter)

**Context**: Three bugs in the per-aspect discovery agent: (1) extraction ran before the conversational turn, causing premature formalization from the user's first message, (2) the formalize LLM call was disconnected from conversation context (synthetic message with no history), (3) no minimum depth before formalization could trigger.

**Decision**: (1) Move extraction to after the conversational turn. (2) Pass full `state.messages` to formalization instead of a synthetic prompt. (3) Add `discovery_aspect_turns` counter -- require at least 1 conversational turn before formalization triggers. Reset counter on confirm/correct.

**Alternatives considered**: Fix the prompt alone (wouldn't solve the extraction-before-conversation ordering bug).

**Tradeoffs**: Fixes the immediate bugs within the per-aspect architecture. Does not address the fundamental fragility of the FSM approach.

**Status**: Superseded by "Simplify pipeline" (2026-02-23). The per-aspect architecture itself was replaced.

---

### 2026-02-22: Graceful discovery start + off-topic handling

**Context**: Every first user message was treated as "product idea shared," causing the agent to immediately ask about target user even when the user just said "hi." Off-topic and non-sequential messages during discovery were handled rigidly.

**Decision**: (1) Add `DISCOVERY_ASK_FOR_IDEA_PROMPT` -- when the user hasn't shared an idea yet (first message), respond naturally and ask for their idea. Skip extraction. (2) Add off-topic redirect instructions to the discovery and scoping system prompts ("If they go off-topic, briefly acknowledge and redirect"). (3) Non-sequential answers (user answers about a different aspect) are acknowledged and woven in, then conversation redirected.

**Alternatives considered**: LLM-based turn-type classifier (greeting vs product_idea) -- decided the simple heuristic (first message) was sufficient.

**Tradeoffs**: Gain natural conversation start and graceful handling of edge cases. Minor: the first-message heuristic could miss multi-greeting users (accepted as low priority).

**Status**: Accepted. `DISCOVERY_ASK_FOR_IDEA_PROMPT` is in production.

---

### 2026-02-22: Show active agent in UI

**Context**: All assistant messages showed the same generic author. Users couldn't tell which agent (Discovery, Scoping, Spec Writer) produced each response. No indication of "work in progress" during phase transitions.

**Decision**: (1) Add `PHASE_AUTHOR` mapping (`discovery` -> "Discovery", `scoping` -> "Scoping", `spec` -> "Spec Writer", `done` -> "PM") and pass as `author` to `cl.Message`. (2) Add `step_callback` in the orchestrator for progress indicators during transitions (e.g., "Researching comparable products...").

**Alternatives considered**: Chainlit `Steps` for a more structured UI -- decided simple author labels were sufficient for MVP.

**Tradeoffs**: Gain clarity about which agent is speaking and visibility into background work. No significant downsides.

**Status**: Accepted

---

### 2026-02-22: Rigorous scoping with web search guarantees

**Context**: The Scoping Agent called `search_comparable_products()` but comparable products often didn't reach the spec. The model's natural-language proposal didn't always cite them explicitly enough for the extractor to parse, so `comparable_products` was often empty in the structured output.

**Decision**: After extraction, merge the raw DuckDuckGo search results directly into `state.scoping_output.comparable_products`, deduplicating by name and URL. Also add `key_screens` to `ScopingOutput` schema and require the scoping prompt to produce 3-5 key screens.

**Alternatives considered**: Fix the extraction prompt to be better at parsing comparables (fragile, model-dependent).

**Tradeoffs**: Gain guaranteed comparable products in the spec whenever search succeeds. Merge logic adds ~15 lines of code but eliminates a class of extraction failures.

**Status**: Accepted

---

### 2026-02-22: Fix prompt template KeyError (.format vs .replace)

**Context**: `EXTRACTION_DISCOVERY_PROMPT` and `EXTRACTION_SCOPING_PROMPT` contain literal JSON braces (`{`, `}`). Python's `str.format()` interpreted these as format placeholders, causing `KeyError('\n  "target_user"')`. The error propagated to users because the `.format()` call was outside the try/except block.

**Decision**: Replace `.format(conversation=...)` with `.replace("{conversation}", ...)` for both extraction prompts. Also move the template substitution inside the try/except so any future templating errors degrade gracefully.

**Alternatives considered**: Escape all braces in the JSON schema with `{{` / `}}` -- rejected as fragile and hard to read.

**Tradeoffs**: `.replace()` is slightly less expressive than `.format()` (single placeholder only) but eliminates the entire class of brace-interpretation bugs.

**Status**: Accepted

---

### 2026-02-23: Simplify discovery agent (LLM-first with light guardrails)

**Context**: The per-aspect discovery agent was an FSM fighting an LLM. Five branching code paths, an intent classifier per turn, a turn counter, and dual research triggers created loops and rigid behavior. The fix-on-fix approach (extraction timing, turn counter) was treating symptoms.

**Decision**: Strip the rigid state machine entirely. Replace with a single code path: (1) build dynamic prompt with confirmed/pending aspects, (2) single LLM call, (3) extract summary, (4) passive post-turn confirmation check. No hardcoded responses anywhere -- every user-facing message comes from the LLM. Research becomes opt-in (LLM offers, user agrees).

**Alternatives considered**: Keep the per-aspect FSM with better prompts; add more guardrails to the existing architecture.

**Tradeoffs**: Gain simplicity (one code path vs five) and natural conversation flow. Confirmation is passive -- a missed detection just means the LLM continues exploring naturally (no dead loops). Lose the strict per-aspect ordering guarantee.

**Status**: Superseded by "Simplify pipeline" (2026-02-23). This intermediate approach was further simplified into the checkpoint model.

---

### 2026-02-23: Simplify pipeline -- Code Orchestrator + Checkpoint Agents (V2)

**Context**: After two iterations of the Discovery agent (per-aspect FSM, then LLM-first single path), the fundamental issues became clear: (1) Discovery was generating PRDs/tables instead of conducting an interview, (2) handoffs between phases were invisible, (3) any per-aspect confirmation was fragile. Needed a clean break.

**Decision**: Complete rewrite of the pipeline:

1. **Discovery**: Remove all per-aspect tracking. Use extraction + `check_completeness()` after each turn; when complete (score >= 0.75, mandatory fields filled, >= 4 user turns), show summary for user confirmation. Add output validation (reject tables/PRDs, reject multi-question replies).
2. **Orchestrator**: Code-only with explicit handoff messages, skip prevention, no LLM orchestrator. Deterministic phase transitions with user confirmation.
3. **Scoping**: Add RICE scoring framework and phased implementation planning (Phase 1/2/3). Features scored by Reach, Impact, Confidence, Effort.
4. **Spec Writer**: Output phased spec organized by implementation phase, designed for AI code-gen tools.
5. **Schemas**: Add `ImplementationPhase`, RICE fields to `Feature`, `key_screens` to `ScopingOutput`, `discovery_summary_shown` flag.
6. **Docs**: Create SYSTEM_DESIGN.md and DECISION_LOG.md.

**Alternatives considered**: LLM orchestrator for flexible routing; hybrid (code router + LLM transition gates); keep per-aspect confirmation with better prompts.

**Tradeoffs**: Gain determinism, debuggability, clear user-confirmed handoffs, RICE-scored features, and phased specs. Lose flexibility (no "go back to discovery") and per-aspect granularity. Accepted: the completeness checkpoint covers the same ground with less fragility.

**Status**: Accepted. This is the current architecture.

---

## MoE and Model Routing (Feb 22)

### 2026-02-22: Implement 3-tier MoE model routing

**Context**: All task types were routing to the same model (`groq/llama-3.3-70b-versatile`). The routing plumbing existed in `config.py` and `models/llm.py` but wasn't differentiated.

**Decision**: Implement actual differentiation: (1) `MODEL_CONVERSATION = "groq/openai/gpt-oss-20b"` with reasoning enabled. (2) `MODEL_SPEC = "groq/llama-3.3-70b-versatile"` for spec generation. (3) `MODEL_EXTRACTION = "groq/llama-3.1-8b-instant"` for extraction and classification. Add `REASONING_EFFORT` and `INCLUDE_REASONING` config knobs. Inject reasoning params in `llm_call()` only when `task_type == "conversation"` and model is GPT-OSS.

**Alternatives considered**: Keep one model for everything (cheaper to maintain but wastes cost/quality); add a dynamic content-based router (another LLM call, more complexity).

**Tradeoffs**: Most turns now use cheap models (8B + 20B). Only the single spec call uses 70B. Per-conversation cost drops significantly while conversation quality improves via reasoning.

**Status**: Accepted

---

## Eval Framework Evolution (Feb 24 - Mar 9)

### 2026-02-24: LLM-simulated user for eval (Layer 1)

**Context**: The eval runner iterated over a fixed `user_messages` list. Since scenario YAMLs only defined `initial_message` (the `messages` lists were commented out), each scenario sent exactly 1 message, the agent replied once, and the eval ended -- never reaching scoping or spec. Fixed lists can't adapt to agent responses (the agent asks different questions each run).

**Decision**: Create `eval/simulated_user.py` with a `SimulatedUser` class that uses `llm_call("conversation", ...)` to generate the next user message given the conversation history, persona, and message policy. Four policies: `minimal` (one-word answers), `expansive` (full answers, cooperative), `pushback` (cooperative in discovery, fights cuts in scoping), `pivot` (changes idea mid-conversation). Conversation perspective inversion: agent messages become "user" role, founder messages become "assistant" role.

**Alternatives considered**: Write comprehensive fixed message lists per scenario (deterministic but can't adapt to varying agent questions); use a separate provider for simulation (adds API key complexity).

**Tradeoffs**: Gain realistic multi-turn conversations that reach all 3 phases. Lose determinism (each run varies). Accept LLM cost for simulation and need for rate-limit management.

**Status**: Accepted

---

### 2026-02-26: Layer 2 deterministic assertions

**Context**: Layer 1 (conversation simulation) generates transcripts and state, but there's no automated way to check if the output is correct. Manual review doesn't scale across 5 scenarios.

**Decision**: Create `eval/assertions.py` with `AssertionResult` dataclass and programmatic pass/fail checks. Split into universal assertions (all scenarios: reached_done, target_user_extracted, spec_non_empty, etc.) and scenario-specific assertions (over_scoper: features_cut >= 3, clear_thinker: turns <= 15, etc.). Integrate into runner with `print_checklist()`.

**Alternatives considered**: LLM-based evaluation only (non-deterministic, expensive); manual spot-checking (doesn't scale).

**Tradeoffs**: Gain zero-cost, deterministic, repeatable quality checks. Limited to structural checks -- can't evaluate conversation quality or naturalness (that's Layer 3's job).

**Status**: Accepted

---

### 2026-02-26: Expand assertions to full coverage

**Context**: Initial assertion set was minimal (6 checks). Missing coverage for discovery depth (completeness, min turns, multi-question), scoping quality (P0 features, RICE scores, comparable products, social-not-P0, phase timeline), and spec quality (hallucination check, section headers, TBD count).

**Decision**: Expand to 22 universal assertions + 5 scenario-specific = 27 total. Add `_nonempty()` helper that rejects null-like placeholder strings ("null", "none", "n/a", "tbd", etc.). Surface `negotiation_rounds` in state_dict for the arguer scenario. Replace arguer's scoping-turns proxy with direct `negotiation_rounds > 0` check.

**Alternatives considered**: Fewer, broader assertions (less diagnostic); more assertions per scenario (maintenance burden).

**Tradeoffs**: Comprehensive coverage catches subtle regressions (e.g., RICE scores going null, Phase 1 exceeding 4 weeks). Some heuristic assertions (multi-question detection) produce occasional false positives.

**Status**: Accepted

---

### 2026-02-26: Eval report generation

**Context**: Eval results were only printed to console and lost after the terminal closed. No way to compare across runs as prompts and models evolve.

**Decision**: Create `eval/report.py` with `generate_report()` that writes a timestamped markdown report (`eval/reports/eval_YYYYMMDD_HHMMSS.md`) after each run. Report includes: run metadata (models, timestamp), summary table (per-scenario assertions, turns, spec length), and full assertion detail per scenario. Structure designed for future Layer 3 section.

**Alternatives considered**: JSON output (less readable); database (overkill for MVP).

**Tradeoffs**: Gain persistent, human-readable run history. Reports accumulate on disk (gitignored, acceptable).

**Status**: Accepted

---

### 2026-03-09: LLM-as-Judge eval layer (Layer 3)

**Context**: Layer 2 assertions check structural correctness but can't evaluate qualitative aspects: Was the conversation natural? Were the right questions asked? Was the spec accurate? These require judgment.

**Decision**: Create `eval/judge.py` with `judge_transcript()` that sends the full transcript + rubric to the 70B model and gets 1-5 scores with reasoning across 5 dimensions (discovery_depth, conversation_naturalness, scoping_quality, spec_accuracy, argue_back_quality). Key design choices: (1) Use `response_format={"type": "json_object"}` for reliable JSON. (2) Prompt requires reasoning BEFORE score to prevent anchoring. (3) Judge decides N/A per dimension (not hardcoded per scenario). (4) Retry once on JSON parse failure. Add `--judge` CLI flag. Generate `eval/results.md` comparison table.

**Alternatives considered**: Human evaluation (doesn't scale); different provider for judging (adds API key complexity); hardcoded N/A mapping per scenario (less flexible).

**Tradeoffs**: Gain qualitative scoring at scale. Known limitation: same 70B model generates specs and judges them (self-bias risk). Mitigated by structured rubric and reasoning-first prompting. Flagged as future improvement: use a different provider for judging.

**Status**: Accepted

---

### 2026-03-09: Eval suite bug fixes (10 items)

**Context**: Running the full eval suite across all 5 scenarios revealed several bugs and gaps:

1. `all_phases_visited` expected `["discovery","scoping","spec"]` but `spec` phase is transient (never appears in transcripts).
2. No rate-limit delay before `simulator.next_message()`, causing TPM exhaustion.
3. `_nonempty()` accepted literal string `"null"` as a filled field, inflating completeness scores.
4. No assertion caught `[SIM ERROR` in user messages (masked broken runs).
5. Discovery agent generated 2+ questions per turn despite "ONE question at a time" rule.
6. DuckDuckGo rate-limited after 2-3 searches, returning empty for later scenarios.
7. No assertion for RICE scores on P0 features.
8. No assertion for Phase 1 timeline (MVP buildable in 2-4 weeks).
9. No assertion for Problem Statement being filled vs TBD.
10. SSL/transport resource warnings at shutdown.

**Decision**: Fix all 10. (1) Change expected phases to `["discovery","scoping","done"]`. (2) Add 20s delay before simulator call. (3) Add `_NULL_STRINGS` set to `_nonempty()`. (4) Add `no_sim_errors` assertion. (5) Add `_has_multi_question` detection + `_retry_single_question` in discovery agent. (6) Add retry with 5s backoff in web search. (7-9) Add `rice_scores_present`, `phase1_within_4_weeks`, `spec_problem_statement_filled` assertions. (10) Suppress ResourceWarning + drain loop.

**Alternatives considered**: Fix only P0 bugs (would leave assertion gaps); refactor eval architecture (scope creep).

**Tradeoffs**: Assertion count grows from 22 to 27 (more to maintain) but catches real quality regressions. Rate-limit delays double eval runtime but prevent crashes on free tier.

**Status**: Accepted

---

## Documentation (Mar 10)

### 2026-03-10: Consolidate design documentation

**Context**: Three docs existed but were outdated and incomplete: `Implementation Summary.md` (flat bullet-point list), `MODEL_ARCHITECTURE.md` (covered model routing but missed eval, orchestrator, prompts), `SYSTEM_DESIGN.md` (had some structure but incomplete on agent internals, eval, and design rationale). None was comprehensive enough for a PM to explain the full system.

**Decision**: Replace all three with two comprehensive documents: (1) `HIGH_LEVEL_DESIGN.md` -- architecture, data flow, agent roles, MoE routing, tech stack, eval framework, 10 design decisions with tradeoffs. (2) `LOW_LEVEL_DESIGN.md` -- every Pydantic schema, config constant, LLM call mechanism, agent decision trees, all 9 prompts, all 5 tools, orchestrator internals, full eval subsystem. Delete the 3 old docs, update README cross-references.

**Alternatives considered**: Update the existing 3 docs in place (fragmented, inconsistent structure); single mega-doc (too long for any one audience).

**Tradeoffs**: Two docs with clear HLD/LLD split serve both "explain it to someone" and "implement it from scratch" audiences. Old doc names are gone (links break, but they were internal-only).

**Status**: Accepted

---

### 2026-03-10: Revamp README and Decision Log

**Context**: README had placeholder repo name (`<REPO_NAME>`), no architecture diagram, no eval results, and a sparse project structure table. Decision Log had only 5 entries ending Feb 23, missing 12+ decisions made since then.

**Decision**: Rewrite README as a world-class repo landing page with architecture mermaid diagram, key design decisions, eval results table, expanded project structure, actual repo URL (Vibe-PM), model routing table, and design doc links. Expand Decision Log to capture every architectural decision chronologically from Feb 22 through Mar 10.

**Alternatives considered**: Incremental updates to existing README (would still miss the architecture diagram and eval results).

**Tradeoffs**: Longer README (some visitors prefer minimal). Accepted: the target audience (PMs, engineers evaluating the project) benefits from comprehensive first impressions.

**Status**: Accepted
