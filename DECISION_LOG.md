# Decision Log

Chronological log of architectural and product decisions. Updated when changes are reviewed and confirmed.

Format per entry:

- **Context**: Why this came up
- **Decision**: What was decided
- **Alternatives considered**: What else was on the table
- **Tradeoffs**: What we gain/lose
- **Status**: Accepted | Superseded by [reference]

---

### 2026-02-22 (approx.): Multi-agent vs single agent

**Context**: Need to validate whether specialized agents (Discovery, Scoping, Spec Writer) outperform one well-prompted PM agent.

**Decision**: Build with 3 specialized agents and a simple phase manager (orchestrator). Same models; only architecture varies for comparison.

**Alternatives considered**: Single mega-prompt agent handling discovery, scoping, and spec in one flow.

**Tradeoffs**: Gain separation of concerns, clearer state boundaries, and evaluable per-phase behavior. Lose some cross-phase nuance and add routing/orchestration code.

**Status**: Accepted

---

### 2026-02-22 (approx.): Open source models only

**Context**: Project goal is zero vendor lock-in and cost-effective inference.

**Decision**: Use only open source models (e.g. Llama, Mistral) via Groq/Together/LiteLLM. No GPT-4/Claude in the main pipeline.

**Alternatives considered**: Proprietary models for quality; hybrid (e.g. GPT for conversation, OSS for extraction).

**Tradeoffs**: Gain portability and cost control. Accept possible quality/reliability gaps vs top proprietary models.

**Status**: Accepted

---

### 2026-02-22 (approx.): Groq as primary provider

**Context**: Need fast, free-tier-friendly inference for development and demos.

**Decision**: Use Groq as primary provider (LiteLLM). Backup: Together AI, OpenRouter.

**Alternatives considered**: OpenAI, Anthropic, local inference, other OSS hosts.

**Tradeoffs**: Gain speed and free tier. Accept dependency on Groq availability and model set.

**Status**: Accepted

---

### 2026-02-22 (approx.): Task-based model routing (MoE)

**Context**: Different tasks need different cost/quality tradeoffs (conversation vs extraction vs spec).

**Decision**: Route by task type: conversation → reasoning model (e.g. GPT-OSS 20B), spec → 70B, extraction/classification → 8B. Single `llm_call(task_type, messages)` API.

**Alternatives considered**: One model for everything; dynamic router based on content.

**Tradeoffs**: Gain efficiency and quality per task. Lose simplicity of one model.

**Status**: Accepted

---

### 2026-02-23: Simplify pipeline — Code Orchestrator + Checkpoint Agents

**Context**: Discovery agent was generating PRDs/tables instead of conducting an interview; handoffs were invisible; per-aspect confirmation was fragile. Need strict sequential flow, clear handoffs, and simpler logic.

**Decision**: (1) Remove per-aspect state machine from Discovery. Use extraction + `check_completeness()` after each turn; when complete (and min turns), show summary for user confirmation; then transition to scoping. (2) Orchestrator is code-only: explicit handoff messages, skip prevention, no LLM orchestrator. (3) Scoping: add RICE scoring and phased implementation planning; spec writer outputs phased spec for vibe coding tools. (4) Add SYSTEM_DESIGN.md and DECISION_LOG.md; keep them updated with changes.

**Alternatives considered**: LLM orchestrator for flexible routing; hybrid (code router + LLM transition gates); keep per-aspect confirmation with better prompts.

**Tradeoffs**: Gain determinism, debuggability, and clear user-confirmed handoffs. Lose flexibility (e.g. "go back to discovery") and per-aspect granularity in favor of completeness-based checkpoint.

**Status**: Accepted. Implementation completed (code orchestrator, checkpoint discovery, RICE/phased scoping, phased spec, SYSTEM_DESIGN.md, DECISION_LOG.md).
