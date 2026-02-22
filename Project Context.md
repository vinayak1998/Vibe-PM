# PROJECT CONTEXT: AI PM Agent

""" DO NOT CHANGE OR EDIT THIS FILE BY YOURSELF. ALWAYS ASK USER BEFORE TRYING TO EDIT IT """

## What This Is

An open source AI-powered Product Manager agent that sits between a founder's raw idea and code generation tools (like Cursor, Lovable, Emergent, Replit Agent, etc.).

Today's flow: **Business Idea → AI generates code → Ship**
Our flow: **Business Idea → AI PM interrogates, scopes, prioritizes → Refined Spec → Code generation → Ship**

The core insight: the biggest failure mode for non-technical founders using AI builders isn't bad code — it's building the wrong thing really fast. Most AI code-gen tools are obedient engineers. They'll build whatever you ask. They won't push back and ask "should you even build this?" or "what's the actual user problem?" or "have you considered the edge cases?"

This tool is the missing product layer between the idea and the build.

**Built entirely with open source models.** Zero vendor lock-in. Free-tier inference. Accessible to every founder.

One well-prompted PM agent (multi-agent) that handles discovery, scoping, and spec in a single conversation. 

3 specialized agents (Discovery, Scoping, Spec Writer) with proper state handoff, web search for comparable products, and the argue-back negotiation loop. Chainlit UI.

**What changes:** Only the architecture. Same model. Tests whether agent specialization improves quality over a single mega-prompt.


5 test conversations with a scoring rubric. Automated quality measurement across models and prompt versions. Defines what "good" looks like and measures it.


- Automated model selection based on task complexity
- Integration with code-gen tools (Cursor, Lovable) as pre-build plugin
- User research agent that validates ideas with real users
- Multi-PM perspectives (growth PM vs. infra PM give different advice)

---

## Why Open Source Models

- **Zero vendor lock-in** — works regardless of which AI company exists tomorrow
- **Cost optimization** — Groq free tier for development, pennies per conversation in production
- **Demonstrates systems thinking** — choosing the right model for each task, not defaulting to the most expensive one
- **Differentiator** — most AI demos use GPT-4 or Claude. An open source stack shows deeper understanding.

**Provider:** Groq (free tier, fast inference). Backup: Together AI, OpenRouter.
**Key models:** Llama 3 70B (conversation/reasoning), Mistral (extraction/light tasks).

---

## Why This Matters

1. **The problem is real**: Founders using AI builders waste weeks building features nobody needs because there's no product thinking before code generation.
2. **The gap is structural**: Code-gen tools optimize for "build what was asked" not "build what should be built." Nobody is solving the upstream problem.
3. **The timing is right**: AI agents are mature enough to have nuanced, multi-turn conversations that feel like working with a real PM — not filling out a form.

---

## How It Works: 3-Phase Agent Architecture

The system is a multi-agent pipeline with three specialized agents orchestrated by a simple phase manager.

The Core Experience
Think of it as a 3-phase conversation the agent has with the user before any code gets written:
Phase 1: Discovery (the "why")
User says something vague like "I want to build an app for gym trainers to manage clients." The agent doesn't just accept this. It digs in — who are these trainers, how many clients do they manage today, what tools are they currently stitching together, what's broken about that? It's basically doing a user research interview on the founder.
Phase 2: Scoping (the "what")
Based on discovery, the agent proposes a problem statement and a prioritized feature set. It actively pushes back on scope creep — "you mentioned payments, scheduling, AND a social feed. For an MVP, which one is the core loop that proves this works?" It might even reference patterns from similar products to ground the conversation.
Phase 3: Spec Output (the "how")
The agent generates a lightweight but structured spec — user personas, core user flows, MVP feature list with priority tiers, key screens described, edge cases flagged. This becomes the handoff document to any code-gen tool.
Agent Architecture
Here's where it gets interesting from a build perspective:
┌─────────────────────────────────┐
│         Orchestrator Agent       │
│   (manages phase transitions,    │
│    tracks conversation state)    │
└──────────┬──────────────────────┘
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
┌────────┐┌────────┐┌──────────┐
│Discovery││Scoping ││   Spec   │
│ Agent   ││ Agent  ││ Writer   │
└────┬───┘└───┬────┘└────┬─────┘
     │        │          │
     ▼        ▼          ▼
  [Tools]  [Tools]    [Tools]
