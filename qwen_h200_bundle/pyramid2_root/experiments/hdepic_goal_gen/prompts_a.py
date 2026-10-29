"""Method A: EgoPlan-Bench style hierarchical goal extraction (overall goal -> subgoal -> secondary subgoal), written in our words
from the prose description of EgoPlan-Bench App. A.1 (arXiv 2312.06722). Leaves (secondary subgoals) become candidate goals."""
SYSTEM = """You analyse timestamped action narrations from one egocentric kitchen video and organise them into a task hierarchy, in the way EgoPlan-Bench built task goals from Epic-Kitchens narrations.

Analyse the actions focusing on the sequence and timing of actions: temporal relationships between actions, the conditions before and after each action, the objects interacted with and their state changes, and changes of the functional area of the kitchen (sink, hob, counter, fridge, table).

Then distil the structure in three levels:
1. overall goal: what the whole segment is for (one short phrase);
2. subgoals: the main sub-tasks that make up the overall goal;
3. secondary subgoals: concrete plans a person follows to reach one identifiable outcome, each covering roughly 4 to 20 consecutive or lightly interrupted actions.

Secondary subgoals are the deliverable. Each must:
- describe ONE intended outcome in a short imperative phrase in the style of EgoPlan task goals, e.g. "Clean and put away pan and spatula", "Prepare the hot water and test its temperature", "Rinse various utensils", "Season and stir the vegetables";
- list the action_ids that realise it, in chronological order;
- normally contain 4 to 20 actions; do not create single-action goals, and split a run of more than 20 actions into separate outcomes;
- be based only on the given narrations: do not invent ingredients, recipes, intentions or steps that are not narrated.

Rules on time: you receive official start/end times only so you can read the order and gaps. NEVER write times, durations or frame numbers in any output field. Refer to actions only by action_id. Never invent, merge, rename or drop actions.

Interleaving: a goal may be interrupted by actions of another goal and resumed later; put resumed actions back into the same goal. Actions that support none of the outcomes (idle, phone, walking without purpose) go to unassigned_action_ids. An action that clearly serves two outcomes may be listed under both (at most two).

Continuity: some windows list earlier goals that are still open. If the first actions of this window continue one of them, output a goal with "extends_goal_id" set to that goal's id and only the new action_ids; otherwise leave extends_goal_id null.

Return only JSON following the requested schema."""
USER = """Video ID: {VIDEO_ID}
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
    {{"goal_id": "a1", "parent_chain": ["<overall_goal>", "<subgoal description>"], "description": "<short imperative outcome>",
      "extends_goal_id": null, "action_ids": ["..."], "outcome_evidence_action_ids": ["..."], "rationale": "<one sentence, no times>"}}
  ],
  "unassigned_action_ids": ["..."]
}}"""
def build_prompt(vid, label, w, prev):
    from common import fmt_action
    pg = "\n".join(f'- {g["goal_id"]}: {g["description"]} (last action ids: {", ".join(g["action_ids"][-3:])})' for g in prev) or "(none)"
    return USER.format(VIDEO_ID=vid, LABEL=label or "null", WIDX=w["idx"], PREV_GOALS=pg, CONTEXT="\n".join(fmt_action(a, True) for a in w["context"]) or "(none)",
                       N=len(w["assign"]), ACTIONS="\n".join(fmt_action(a) for a in w["assign"]))
