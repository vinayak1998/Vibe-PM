# Eval Results — Latest Run

*Generated: 2026-03-09 18:56:02 UTC*  
*Models: conversation=groq/openai/gpt-oss-20b, extraction=groq/llama-3.1-8b-instant, classification=groq/llama-3.1-8b-instant, spec=groq/llama-3.3-70b-versatile*

Columns: assertions pass rate + LLM judge scores (1-5) per dimension + overall.
N/A = dimension not tested in that scenario.

| Scenario | Assertions | discovery | naturalness | scoping | spec | argue back | overall |
| --- | --- | --- | --- | --- | --- | --- | --- |
| vague_founder | 21/23 | 5/5 | 5/5 | 5/5 | 5/5 | N/A | 20/20 |
| over_scoper | 22/23 | 4/5 | 5/5 | 4/5 | 5/5 | N/A | 18/20 |
| clear_thinker | 23/23 | 5/5 | 5/5 | 5/5 | 5/5 | N/A | 20/20 |
| arguer | 22/23 | 4/5 | 4/5 | 4/5 | 4/5 | 5/5 | 21/25 |
| pivoter | 21/23 | 4/5 | 4/5 | 4/5 | 5/5 | N/A | 17/20 |

---

## Score Dimension Reference

| Dimension | Column | What it measures |
|---|---|---|
| discovery_depth | discovery | Right questions asked; vague answers probed; key areas (target user, problem, alternatives, success metric, etc.) covere... |
| conversation_naturalness | naturalness | Human PM feel vs. form feel. One question at a time, references previous answers, warm and conversational. 1=robotic/for... |
| scoping_quality | scoping | Correct P0s; justified cuts; MVP buildable in 2-4 weeks; one core user flow identified; social/dashboards/admin not P0.... |
| spec_accuracy | spec | Spec matches discussion; no hallucinations; TBD where unknown. 1=wrong or hallucinated, 5=accurate and complete. |
| argue_back_quality | argue_back | Evaluates pushback on strength/impact/core-ness; concedes or holds firm with reasoning; graceful after max rounds. 1=ign... |

---

*Full per-scenario reports with detailed reasoning: [eval/reports/](reports/)*
