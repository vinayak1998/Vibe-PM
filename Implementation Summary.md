Implementation summary (simplified pipeline: code orchestrator + checkpoint agents)

1. Project setup
config.py – Groq model names, retry config, discovery/scoping constants (DISCOVERY_MIN_TURNS, DISCOVERY_COMPLETENESS_THRESHOLD, DISCOVERY_MANDATORY_FIELDS; no per-aspect constants)
requirements.txt – chainlit, litellm, pydantic, duckduckgo-search, python-dotenv, pyyaml
.env.example – Template for GROQ_API_KEY

2. State and models
models/schemas.py – DiscoverySummary, Feature (with RICE and phase), CutFeature, ComparableProduct, ImplementationPhase, ScopingOutput (with implementation_phases), ConversationState (discovery_summary_shown, awaiting_scope_agreement, scope_agreed; no discovery_confirmed_aspects or discovery_research_*)

3. LLM and tools
models/llm.py – LiteLLM wrapper with task-based routing (conversation / extraction / classification / spec) and retries
tools/completeness.py – Discovery completeness (score, gaps, is_complete); used by Discovery agent after each turn
tools/extraction.py – JSON extraction for DiscoverySummary and ScopingOutput (including implementation_phases and RICE on features)
tools/intent.py – classify_discovery_review (CONFIRM/REVISE), classify_scoping_intent (AGREE/PUSHBACK/QUESTION)
tools/web_search.py – DuckDuckGo search for comparable products (used by Scoping agent)
tools/templates.py – Phased spec Markdown template (Phase 1/2/3, RICE summary)

4. Prompts
prompts/discovery.py – Discovery SOP (top-1% PM depth), DISCOVERY_ASK_FOR_IDEA_PROMPT, DISCOVERY_SUMMARY_PROMPT
prompts/scoping.py – Scoping agent (opinionated, RICE, phased implementation, argue-back, max 3 rounds)
prompts/spec_writer.py – Spec writer (phased output, no hallucination)
prompts/extraction.py – EXTRACTION_DISCOVERY_PROMPT, EXTRACTION_SCOPING_PROMPT (with implementation_phases, RICE), CLASSIFY_DISCOVERY_REVIEW_PROMPT, CLASSIFY_SCOPING_INTENT_PROMPT

5. Agents
agents/base.py – Base agent with _llm_conversation
agents/discovery.py – Checkpoint-based: extract after each turn, check_completeness; when complete (and min turns) show summary for user confirmation; classify_discovery_review on response; output validation (reject tables/PRDs)
agents/scoping.py – Initial proposal (web search + RICE-scored phased MVP + extraction), then AGREE/PUSHBACK/QUESTION and argue-back
agents/spec_writer.py – Single-pass phased spec from discovery + scoping (phased template, RICE summary)

6. Orchestrator and UI
orchestrator.py – Sequential phase manager (discovery → scoping → spec → done); HANDOFF_MESSAGES at each transition; skip prevention (_user_wants_to_skip); step_callback for UI
app.py – Chainlit: session orchestrator, handle_message, spec download when phase is done

7. Eval
eval/rubric.py – Five dimensions (discovery_depth, conversation_naturalness, scoping_quality, spec_accuracy, argue_back_quality), 1–5 scale
eval/scenarios/*.yaml – Five scenarios (vague_founder, over_scoper, clear_thinker, arguer, pivoter)
eval/runner.py – Loads scenarios, runs Orchestrator.handle_message, returns transcript and state_dict (discovery_summary, scoping_output, spec_length)

8. Docs
SYSTEM_DESIGN.md – HLD/LLD (architecture, agents, state, LLM routing, handoffs, schemas)
DECISION_LOG.md – Chronological decision log (multi-agent, open source, Groq, MoE, simplify pipeline)

To run the app:
Copy .env.example to .env and set GROQ_API_KEY. From project root: pip install -r requirements.txt then chainlit run app.py.

To run evals (needs Groq): python eval/runner.py from project root.
