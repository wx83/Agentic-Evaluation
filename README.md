# Agentic Evaluation — Pyramid v17 on one HD-EPIC video

This repository is a self-contained snapshot of the **pyramid2** adaptive examiner (design v17, 2026-10-29)
together with everything needed to re-run it on **one video / one recipe step**:

* **Examiner / question generator / planner / judge:** `gemini-3.1-pro-preview` (Gemini 3.1 Pro)
* **Solver (the model being evaluated):** Gemini 4 (`gemini-4-argon` on the NVIDIA gateway; see §3 for naming)

The task is HD-EPIC video `P09-20240622-154652`, recipe *Chicken Cheese Balls*, official step `P09_R02_S07`
("Dredge each chicken-cheese ball into flour, then dip into egg and roll in the breadcrumbs"), 6.3 s – 232.8 s.
Reference runs of both arms (`self`, `goldlive`) with every generated question, solver answer, grade and token
usage are included under `pyramid_v2/runs/`.

If you are reading this with an AI coding assistant (Claude Code, etc.): the assistant can follow §2–§5 verbatim.
Everything is plain Python 3 + ffmpeg; no GPU, no dataset download.

---

## 1. Layout

```
README.md                     this file
run_v17_task55.sh             one-shot reproduction (both arms + scores)
requirements.txt              google-genai, numpy, requests   (+ ffmpeg/ffprobe on PATH)
.secrets/                     put your API key here (git-ignored), see .secrets/README.md
video/P09-20240622-154652.mp4 first 240 s of the HD-EPIC video, 704×704, 30 fps, with audio (23 MB)
prompts/1028_prompts_hdepic_e_v16.md
                              THE prompts: shared Examiner system prompt (§2), L1–L4 prompts (§3–§6),
                              task-context addendum (§7), sub-goal / scope planner prompt (§8).
                              prompts.py cuts the ```text blocks by their "## N." headings.
design/v17_design.md          what v17 does (event loop, ladder, arms, scoring)
design/v17_results_notes_zh.md original lab notes (Chinese)
code/bench/pyramid2/          the examiner (see table below)
code/bench/{clips,config,prompt,primitives,timeline_index}.py, code/bench/pyramid/{formats,pconfig,phrase,gemini_io}.py
                              small helpers the examiner imports (clip cutting, answer formats)
code/gemini/nv_gemini.py      Gemini client; backend switch (Google AI Studio or NVIDIA gateway)
pyramid_v2/data/              evidence store for this one video (1 026 verified annotation records),
                              capability map, extension registry, skill exclusions, sample list,
                              sg_cache/ = cached sub-goal planner output (so the planner call is optional)
pyramid_v2/contracts/         run contracts (= all hyper-parameters) for the self and goldlive arms
pyramid_v2/runs/              reference runs: L{1..4}/history.jsonl (every item), summary.json, state.json,
                              contexts/ (exact JSON the Examiner saw), usage.jsonl, report.md, score.json
