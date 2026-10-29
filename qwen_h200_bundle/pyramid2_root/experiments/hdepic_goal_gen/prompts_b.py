"""Method B: few-shot grouping with EgoPlan time+narration -> goal exemplars (official EgoPlan annotations, times kept)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SYSTEM = """You group timestamped action narrations from one egocentric kitchen video into task goals with the same granularity and wording as the EgoPlan benchmark examples you are shown.

In EgoPlan, a task goal is a short imperative outcome ("Clean and put away pan and spatula") realised by a plan of roughly 4 to 20 narrated actions, usually consecutive but sometimes interrupted. Reproduce that granularity: not one goal per action, and not one goal for a whole 10-minute phase.

Rules:
- Use only the given narrations. Do not invent ingredients, recipes, intentions or steps.
- Refer to actions only by action_id. Never write times, durations or frame numbers in any output field; the times are shown only so you can read order and gaps.
- Every assignable action_id must appear exactly once in a goal or in unassigned_action_ids (an id may appear in two goals only if it clearly serves both outcomes).
- Interrupted goals: put the resumed actions back into the same goal.
- Actions that support no outcome (idle, phone, aimless walking) go to unassigned_action_ids.
- Some windows list earlier goals still open; if the first actions of this window continue one, output a goal with extends_goal_id set to that id and only the new action_ids.
Return only JSON following the requested schema."""
USER = """EgoPlan examples (official EgoPlan annotations: time ranges in seconds, narrations, and the goal they were grouped under):
{EXEMPLARS}

Now group the HD-EPIC actions below the same way.
Video ID: {VIDEO_ID}
Existing coarse label for the whole video (hint only, may mix several goals): {LABEL}
Window {WIDX} of this video.

Recently identified goals from earlier windows (may be extended):
{PREV_GOALS}

Context actions from the previous window (already assigned; do NOT include their ids in your output):
{CONTEXT}

Actions to group in this window (assign EVERY one of these {N} action_ids):
{ACTIONS}

Return JSON:
{{
  "goals": [
    {{"goal_id": "b1", "description": "<short imperative outcome in EgoPlan style>", "extends_goal_id": null, "action_ids": ["..."], "rationale": "<one sentence, no times>"}}
  ],
  "unassigned_action_ids": ["..."]
}}"""
_EX = None
def exemplar_text():
    global _EX
    if _EX is None:
        ex = json.load(open(f"{HERE}/exemplars.json"))
        parts = []
        for k, e in enumerate(ex, 1):
            lines = "\n".join(f'  [{s["t0"]:.1f}-{s["t1"]:.1f}s] {s["narration"]}' for s in e["steps"])
            parts.append(f'Example {k} ({e["source"]}, video {e["video_id"]}):\n{lines}\n  => goal: {e["goal"]}')
        _EX = "\n\n".join(parts)
    return _EX
def build_prompt(vid, label, w, prev):
    from common import fmt_action
    pg = "\n".join(f'- {g["goal_id"]}: {g["description"]} (last action ids: {", ".join(g["action_ids"][-3:])})' for g in prev) or "(none)"
    return USER.format(EXEMPLARS=exemplar_text(), VIDEO_ID=vid, LABEL=label or "null", WIDX=w["idx"], PREV_GOALS=pg, CONTEXT="\n".join(fmt_action(a, True) for a in w["context"]) or "(none)",
                       N=len(w["assign"]), ACTIONS="\n".join(fmt_action(a) for a in w["assign"]))
