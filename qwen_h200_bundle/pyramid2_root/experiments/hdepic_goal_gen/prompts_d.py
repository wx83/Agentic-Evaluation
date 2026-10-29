"""Method D = A's EgoPlan-style hierarchical system prompt + B's official EgoPlan few-shot exemplars for granularity."""
from prompts_a import SYSTEM as _SYS
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
_EX = None
def exemplar_text():
    global _EX
    if _EX is None:
        ex = json.load(open(f"{HERE}/exemplars_b2.json")); parts = []
        for k, e in enumerate(ex, 1):
            lines = "\n".join(f'  [{s["t0"]:.1f}-{s["t1"]:.1f}s] {s["narration"]}' for s in e["steps"])
            parts.append(f'Example {k} ({e["source"]}, scenario: {e["scenario"]}):\n{lines}\n  => goal: {e["goal"]}')
        _EX = "\n\n".join(parts)
    return _EX
SYSTEM = _SYS + """

You will also be shown examples of goals from the EgoPlan benchmark (official annotations). Use them to calibrate the granularity and wording of secondary subgoals: each example goal is one secondary subgoal in this scheme."""
USER = """EgoPlan-Bench2 examples of the target granularity (official annotations: time in seconds, narration, and the goal they were grouped under):
{EXEMPLARS}

Video ID: {VIDEO_ID}
Existing coarse label for the whole video (hint only, may mix several goals): {LABEL}
Window {WIDX} of this video.

Recently identified goals from earlier windows (may be extended):
{PREV_GOALS}

Context actions from the previous window (already assigned; do NOT include their ids in your output):
{CONTEXT}

Actions to organise in this window (assign EVERY one of these {N} action_ids exactly once to a secondary subgoal or to unassigned_action_ids; an id may appear in two goals only when it clearly serves both):
{ACTIONS}

Return JSON:
{{
  "overall_goal": "...",
  "subgoals": [{{"subgoal_id": "s1", "description": "..."}}],
  "goals": [
    {{"goal_id": "d1", "parent_chain": ["<overall_goal>", "<subgoal description>"], "description": "<short imperative outcome, EgoPlan style>",
      "extends_goal_id": null, "action_ids": ["..."], "outcome_evidence_action_ids": ["..."], "rationale": "<one sentence, no times>"}}
  ],
  "unassigned_action_ids": ["..."]
}}"""
def build_prompt(vid, label, w, prev):
    from common import fmt_action
    pg = "\n".join(f'- {g["goal_id"]}: {g["description"]} (last action ids: {", ".join(g["action_ids"][-3:])})' for g in prev) or "(none)"
    return USER.format(EXEMPLARS=exemplar_text(), VIDEO_ID=vid, LABEL=label or "null", WIDX=w["idx"], PREV_GOALS=pg, CONTEXT="\n".join(fmt_action(a, True) for a in w["context"]) or "(none)",
                       N=len(w["assign"]), ACTIONS="\n".join(fmt_action(a) for a in w["assign"]))