```

Main modules in `code/bench/pyramid2/`:

| file | role |
|---|---|
| `cli.py` | entry point: `preflight`, `run`, `report`, `sg-dry`, `replay`, `compare` |
| `controller.py` | one turn = build context → Examiner proposes an item → validate → Solver answers (3 reps) → grade |
| `sg.py` | sub-goal planner (Gemini 3.1 Pro) + **v17 event loop** (`run_layer_events`, §8 of the file) |
| `staircase.py` | 2-down-1-up difficulty ladder per skill, 4 levels, boundary detection |
| `chain.py` | lower-layer history shown to the Solver (`by_event` selection in v17) |
| `examiner.py` / `prompts.py` | Gemini call for the Examiner, output validation, prompt slicing |
| `solver.py` | Gemini 4 call with the inlined clip (video+audio bytes), answer parsing |
| `grade.py` | rule grading for choice items; Gemini 3.1 Pro judge for short-answer / plan items |
| `retrieve.py` / `context.py` / `store.py` | evidence clusters per skill, runtime context JSON, jsonl store |
| `l3ext.py` / `l4check.py` / `gap_distractors.py` | L3 relation skills, L4 answerability filter, gap-item distractors |
| `pyramid_score.py` / `merge_runs.py` / `p2report.py` | scoring, merging per-task runs, Markdown report |
| `mock.py` | offline mock Examiner + Solver (no API) for testing the state machine |
| `build_data.py`, `adapters/` | how `pyramid_v2/data` was built from the full HD-EPIC release (not needed here) |

## 2. Install

```bash
git clone https://github.com/wx83/Agentic-Evaluation.git
cd Agentic-Evaluation
python3 -m venv .venv && source .venv/bin/activate        # Python ≥ 3.10 (3.14 used originally)
pip install -r requirements.txt
ffmpeg -version && ffprobe -version                          # must be on PATH
```

Offline smoke test (no API key, ~10 s): runs the whole L1 state machine with a mock examiner/solver.

```bash
cd code/bench/pyramid2
python3 - <<'PY'
import json; c=json.load(open("../../../pyramid_v2/contracts/p2_hdepicE_1023t_g4_v17_self__55.json"))
c["run_id"]="p2_mock_L1"; json.dump(c,open("../../../pyramid_v2/contracts/p2_mock_L1.json","w"),indent=1)
PY
GEMINI_BACKEND=google python3 cli.py run --contract ../../../pyramid_v2/contracts/p2_mock_L1.json --levels L1 --mock "W,W,C,C,W,C"
tail -3 ../../../pyramid_v2/runs/p2_mock_L1/run.log      # expect "L1: EVENT_LOOP_COMPLETE ..." then "run finished"
```

(The mock examiner writes placeholder questions, so most mock items are rejected by the v17 validators as
`item_invalid`; that is expected. Clips are cut into `pyramid_v2/media/`.)

## 3. API keys and model names

The code talks to Gemini through the `google-genai` SDK. Two backends, chosen with `GEMINI_BACKEND`:

| backend | key | model names in the contract |
|---|---|---|
| `google` (**default in the scripts here**) — Google AI Studio / `generativelanguage` API | `export GEMINI_API_KEY=...` or write it to `.secrets/gemini_api_key` | the `gcp/google/` prefix is stripped automatically → `gemini-3.1-pro-preview`, `gemini-4-argon` |
| `nv` — NVIDIA `inference-api.nvidia.com` gateway (what the reference runs used) | `export NVIDIA_API_KEY=...` or `.secrets/nvidia_key` | used verbatim: `gcp/google/gemini-3.1-pro-preview`, `gcp/google/gemini-4-argon` |

Model roles are set in the contract JSON and nowhere else:

```json
"examiner_model": "gcp/google/gemini-3.1-pro-preview",   // question generation
"scope_model":    "gcp/google/gemini-3.1-pro-preview",   // sub-goal planner (cached in data/sg_cache)
"judge_model":    "gcp/google/gemini-3.1-pro-preview",   // short-answer / plan grading
"solver_model":   "gcp/google/gemini-4-argon",           // the model under test
"solver_thinking": "off", "solver_reps": 3
```

If your provider calls Gemini 4 something else, edit `solver_model` in the two contracts; the code only
special-cases the substring `gemini-4` (it sends `thinking_level="low"` instead of `thinking_budget=0`,
see `solver.py:ask`). Check connectivity with

```bash
cd code/bench/pyramid2
GEMINI_BACKEND=google python3 cli.py preflight --contract ../../../pyramid_v2/contracts/p2_hdepicE_1023t_g4_v17_self__55.json
```

which sends one "Reply with OK" request per role and prints `probe='OK'` for each.

## 4. Reproduce the v17 run

```bash
GEMINI_BACKEND=google ./run_v17_task55.sh          # both arms, ~100 items each, L1→L4, then scores
```

What it does, step by step (so you can run pieces by hand):

1. copies each contract to a new `run_id` (`p2_v17_self__55_repro`, `p2_v17_goldlive__55_repro`);
2. `cli.py preflight` — key / model check;
3. `run_smoke.sh <contract> L1 L2 L3 L4` → `cli.py run`, resumable: re-running with the same `run_id`
   continues from `L*/state.json`;
4. `cli.py report --run-id …` → `runs/<run_id>/report.md`;
5. `pyramid_score.py runs/<run_id>` → pyramid score, height, per-skill boundaries (also `score.json`).

Inside `cli.py run`, for every layer:

* `sg.py` loads the sub-goal plan (cache hit in `data/sg_cache/`; a new plan is only requested if the
  planner prompt or inputs changed) and lists the expected events per sub-goal (≤ 3 per sub-goal).
* **Event loop (v17):** for each event in time order and each applicable skill, `controller.run_turn`
  builds the runtime context (`contexts/L{k}_{turn}.json`: the clip reference, the verified evidence
  records with role target/context, the skill's current difficulty level, the same-event lower-layer
  history), sends the layer prompt + context to the Examiner, validates the returned item (format,
  event words present, position-in-clip wording, no goal leakage, answerability), cuts the clip with
  ffmpeg (288×288, audio kept), asks the Solver 3 times, grades (rule or Gemini judge), and moves the
  skill's ladder up/down.
* After a skill's ladder converges it keeps answering the remaining events at the boundary level (`verify`).
* L4 uses the v16 unified ladder on the decision points (one per sub-goal), with the official step goal shown.

Expected cost per arm (from `usage.jsonl` of the reference run): ≈ 100 examiner calls (~22 k input tokens
each), ≈ 300 solver calls with an inlined clip, ≈ 20 judge calls. Wall-clock ≈ 2–3 h per arm on the gateway.

## 5. Reading the output

* `runs/<id>/L2/history.jsonl` — one line per item. Key fields: `capability_skill`, `difficulty_level`,
  `difficulty_format`, `question`, `options`, `reference`, `solver_answer`, `verdict`, `media_refs`
  (absolute seconds in the source video), `history_used`, `sg` (sub-goal / event ids), `reps`.
* `runs/<id>/L2/summary.json` — per-skill staircase trace (`levels_tested`, `per_level`, `boundary`, `stop`).
* `runs/<id>/score.json` — layer masteries and the pyramid score (definition in `design/v17_design.md` §6).
* `runs/<id>/contexts/` — the exact JSON each Examiner call received (useful for prompt debugging).

Example item from the reference self run (L2, `action_recognition`, level 2):

> In the clip, what action does the camera wearer perform involving the lid of breadcrumbs and the bowl?
> A. Pours the contents of the lid into the bowl / B. Scoops breadcrumbs from the bowl using the lid /
> C. Places the lid on top of the bowl / D. Taps the lid against the edge of the bowl — reference A, solver A.

Reference scores (Gemini 4 solver): self arm pyramid 2.65 / 4, goldlive arm 1.90 / 4. Differences between
the arms on a single task are within run-to-run noise (see `design/v17_results_notes_zh.md`).

## 6. Changing things

* **Another solver:** change `solver_model` (and `solver_thinking`) in the contract. `solver_backend: "qwen_http"`
  points at a local HTTP server (`qwen_server.py`) instead of Gemini.
* **History arm:** `history_mode` = `self` | `gold` | `none`.
* **Budget:** `events_per_subgoal`, `history_per_layer`, `solver_reps`, `include_skills`.
* **Prompts:** edit `prompts/1028_prompts_hdepic_e_v16.md` (keep the `## N.` headings and ```text fences);
  the contract's `prompt_md` points at it (`$P2_REPO` is expanded).
* **Another video:** you need the full HD-EPIC release and `build_data.py` + `adapters/` to produce
  `evidence.jsonl`, `media_manifest.jsonl` and `hdepic_e_samples.json`; the paths in `p2config.SOURCES`
  and `bench/config.py` (`HDEPIC_ROOT`) must then point at your copy. This bundle only contains the records of
  `P09-20240622-154652`.

Environment variables: `P2_REPO` (repo root, auto-detected), `P2_ROOT` (defaults to `$P2_REPO/pyramid_v2`;
set it elsewhere to keep the reference runs untouched), `P2_VIDEO_DIR` (defaults to `$P2_REPO/video`),
`GEMINI_BACKEND`, `GEMINI_API_KEY` / `NVIDIA_API_KEY`.

## 7. Data credit and licence

The video and the human annotations it was built from are from
**HD-EPIC** (Perrett et al., 2025, https://hd-epic.github.io), released under **CC BY-NC 4.0**;
they are redistributed here for non-commercial research only, trimmed to the first 240 s and downscaled.
Sub-goal texts, spatial relations derived from the official 3D annotations, and all generated questions are
model outputs of this pipeline (Gemini 3.1 Pro) and are **not** human-verified.
