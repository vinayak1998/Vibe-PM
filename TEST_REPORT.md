# AI PM Chainlit App - Test Report

**Test Date:** March 12, 2026  
**Tester:** Automated Test Script  
**App URL:** http://localhost:8000  
**Testing Method:** Programmatic API testing (browser tools not available)

---

## Executive Summary

⚠️ **Test Status:** PARTIALLY COMPLETED - Rate limited during Discovery phase

The test attempted to validate the full 3-phase flow (Discovery → Scoping → Spec Writing) but encountered Groq API rate limits after 8 discovery turns. However, significant progress was made and key insights were gathered.

---

## Test Methodology

### Original Plan
- Use browser automation tools (cursor-ide-browser MCP) to interact with the Chainlit UI at http://localhost:8000
- Simulate user inputs through the chat interface
- Progress through all 3 phases with comprehensive answers

### Actual Implementation
- Browser MCP tools were not available in the test environment
- Created a programmatic test script (`test_manual_flow.py`) that directly interacts with the Orchestrator
- Provided comprehensive, multi-area answers to speed through discovery
- Implemented question-pattern matching to provide relevant responses

---

## What Was Tested

### ✓ Phase 1: Discovery (Partial)

**Turns Completed:** 8 out of estimated 10-15  
**Status:** In progress when rate limited

#### Test Inputs Provided:
1. **Initial Idea:** "DogMeet - a social app for urban dog owners to find dog-friendly parks, schedule playdates, and track their dog's health"

2. **Comprehensive User Info:** Target user persona (urban millennials 25-40), typical day scenario (Sarah with golden retriever Max), daily pain points (30+ min searching, Facebook group coordination, spreadsheet tracking)

3. **Problem Details:** No dog-specific filters on maps, clunky playdate coordination, manual health tracking leading to stressed owners and under-exercised dogs

4. **Multiple Attempts:** The agent asked variations of the same questions multiple times

#### Observations:

**✓ What Worked:**
- Agent correctly identified it was in discovery phase
- Agent asked relevant follow-up questions about:
  - Target user and typical day
  - What's changed recently (why now)
  - Current pain points
- Agent began summarizing information after ~5 turns (showing it recognized completeness)
- Information extraction appeared to be working (agent referenced previous answers in summaries)

**✗ Issues Encountered:**
- **Repetitive Questions:** Agent asked similar questions multiple times even after receiving comprehensive answers
  - Asked "walk me through a typical day" in turn 2
  - Asked "what's changed recently" in turns 3 and 4
  - Generated multiple summaries (turns 5, 6, 7, 8) instead of moving forward
  
- **Not Moving to Scoping:** Despite providing all required information:
  - target_user ✓
  - core_problem ✓
  - current_alternatives ✓
  - why_now ✓
  - feature_wishlist ✓
  - success_metric ✓
  - revenue_model ✓
  - constraints ✓
  
  The agent continued asking questions rather than showing a final summary and requesting confirmation.

- **Rate Limiting:** Hit Groq API limits (8000 TPM) during turn 8
  - Model: `openai/gpt-oss-20b`
  - Error: "Rate limit reached... Please try again in 10.3725s"
  - This prevented completion of the discovery phase

### ✗ Phase 2: Scoping

**Status:** Not reached due to discovery phase incomplete

**Planned Test:**
- Wait for scoping agent to perform web research
- Review RICE-scored feature proposals
- Agree with reasonable MVP scope prioritization
- Respond: "I agree with prioritizing the park finder and playdate scheduling for MVP. Health tracking can come in phase 2."

### ✗ Phase 3: Spec Writing

**Status:** Not reached

**Planned Test:**
- Wait for spec generation
- Verify markdown spec is generated
- Confirm download link is provided
- Review spec content for completeness

---

## Technical Issues

### 1. Browser Tools Not Available
**Severity:** High  
**Impact:** Could not test the actual UI as requested

**Details:**
- System instructions indicated browser MCP tools should be available
- `CallMcpTool` function not present in toolset
- Browser tools exist in `/Users/vinayakrastogi/.cursor/projects/.../mcps/cursor-ide-browser/`
- Worked around by creating programmatic test

**Recommendation:** Configure MCP browser tools properly or clarify test methodology

### 2. Rate Limiting
**Severity:** High  
**Impact:** Prevented test completion

**Details:**
- Groq free tier: 8000 tokens per minute (TPM)
- Discovery phase alone used 7131 tokens
- Each comprehensive answer consumed significant tokens
- Retry logic attempted 3 times per call, compounding the issue

**Solutions:**
1. Add delays between turns (eval/runner.py uses 20s `TURN_DELAY_SECONDS`)
2. Upgrade to Groq Dev Tier
3. Use more concise answers during testing
4. Switch to a different model with higher limits

### 3. Discovery Agent Loop
**Severity:** Medium  
**Impact:** Inefficient, uses extra tokens, may confuse users

**Details:**
- Agent generated multiple summaries without asking for user confirmation
- Questions repeated even when info was already provided
- May be related to:
  - Extraction logic not catching all fields
  - Completeness check threshold (0.75) not being met
  - Minimum turns requirement (4) extending the conversation

**Recommendation:** 
- Review `tools/extraction.py` to ensure comprehensive info is properly extracted
- Check `tools/completeness.py` scoring logic
- Consider lowering minimum turns or threshold for testing
- Add logging to show which fields are missing/incomplete

---

## App Architecture Review

Based on code analysis:

