"""Method C: few-shot with TASK-level EgoPlan exemplars (complete outcomes), official times kept."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SYSTEM = """You group timestamped action narrations from one egocentric kitchen video into goals at the SAME level of abstraction as the EgoPlan examples you are shown.

Every example goal is a complete outcome a person sets out to achieve: a dish or component that gets finished ("prepare a bowl of cereal", "cook vegetables", "serve rice"), or a self-contained chore ("clean up the kitchen"). Name goals that way: a short imperative phrase for a complete outcome, never a single step ("open the fridge") and never a vague phase ("cooking").

Important difference in density: the example narrations are coarse (one line per 3-6 seconds). The HD-EPIC narrations you receive are much finer (several lines per step, with hands described). So one goal here will usually contain many more lines than in the examples, often 15-80, sometimes more. Do not split a complete outcome into pieces just to keep goals short, and do not merge two different outcomes into one goal.

Rules:
- Use only the given narrations; do not invent ingredients, recipes or intentions.
- Refer to actions only by action_id. Never write times, durations or frame numbers in any output field; times are shown only so you can read order and gaps.
- Every assignable action_id must appear exactly once in a goal or in unassigned_action_ids (an id may be in two goals only if it clearly serves both outcomes).
- Goals are often interleaved: a person starts one dish, works on another, and comes back. Put resumed actions back into the same goal regardless of the gap.
- Actions that support no outcome (idle, phone, aimless walking) go to unassigned_action_ids.
- Some windows list goals from earlier windows that may still be open; if actions in this window continue one, output a goal with extends_goal_id set to that id and only the new action_ids.
Return only JSON following the requested schema."""
USER = """EgoPlan examples of complete-outcome goals (official EgoPlan annotations: time in seconds, narration, and the goal):
{EXEMPLARS}

Now group the HD-EPIC actions below into goals at the same level of abstraction.
Video ID: {VIDEO_ID}
Existing coarse label for the whole video (hint only, may mix several goals): {LABEL}
Window {WIDX} of this video.

Goals identified in earlier windows (may be extended):
{PREV_GOALS}

Context actions from the previous window (already assigned; do NOT include their ids in your output):
{CONTEXT}

Actions to group in this window (assign EVERY one of these {N} action_ids):
{ACTIONS}

Return JSON:
{{
  "goals": [
    {{"goal_id": "c1", "description": "<complete outcome, EgoPlan style>", "extends_goal_id": null, "action_ids": ["..."], "rationale": "<one sentence, no times>"}}
  ],
  "unassigned_action_ids": ["..."]
}}"""
_EX = None
def exemplar_text():
    global _EX
    if _EX is None:
        ex = json.load(open(f"{HERE}/exemplars_task.json")); parts = []
        for k, e in enumerate(ex, 1):
            lines = "\n".join(f'  [{s["t0"]:.1f}-{s["t1"]:.1f}s] {s["narration"]}' for s in e["steps"])
            parts.append(f'Example {k} ({e["source"]}, video {e["video_id"]}):\n{lines}\n  => goal: {e["goal"]}')
        _EX = "\n\n".join(parts)
    return _EX
def build_prompt(vid, label, w, prev):
    from common import fmt_action
    pg = "\n".join(f'- {g["goal_id"]}: {g["description"]} ({len(g["action_ids"])} actions so far; last ids: {", ".join(g["action_ids"][-3:])})' for g in prev) or "(none)"
    return USER.format(EXEMPLARS=exemplar_text(), VIDEO_ID=vid, LABEL=label or "null", WIDX=w["idx"], PREV_GOALS=pg, CONTEXT="\n".join(fmt_action(a, True) for a in w["context"]) or "(none)",
                       N=len(w["assign"]), ACTIONS="\n".join(fmt_action(a) for a in w["assign"]))
