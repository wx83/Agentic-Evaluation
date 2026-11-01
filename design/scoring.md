# Scoring: from one item to the pyramid score

**Item verdict.** Single-choice / multi-select items are rule-graded against the reference letters (multi-select must match exactly).
Short answers are matched against the reference and its accepted alternatives, otherwise judged by Gemini 3.1 Pro against the
reference and rubric (`grade.py`). Bounding boxes are correct at IoU ≥ `bbox_iou_min` (default 0.5). Plan items are judged on stage
coverage, order and contradictions; all three must pass. Gemini 4 answers each item 3 times (`solver_reps`), the majority verdict counts;
Qwen answers once.

**Invalid items are disregarded.** An item that fails the Examiner's output validation (`item_invalid`) or for which the Examiner asks for
evidence verification (`evidence_unresolved`) is neither scored nor used to move the tier. `stair_invalid_limit` (3) consecutive invalid
items end the skill with `examiner_failed`.

**Staircase per skill** (`staircase.py`). 4 tiers. Start at tier 2 (`stair_start_level`), or at the previous task's boundary when
`stair_start_from` names an earlier run. Correct → one tier up; wrong → one tier down (2-down-1-up: two consecutive correct answers are
needed to move up). Stop after 2 reversals, at the ceiling (correct at tier 4 twice), at the floor (wrong at tier 1 twice), when the tier
has no questions left (`exhausted_*`), or after `stair_budget` (12) items. In v17 the skill keeps answering the remaining events at the
boundary tier after it converged; `stair_fixed_level_skills` (v18) pins a skill to one tier and never stops it.

**Boundary.** Mean tier of the reversal points; ceiling = 4.5, floor = 0.5, exhausted = current tier ± 0.5 (flagged `unconverged`).

**Skill score = layer + (boundary − 0.5) / 4**, in [layer, layer + 1]. **Layer score** = mean of its skill scores (skills listed in
`data/skill_exclusions.json` are not counted). **Mastery = layer score − layer index**, in [0, 1]. **Pyramid = Σ mastery over L1–L4**,
in [0, 4]. **Height** = number of consecutive layers from L1 with mastery ≥ 0.5.

**Pass rate** = share of scored items answered correctly per layer; reported separately, not part of the score.
**Blind baseline** (`history_mode: none`, `solver_input_spec.modalities: []`): the same items answered without the clip and without history;
items it answers correctly are "guessable". `new_layers.py` recomputes pass rates and a tier-averaged proxy score after removing them.

All of this is implemented in `pyramid_score.py` (`score_run`, writes `score.json`), `compare_budget.py` and `new_layers.py`.
