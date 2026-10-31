# Pyramid v17 design (2026-10-29)

v17 is the event-traversal version of the pyramid examiner. It keeps the four layers and the per-skill
difficulty ladder of v8–v16 and changes **what the Examiner is asked to write a question about**:
instead of letting the ladder pick evidence clusters, L1–L3 walk the planner's expected events in time
order and ask one question per (event, applicable skill).

## 1. Task unit

* **Task** = one official HD-EPIC recipe step (`hdepic_e.official_step`), e.g. `P09_R02_S07`
  "Dredge each chicken-cheese ball into flour, then dip into egg and roll in the breadcrumbs".
* **Sub-goals** = Gemini-written steps inside the task (`hdepic_e.gemini_subgoal`, Method E, 7 for this task).
* **Sub-goal planner** (`sg.py`, Gemini 3.1 Pro, cached in `pyramid_v2/data/sg_cache/`): reads only the goal
  text and the sub-goal texts and writes, for every sub-goal, the *expected events* (what the wearer must do)
  and, per skill, which events that skill applies to. The planner never sees the video.
* **Clips** are cut per sub-goal: L1 = event ± 5 s, L2 = sub-goal window (15 s / 30 s / whole sub-goal),
  L3 = two adjacent sub-goals played back to back (continuous, ≤ 180 s), L4 = everything before the decision point.

## 2. Layers and skills (capability-v3)

| layer | meaning | skills used in this run |
|---|---|---|
| L1 | directly observable facts | object_recognition, object_location_at_time, object_grounding (bbox/IoU), spatial_near, spatial_side |
| L2 | within-event understanding | action_recognition, event_object_role, action_temporal_order, sound_action_binding, object_state_change, sound_movement_binding, sound_anchored_spatial_near/side |
| L3 | cross-event relations / implicit inference between adjacent sub-goals | cross_event_integration, causal_prerequisite_reasoning, hidden_state_inference, spatial_state_integration |
| L4 | goal-conditioned action selection | goal_conditioned_planning (stage-level plan, judged by Gemini) |

Skills listed in `pyramid_v2/data/skill_exclusions.json` (the four contact-rich skills) are never asked.

## 3. Difficulty ladder inside a skill (unchanged from v16)

Each skill has 4 difficulty levels. Levels 1–3 are single choice, level 4 is short answer.
The level also changes the clip: L2 windows are 15 s / 30 s / whole sub-goal / whole sub-goal + short answer;
L3 windows are two sub-goals / previous + current + next / 180 s.
L4 uses the unified ladder in `staircase.PLAN_U`: 1 small single-choice, 2 large single-choice,
3 small open plan, 4 large open plan.

The ladder is a 2-down-1-up staircase starting at level 2: two consecutive correct answers move the skill
one level up, one wrong answer moves it one level down. The **boundary** is the level where the direction
reverses; ceiling = 4.5, floor = 0.5.

## 4. What v17 changes (vs v16)

| | v16 | v17 |
|---|---|---|
| what drives item selection | the ladder picks the next evidence cluster for the skill | the **event loop** walks planner events in time order (≤ 3 events per sub-goal, `events_per_subgoal`); for every event, every applicable skill gets one item |
| difficulty | ladder picks level and cluster | ladder only picks the **level**; the event is given |
| after convergence | stop the skill | keep asking at the boundary level for the remaining events (`verify` phase) |
| history shown to the Solver | ≤ 8 lower-layer items per layer, same sub-goal first | only lower-layer items about the **same event** (`history_select = by_event`, ≤ 3 per layer) |
| L4 | unchanged | unchanged (v16 unified ladder, decision-point clips) |
| coverage of applicable events | 44–81 % | ≈ 100 % |

Contract keys that switch v17 on: `"event_loop": true`, `"events_per_subgoal": 3`,
`"history_select": "by_event"`, `"history_per_layer": 3`, `"sg_mode": true`. Code: `sg.run_layer_events`
(sg.py §8), `staircase.py` (level bookkeeping), `chain.py` (`select == "by_event"` history).

## 5. Arms

* **self**: history = the Solver's own earlier answers at lower layers (`history_mode = self`).
* **goldlive**: history = the Examiner's reference answers (`history_mode = gold`), run as its own staircase.
* L1 has no history, so the two arms only differ from L2 up.

## 6. Scoring (`pyramid_score.py`)

skill score = layer index + (boundary − 0.5) / 4 → a converged skill lands in [L, L+1].
Layer score = mean of its skills; mastery = layer score − L (0–1).
**Pyramid score** = sum of the four masteries (0–4); **height** = number of consecutive layers from L1
with mastery ≥ 0.5. Unconverged skills (events exhausted, examiner failed) are included but flagged.

## 7. Reference results on the bundled task (Gemini 3.1 Pro examiner, Gemini 4 solver, 3 reps per item)

| arm | L1 | L2 | L3 | L4 | pyramid | scored items | converged skills |
|---|---|---|---|---|---|---|---|
| self | 0.58 | 0.62 | 0.69 | 0.75 | 2.65 / 4 | 99 | 8 / 12 |
| goldlive | 0.35 | 0.54 | 0.69 | 0.31 | 1.90 / 4 | 102 | 8 / 12 |

The full per-item logs are in `pyramid_v2/runs/p2_hdepicE_1023t_g4_v17_{self,goldlive}__55/`.
The original Chinese lab notes for this run are in `v17_results_notes_zh.md`.
