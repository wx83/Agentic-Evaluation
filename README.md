# Agentic Evaluation — pyramid2 on HD-EPIC Method E · branch `gemini-solver`

Adaptive, four-layer ("pyramid") evaluation of a video-audio model on first-person cooking video.
An **Examiner** (Gemini 3.1 Pro) writes questions from verified annotations, a **Solver** (the model under test)
answers them from a clip, a 2-down-1-up **staircase** per skill finds the hardest difficulty tier the Solver still passes,
and the per-layer results are summarised as a pyramid score.

* **This branch:** the Solver is **Gemini 4** (`gemini-4-argon`). Examiner / sub-goal planner / judge are Gemini 3.1 Pro.
* **Branch `qwen-solver`:** same code; the Solver is **Qwen3-Omni-30B-A3B-Instruct** served locally; it also contains the runs
  in which Qwen was the Examiner. See its README.
* **Branch `main`:** index of the two branches.

Everything you need to re-run any version documented below is in this branch: code, prompts, contracts (= all hyper-parameters),
sub-goal planner caches, reference runs, and a one-video data bundle (task 55). Other tasks need the full evidence store
(`setup_full_data.sh`, ~2.8 GB from a public Hugging Face dataset).

If you are reading this with an AI coding assistant: §2 (install), §3 (keys), §4 (run) can be followed verbatim.

---

## 1. What is evaluated

**Task** = one official HD-EPIC recipe step (`goal`, e.g. "Dredge each chicken-cheese ball into flour, then dip into egg and roll
in the breadcrumbs"), with its official sub-steps (**sub-goals**). A sub-goal planner (Gemini 3.1 Pro, cached in
`pyramid_v2/data/sg_cache/`) reads only the goal + sub-goal texts and lists the events that must happen; the program aligns
those events to the human annotations (narrations, object movements, sound events, 3D spatial relations) to get timestamps.
No model ever generates a timestamp.

**Layers and skills** (v16 onward; one line each, full definitions in `design/levels_skills_tiers_zh.md`):

| layer | unit | clip | skills |
|---|---|---|---|
| L1 perception | one moment of one event | event ± 5 s | object_recognition, object_location_at_time, object_grounding (bbox), spatial_near, spatial_side |
| L2 understanding | one event inside one sub-goal | 15 s / 30 s / whole sub-goal | action_recognition, event_object_role, action_temporal_order, object_state_change, sound_action_binding, sound_movement_binding, sound_anchored_spatial_near / _side |
| L3 inference | relation between an event of sub-goal k and one of sub-goal k−1 | both sub-goals … 180 s, one continuous clip | cross_event_integration, causal_prerequisite_reasoning, hidden_state_inference, spatial_state_integration |
| L4 planning | decision point = start of a sub-goal | previous sub-goal (v18: last 10 s), cutoff = decision point; goal shown | goal_conditioned_planning |

**Difficulty tiers** (4 per skill; tiers 1–3 single choice, tier 4 short answer): L1 = quartile of a perceptual quantity
(distractor count / spatial margin / box area); L2 = clip length; L3 = clip extent (two sub-goals → ±neighbours → 180 s);
L4 = question type × remaining steps (official options / fresh distractors / plan with 1–2 stages left / plan with 3+ stages left).

**History arms.** Lower-layer items and answers are shown to the Solver when it answers an upper-layer item:
`self` = its own earlier answers, `goldlive` = the reference answers while it walks its own staircase,
`gold` = replay of the self items with reference answers (the "corrected" arm), `none`/`blind` = no history and no clip
(language-prior baseline). Items the blind arm answers correctly are "guessable".

**Scores** (`design/scoring.md`): boundary tier per skill → skill score = layer + (boundary − 0.5)/4 → layer score = mean
→ mastery = layer score − layer index (0–1) → pyramid = Σ mastery (0–4), height = consecutive layers with mastery ≥ 0.5.
Pass rate per layer is reported separately.

## 2. Install

```bash
git clone -b gemini-solver https://github.com/wx83/Agentic-Evaluation.git && cd Agentic-Evaluation
python3 -m venv .venv && source .venv/bin/activate          # Python ≥ 3.10
pip install -r requirements.txt                              # google-genai, numpy, requests, huggingface_hub
ffmpeg -version && ffprobe -version                          # must be on PATH
```

Offline smoke test (no key, ~10 s, mock Examiner + Solver through the whole L1 state machine):