Orchestrator Agent — The brain. Decides which phase the conversation is in, whether enough info has been gathered to move forward, and when to push back vs. proceed. This is where your PM judgment gets encoded.
Discovery Agent — Has a checklist of things it needs to understand (target user, problem, current alternatives, willingness to pay, etc.). It doesn't ask them all robotically — it weaves them into natural conversation. It knows when it has "enough" to move on.
Scoping Agent — This is the opinionated one. It takes discovery outputs and proposes an MVP scope. It has access to a tool that can look up comparable products (via web search or a curated knowledge base) so it can say "this sounds similar to Calendly's core loop — what's different about your version?" It actively trims scope.
Spec Writer Agent — Takes the structured outputs from discovery + scoping and generates a clean PRD-like document. User stories, prioritized features, key screens, open questions.
Tools Each Agent Needs
Discovery Agent:

Conversation memory (to track what's been asked/answered)
A "completeness checker" — a structured schema of what a good discovery looks like, so it knows what gaps remain

Scoping Agent:

Web search (to find comparable products)
A prioritization framework (maybe ICE or RICE baked in)
Pattern library — common MVP archetypes (marketplace, SaaS dashboard, booking tool, etc.) so it can suggest proven starting shapes

Spec Writer:

Template engine — structured PRD/spec format
Maybe a simple wireframe describer (text-based screen descriptions that a code-gen tool could interpret)

let the user argue back. "No, I really think the social feed is core." And have the agent either concede with reasoning or hold firm with evidence. That back-and-forth is what real PM work looks like — and showing an AI that can do it is genuinely novel.

What you're actually building has two parts:

The brain — agent orchestration, state management, prompts, conversation design (this is where YOUR value is)
The face — a chat UI that anyone can open and use (this should be near-zero effort)

### Phase 1: Discovery Agent (The Interviewer)
- Conducts a PM-style discovery interview with the founder
- Asks clarifying questions ONE at a time, naturally, like a conversation
- Tracks what has been learned via a structured "completeness schema" (target user, core problem, alternatives, success metrics, etc.)
- Probes deeper on vague answers, redirects off-topic tangents
- Ends with a summary confirmation: "Here's what I heard — did I get this right?"
- **Output:** Structured discovery summary (JSON)

### Phase 2: Scoping Agent (The Opinionated PM)
- Takes discovery output and proposes an MVP scope
- Searches for comparable products to ground recommendations
- Explicitly cuts features and explains why
- Identifies the ONE core user flow that proves the idea works
- **Key differentiator:** The "argue-back" loop — when the founder pushes back on cuts, the agent evaluates their argument and either concedes with reasoning or holds firm with evidence. Multi-round negotiation, max 3 rounds, then graceful concession.
- **Output:** Prioritized feature list (P0/P1/P2), cut list with rationale, comparable products, core user flow

### Phase 3: Spec Writer (The Documenter)
- Takes discovery + scoping outputs
- Generates a clean, structured product spec in Markdown
- Includes: problem statement, persona, MVP features, user flow, key screens, open questions, risks
- Non-conversational — single LLM call, template-driven
- **Output:** Downloadable Markdown spec document

### Orchestrator
- Simple sequential phase manager: Discovery → Scoping → Spec Writer
- Manages state flow between agents as plain Python dicts
- Handles phase transitions and user interaction routing
- No frameworks — just function calls and if/else

```
┌─────────────────────────────────┐
│         Orchestrator Agent       │
│   (manages phase transitions,    │
│    tracks conversation state)    │
└──────────┬──────────────────────┘
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
┌────────┐┌────────┐┌──────────┐
│Discovery││Scoping ││  Spec    │
│ Agent   ││ Agent  ││  Writer  │
│(conv.)  ││(conv.) ││(single)  │
└────┬───┘└───┬────┘└────┬─────┘
     │        │          │
     ▼        ▼          ▼
  [Extract] [Search]  [Template]
  [Check]   [Argue]   [Export]
```

---


### Multi-Model Routing Strategy
- **Llama 3 70B** → core conversations requiring deep reasoning (Discovery questions, Scoping decisions, Argue-back evaluation, Spec writing)
- **Mistral** → lighter tasks (JSON extraction from conversations, comparable product analysis)
- All accessed through LiteLLM's unified interface for easy swapping
- Model choice documented with quality comparison data in `research/model_comparison.md`

---

## Key State Objects

### DiscoverySummary
```python
DiscoverySummary = {
    "target_user": str,           # Who specifically is this for?
    "core_problem": str,          # What pain are they solving?
    "current_alternatives": list,  # What do they use today?
    "why_now": str,               # Why build this now?
    "feature_wishlist": list,      # What do they want to build?
    "success_metric": str,        # How will they know it works?
    "revenue_model": str,         # How will it make money?
    "constraints": str            # Budget, timeline, tech limits
}
```

Discovery is "complete" when: score >= 0.75 (6/8 fields filled) AND `target_user` and `core_problem` are filled (mandatory).

### ScopingOutput
```python
ScopingOutput = {
    "mvp_features": list,          # [{name, description, priority: P0/P1/P2}]
    "cut_features": list,          # [{name, reason_cut}]
    "comparable_products": list,   # [{name, url, relevance}]
    "core_user_flow": str,         # The one flow that proves the idea works
    "scope_rationale": str         # Why this scope, in plain language
}
```

---

## Eval Framework (v2.2)

### 5 Test Scenarios
1. **Vague founder** — one-word answers, needs deep probing
2. **Over-scoper** — wants 15 features, needs aggressive cutting
3. **Clear thinker** — well-defined idea, should finish fast
4. **Arguer** — pushes back on every scope cut
5. **Pivoter** — changes their mind mid-conversation

### Scoring Rubric (1-5 each)
- **Discovery depth** — right questions, probing vague answers
- **Conversation naturalness** — human PM feel vs. form feel
- **Scoping quality** — correct P0s, justified cuts
- **Spec accuracy** — matches discussion, no hallucinations
- **Argue-back quality** — evaluates pushback well (v2 only)

### Comparison Matrix
Evals run against: v1 (single agent) vs v2 (multi-agent) vs v2.1 (multi-model routed) — with data.

---

## Design Principles

1. **Conversation, not a form.** The agent should feel like talking to a smart PM friend, not filling out a questionnaire. One question at a time. Reference previous answers. Probe deeper on vague responses.

2. **Opinionated by default, flexible when argued.** The scoping agent cuts aggressively. But if the founder gives a strong reason to include something, the agent should listen, evaluate, and potentially concede. Real PMs negotiate.

3. **Structured state, natural conversation.** Under the hood, everything is tracked as structured data (JSON, dicts). But the user only sees natural conversation. The extraction happens behind the scenes.

4. **Right model for the right task.** Llama 70B for reasoning-heavy conversations. Mistral for extraction and formatting. Don't burn expensive tokens on cheap tasks. Open source throughout.

5. **Graceful degradation.** If an agent can't extract info, it asks again. If the user gives one-word answers, it probes. If the API times out, it retries. Never crash, never lose state.

6. **The spec should be buildable.** The final output isn't a vague strategy doc — it's a spec specific enough that a developer (or an AI code-gen tool) could build from it. Concrete features, concrete flows, concrete screens.

---

## Agent Behavior Guidelines

### Discovery Agent Personality
- Warm, curious, rigorous
- Asks ONE question at a time
- Acknowledges what it heard before moving on
- Probes vague answers: "you said 'everyone' — can you be more specific?"
- Redirects off-topic: "interesting! let's come back to the product..."
- Confirms understanding before exiting: "here's what I heard — did I get this right?"

### Scoping Agent Personality
- Opinionated, direct, evidence-based
- Always cuts more than the founder wants
- Justifies every cut with reasoning
- References comparable products
- Social features, analytics dashboards, and admin panels are NEVER P0
- MVP should be buildable in 2-4 weeks by one developer
- Evaluates pushback on 3 dimensions: strength of argument, impact on scope, core-ness to value prop
- Max 3 negotiation rounds, then graceful concession with risk flagging

### Spec Writer Behavior
- Not conversational — single-pass generation
- Follows template exactly
- Only includes information that was explicitly discussed (no hallucination)
- Marks unknown sections as "TBD — needs further discovery"
- Clear, concise, developer-friendly language

---

## What "Done" Looks Like

A shareable web app where:
1. A user types a vague product idea
2. An AI PM conducts a thorough but natural discovery interview (5-8 questions)
3. The AI proposes an MVP scope, actively cutting features and explaining why
4. The user can argue back, and the AI evaluates their arguments
5. A clean, structured product spec is generated and downloadable as Markdown
6. The whole experience takes 5-10 minutes and feels like talking to a smart PM
7. All powered by open source models — zero vendor lock-in, free to run

---

## Builder Context

- **Builder:** Vinayak — PM with CS background (IIT Delhi), experienced in B2B SaaS, creator commerce, and ML platforms. Building this as a portfolio project to demonstrate product thinking + technical execution for job applications at top tech companies and AI startups.
- **Timeline:** 7 days, ~35-40 hours total
- **Work split:** 65% PM work (research, design, prompts, testing, storytelling) / 35% AI-assisted coding
- **Learning curve:** Zero prior experience with LLM APIs or agent frameworks. Fast learner. Using Cursor/Claude Code as primary dev assistant.
- **Priority:** Agent intelligence > UI polish. A brilliant agent in a simple UI beats a gorgeous frontend with a mediocre agent.
- **Open source commitment:** All models are open source. All code is open source (MIT). Building in public from Day 1.