### Strengths ✓
- **Clean separation:** Discovery → Scoping → Spec Writing phases
- **Extraction pipeline:** Structured data extraction from conversations
- **Completeness checking:** Ensures all required info is gathered
- **Retry logic:** LLM calls have exponential backoff
- **Eval framework:** Comprehensive testing infrastructure exists
  - 5 test scenarios (vague_founder, over_scoper, clear_thinker, arguer, pivoter)
  - Simulated user with different message policies
  - Assertions + optional LLM judge scoring
  - See `eval/runner.py`

### Improvement Opportunities
1. **Add rate limit handling:** Sleep between turns in main app (not just eval)
2. **Better extraction feedback:** Show user which fields are still needed
3. **Prevent summary loops:** Only show summary once, then wait for confirmation
4. **Progress indicator:** Show user how many fields have been covered (e.g., "3/8 areas discussed")

---

## Comparison: Browser Testing vs Programmatic Testing

| Aspect | Browser Testing | Programmatic Testing |
|--------|-----------------|---------------------|
| **Realism** | ✓ Tests actual UI | ✗ Bypasses UI layer |
| **Chainlit Integration** | ✓ Tests full stack | ✗ Tests backend only |
| **Speed** | ✗ Slower | ✓ Faster |
| **Debugging** | ✗ Harder to debug | ✓ Direct stack traces |
| **Screenshots** | ✓ Visual documentation | ✗ No visual evidence |
| **Rate Limits** | Same API limits | Same API limits |
| **Availability** | ✗ Requires browser tools | ✓ Always available |

**Recommendation:** Use both approaches:
- **Programmatic** for rapid iteration and backend logic validation
- **Browser** for UI/UX testing and user flow validation

---

## Next Steps

### Immediate (to complete this test):
1. ✓ Wait 10+ seconds for rate limit reset
2. ✓ Modify test to include delays (20s between turns)
3. ✓ Re-run with rate limit handling
4. ✓ Complete discovery → scoping → spec flow

### Short-term improvements:
1. Fix discovery agent summary loop
2. Add progress indicators to UI
3. Configure browser MCP tools for UI testing
4. Run existing eval suite: `python eval/runner.py`

### Long-term:
1. Upgrade Groq tier or switch to OpenAI for higher limits
2. Add caching to reduce redundant LLM calls
3. Create Cypress/Playwright tests for UI
4. Add telemetry to track phase transition success rates

---

## Recommended Test Script

For manual browser testing (once browser tools are available):

```python
# Phase 1: Discovery - Answer all 8 areas at once to speed through
initial_comprehensive_answer = """
DogMeet - urban dog owners social app.

Target users: Urban millennials 25-40, apartment dwellers, full-time remote/hybrid workers, tech-savvy.

Core problem: 30+ min/day searching Google Maps for dog parks (no filters), messy Facebook group playdate coordination, manual spreadsheet health tracking. Result: lonely dogs, stressed owners.

Alternatives: Google Maps (no dog filters), Facebook groups (clunky), BarkHappy app (US-only, unmaintained).

Why now: 30% surge in pandemic dog ownership, hybrid work = flexible schedules, FitBark/GPS wearables mainstream.

Features: Park finder with reviews, playdate scheduler with chat, health tracker with vet reminders, dog profiles, social feed.

Success metrics: 10K MAU in 6 months, 5 playdates/user/month, 60% retention at 90 days.

Revenue: Freemium ($5/mo premium for unlimited playdates, health analytics, telehealth) + local ads.

Constraints: 3-month timeline, 2-person team, $10K budget, iOS first, pet data privacy compliance.
"""

# Phase 2: Scoping - Agree with reasonable MVP
scoping_response = "I agree with prioritizing park finder and playdate scheduling for MVP. Health tracking phase 2."

# Phase 3: Spec - Just wait for generation
# No input needed, spec auto-generates
```

---

## Conclusion

The AI PM app shows **strong foundational architecture** with clear phase separation and good extraction logic. However, the test could not be completed due to:

1. **Browser tools not being available** (workaround: programmatic testing)
2. **Groq API rate limits** (solution: add delays or upgrade tier)
3. **Discovery agent not progressing to scoping** (potential bug in completeness logic)

**Overall Assessment:** ⚠️ **NEEDS FIXES BEFORE PRODUCTION**

The discovery phase works but has efficiency issues (repetitive questions, summary loops). Once rate limits are addressed and the discovery→scoping transition is fixed, the app should function as designed.

**Confidence in Assessment:** Medium (75%)  
*Reason:* Could not test scoping or spec phases; discovery observations based on partial run.

---

## Test Artifacts

- **Test Script:** `/Users/vinayakrastogi/Desktop/Agents/PM/test_manual_flow.py`
- **Terminal Output:** See above (8 turns of discovery conversation)
- **Partial Transcript:** Available in test output
- **Screenshots:** N/A (browser tools not available)

---

## Appendix: Existing Eval Framework

The project already has a comprehensive eval system at `eval/runner.py`:

```bash
# Run assertions only (fast, free)
python eval/runner.py

# Run full eval with LLM judge
python eval/runner.py --judge
```

**Scenarios:**
1. `vague_founder` - Minimal message policy, tests extraction
2. `over_scoper` - Tests scoping negotiation
3. `clear_thinker` - Expansive policy, ideal case
4. `arguer` - Pushback during scoping
5. `pivoter` - Changes mind mid-conversation

**Recommendation:** Run this eval suite once rate limits are resolved to get comprehensive coverage.

---

**Report Generated:** March 12, 2026  
**Test Duration:** ~18 seconds (before rate limit)  
**Turns Completed:** 8 / ~30 expected