```bash
cd code/bench/pyramid2
python3 - <<'PY'
import json; c=json.load(open("../../../pyramid_v2/contracts/p2_hdepicE_1023t_g4_v17_self__55.json"))
c["run_id"]="p2_mock_L1"; json.dump(c,open("../../../pyramid_v2/contracts/p2_mock_L1.json","w"),indent=1)
PY
GEMINI_BACKEND=google python3 cli.py run --contract ../../../pyramid_v2/contracts/p2_mock_L1.json --levels L1 --mock "W,W,C,C,W,C"
tail -2 ../../../pyramid_v2/runs/p2_mock_L1/run.log        # "L1: EVENT_LOOP_COMPLETE ..." then "run finished"
```

## 3. Keys and model names

`GEMINI_BACKEND=google` (default in the scripts): Google AI Studio, key in `GEMINI_API_KEY` or `.secrets/gemini_api_key`;
the `gcp/google/` prefix in the contracts is stripped. `GEMINI_BACKEND=nv`: NVIDIA `inference-api.nvidia.com` gateway
(what every reference run used), key in `NVIDIA_API_KEY` or `.secrets/nvidia_key`, names used verbatim.
Roles are only set in the contract: `examiner_model`, `scope_model` (planner), `judge_model`, `solver_model`
(`solver_thinking`, `solver_reps` = 3 for Gemini). Connectivity check:

```bash
cd code/bench/pyramid2 && GEMINI_BACKEND=google python3 cli.py preflight --contract ../../../pyramid_v2/contracts/p2_hdepicE_1023t_g4_v16_self__55.json
```

## 4. Run

```bash
./run_task.sh <prefix> <task> <arm> [<arm> ...]
#   prefix: g4_v16 | g4_v16qa | g4_v17 | g4_v18
#   task:   55 (bundled) or any task listed in §6 after ./setup_full_data.sh
#   arms:   self goldlive            full L1-L4 runs (resumable: re-run with the same run_id continues from L*/state.json)
#           gold                     corrected arm = replay of the self run with reference-answer history (REPLAY_LEVELS="L3 L4" to limit)
#           blindnone | blindgl      blind baselines (no clip, no history) of the self / goldlive run
./run_task.sh g4_v16 55 self goldlive blindnone blindgl     # ≈ 2 h per full arm on the gateway, blind replays ≈ 10 min
./run_task.sh g4_v18 55 self gold
```

Contracts are `pyramid_v2/contracts/p2_hdepicE_1023t_<prefix>_<arm>__<task>.json`; runs land in `pyramid_v2/runs/<run_id>/`
(`L*/history.jsonl` one line per item with question, options, reference, solver answer, verdict, media window, history used;
`summary.json` staircase traces; `score.json`; `report.md`; `contexts/` the exact JSON the Examiner saw; `usage.jsonl` tokens).
Reference runs of every version are included (without `contexts/`, except the two v17 task-55 runs).

Other tasks: `./setup_full_data.sh [--with-videos]` downloads the evidence store and the pre-cut clips of all 49 videos
(public dataset `WitneyWW/pyramid2-qwen-data-1028`), merges this repo's contracts/runs/caches into it and prints the
`P2_ROOT=…` export to use. Source videos (11.7 GB) are only needed for clip windows that were never cut before.

Analysis: `pyramid_score.py <run_dir>` (scores), `compare_budget.py <runA> <runB>` (per-skill boundary comparison),
`new_layers.py` (re-scores all v16/v17 runs under the dependency-based skill grouping of §7, subtracting guessable items),
`merge_runs.py` (merge per-task runs of one family).

## 5. Versions (what changed, contract keys, results)

All versions share the prompts in `prompts/1028_prompts_hdepic_e_v16.md` (`## N.` sections: shared Examiner system prompt,
L1–L4 prompts, task-context addendum, sub-goal planner) and the code in `code/bench/pyramid2/`. The version is a set of
contract keys; `notes` inside each contract carries the decision history (Chinese).

### v16 — sub-goal structure (2026-10-28) · `g4_v16_{self,goldlive,gold,blindnone,blindgl}__<task>` · 10 tasks
* `sg_mode: true`: clips are cut per sub-goal; L1 tiers by perceptual-quantity quartile, L2 = 15 s / 30 s / whole sub-goal / whole sub-goal short answer,
  L3 = relations between adjacent sub-goals only, one continuous clip (pair / ±1 sub-goal / 180 s / 180 s short answer); order and multi-select items removed.
* Staircase per skill from tier 2, 2-down-1-up, no verification items, budget 12; history grouped by sub-goal (≤ 6 per group, ≤ 2 per layer).
* Tasks 05 07 13 16 24 29 39 44 54 55 (12 participants' recipes). Scores (mastery L1/L2/L3/L4, pyramid): **self mean 2.31 (sd 0.25)**,
  per-layer 0.41 / 0.65 / 0.69 / 0.56; **goldlive mean 2.29 (sd 0.28)**, 0.44 / 0.65 / 0.70 / 0.51. goldlive − self per task:
  −0.36 +0.47 −0.08 +0.16 +0.27 −0.31 −0.17 +0.03 +0.09 −0.25 → history source makes no difference beyond noise.
* Blind baseline (10 tasks, self items): share of items answered correctly without the clip = L1 44 %, L2 57 %, L3 67 %, L4 25 %;
  pass rate with clip → after removing guessable items: L1 70 → 51 %, L2 83 → 71 %, L3 90 → 71 %, L4 81 → 81 %.

### v16qa — history without options + bbox IoU 0.3 (2026-10-30) · `g4_v16qa_*__13` (also contracts for 55/39/05, not run)
* `history_render: "qa"` (lower-layer history shows question + answer text, no option list), `bbox_iou_min: 0.3` (default 0.5).
* Task 13: self 2.27 / goldlive 2.41 (v16: 2.43 / 2.59). bbox items: 1/4 → 2/5 correct; the two arms still differ within noise.

### v17 — event traversal (2026-10-29) · `g4_v17_{self,goldlive,blindnone,blindgl}__{55,39,05}`
* `event_loop: true`, `events_per_subgoal: 3`, `history_select: by_event`, `history_per_layer: 3`: L1–L3 walk every planner event in time order and ask
  every applicable skill; the staircase only moves the tier (and keeps asking at the boundary after convergence). L4 unchanged.
* Coverage of applicable events per skill 44–81 % (v16) → ≈ 100 %; items +0–50 %. Scores self 2.65 / 2.35 / 1.86, goldlive 1.90 / 2.40 / 1.93
  (v16 on the same tasks: 2.22 / 2.07 / 1.96 and 1.85 / 2.54 / 2.23). Blind: guessable L1 41 %, L2 57 %, L3 67 %, L4 36 %.

### v18 — correction experiment (2026-11-01) · `g4_v18_{self,gold}__{55,13}` · **not yet run with Gemini**
* Designed to test "does correcting L1–L3 improve L4": `l4_window_sec: 10` (L4 clip = last 10 s before the decision point, so earlier facts can only come
  from history), `history_render: "facts"` (lower-layer Q/A rewritten into declarative statements by Gemini 3.1 Pro, cached in `data/fact_cache.jsonl`),
  `history_cap / per_layer / per_subgoal: 999` + `history_select: by_subgoal` (everything is passed, same selection in both arms),
  `stair_fixed_level_skills: {goal_conditioned_planning: 1}` (L4 asks every decision point at tier 1 instead of stopping at the floor).
* Arms: `self` (own answers as facts) vs `gold` = corrected (reference answers), replay of L3 L4. The Qwen-solver run of this design is on the other branch.

Earlier versions (v5–v15: task-scope examiner, L3 extension skills, verification items, v14 budget variant, v15 first sub-goal version)
are summarised in `design/experiment_notes_zh.md` and `code/bench/pyramid2/README_original_zh.md`; their contracts are not in this branch.

## 6. Tasks

| task | video | official step | step text (abridged) |
|---|---|---|---|
| 55 (bundled) | P09-20240622-154652 | P09_R02_S07 | Dredge each chicken-cheese ball into flour, dip into egg, roll in breadcrumbs |
| 05 | P04-20240415-181212 | P04_R06_S06 | Add 300 ml water and lemon juice, then the drained basmati rice; fry 2–3 min |
| 07 | P06-20240510-104642 | P06_R03_S01 | Chop the onion (half small, half large), chop the tomatoes and grind them |
| 13 | P01-20240203-132119 | P01_R05_S02 | Crumble up the biscuits and combine with the mixture |
| 16 | P01-20240203-184214 | P01_R08_S01 | Mix all ingredients except the chicken; pour into a container, add the chicken thighs |
| 24 | P02-20240211-175138 | P02_R10_S01 | Preheat the oven, line a roasting tray, remove the mushroom stalks |
| 29 | P04-20240413-142619 | P04_R01_S04 | Build the wraps: lettuce, tomatoes, onion, spicy chicken, hot sauce, then wrap |
| 39 | P07-20240529-131737 | P07_R02_S02 | Rinse the chickpeas, towel-dry them, remove loose skins |
| 44 | P07-20240531-201703 | P07_R07_S03 | Pulse all the dressing ingredients in a food processor until mostly smooth |
| 54 | P09-20240621-153208 | P09_R03_S01 | Add the hibiscus flowers and chopped ginger into a pot and fill with water |

The bundled `pyramid_v2/data` holds the 1 026 verified records of task 55 and `video/P09-20240622-154652.mp4` (first 240 s).
All other tasks need `setup_full_data.sh`.

## 7. Findings so far (Gemini 4 solver)

* Pyramid ≈ 2.3 / 4, stable across tasks and versions (sd 0.25–0.3); version-to-version and self-vs-goldlive differences are inside that noise.
* Layer pass rates rise with the layer (70 / 83 / 90 / 81 %) and tier pass rates rise with the tier — neither the layers nor the tiers are
  calibrated as difficulty. Two thirds of L3 items and over half of L2 items are answerable without the video (blind baseline); after removing
  them L1–L3 sit at 51 / 71 / 71 %.
* Grouping skills by information dependency (L1 object_recognition + object_location_at_time; L2 action / role / state-change / sound binding;
  L3 cross-event / causal / hidden-state / temporal order; L4 planning; the five spatial skills as a separate track) gives mastery
  0.64 / 0.76 / 0.66 / 0.56 and spatial 0.20 (`new_layers.py`, `design/experiment_notes_zh.md` §11-01).
* Giving the Solver the reference lower-layer answers does not change L4 (≈ 230 gold-replay L4 items: 11 fixed, 9 broken); v18 is the
  redesign that makes the dependency testable.

## 8. Layout

```
run_task.sh / setup_full_data.sh / run_v17_task55.sh     entry points (§4)
requirements.txt, .secrets/README.md
prompts/1028_prompts_hdepic_e_v16.md                     the prompts (v15–v18); 1027_prompts_hdepic_e_v13.md (used by the Qwen-examiner runs)
design/v17_design.md                                     v17 mechanics (English)
design/scoring.md                                        how item → skill → layer → pyramid scores are computed (English)
design/levels_skills_tiers_zh.md                         every layer / skill / tier definition (Chinese, 2026-10-31)
design/experiment_notes_zh.md                            lab notes with all result tables, v15 → v18 (Chinese)
code/bench/pyramid2/                                     the examiner (cli.py, controller.py, sg.py, staircase.py, chain.py, examiner.py, solver.py,
                                                         grade.py, retrieve.py, context.py, store.py, l3ext.py, l4check.py, pyramid_score.py, ...)
code/bench/{clips,config,prompt,primitives,timeline_index}.py, code/bench/pyramid/*, code/gemini/nv_gemini.py   helpers, Gemini client
pyramid_v2/contracts/                                    70 contracts (§5)
pyramid_v2/runs/                                         50 reference runs (§5)
pyramid_v2/data/                                         task-55 evidence store + sg_cache of 12 tasks + capability map / registry / exclusions
video/P09-20240622-154652.mp4                            task-55 source video (240 s, 704 px, with audio)
```

Environment variables: `P2_REPO` (repo root, auto), `P2_ROOT` (defaults to `$P2_REPO/pyramid_v2`), `P2_VIDEO_DIR`, `P2_POSE_DIR`,
`HDEPIC_ANNOT_ROOT`, `HDEPIC_ROOT`, `GEMINI_BACKEND`, `GEMINI_API_KEY` / `NVIDIA_API_KEY`, `QWEN_PATH` (tokenizer for context trimming, optional).

## 9. Data credit and licence

Video and human annotations are from **HD-EPIC** (Perrett et al., 2025, https://hd-epic.github.io), CC BY-NC 4.0, redistributed for
non-commercial research only. Sub-goal event lists, derived spatial relations, generated questions and reference answers are model
outputs (Gemini 3.1 Pro) and are not human-verified.
