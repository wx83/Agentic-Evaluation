> **Scope planner** — the latest standalone scope planner is on branch [`scope-planner`](https://github.com/wx83/Agentic-Evaluation/tree/scope-planner).

# Agentic Evaluation — pyramid2 on HD-EPIC Method E · branch `qwen-solver`

Same benchmark code as branch `gemini-solver` (read that README first for the benchmark itself: layers, skills, tiers, arms, scoring,
install, keys, `run_task.sh`, `setup_full_data.sh`). This branch adds everything needed to evaluate
**Qwen3-Omni-30B-A3B-Instruct** as the Solver, and documents the runs in which Qwen was also the **Examiner**.

* **Solver = Qwen3-Omni** served by a small HTTP server on a GPU (`qwen/`), called by the examiner through `solver_backend: "qwen_http"`.
* **Examiner / planner / judge = Gemini 3.1 Pro** (versions `qwen_v17`, `qwen_v18`, `qwen_v18b`), or **Qwen3-Omni itself**
  (`qwen_v14`, `qwen_v16`; `examiner_backend: "qwen_http"`, judge still Gemini).
* All Gemini-solver contracts and reference runs are also present (they are the comparison baseline).

---

## 1. Install (two environments)

**A. Benchmark host** (where the examiner runs; CPU is enough): as on `gemini-solver`:

```bash
git clone -b qwen-solver https://github.com/wx83/Agentic-Evaluation.git && cd Agentic-Evaluation
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt     # + ffmpeg/ffprobe on PATH
export GEMINI_API_KEY=...        # or NVIDIA_API_KEY with GEMINI_BACKEND=nv   (Examiner / planner / judge are Gemini)
```

**B. Qwen server** (GPU host; one GPU with ≥ 80 GB, e.g. H100/H200, A100-80G; bf16 weights ≈ 60 GB + KV cache):

```bash
cd qwen
conda create -n qwen python=3.12 -y && conda activate qwen
sudo apt-get install -y ffmpeg                       # audio extraction
pip install -r requirements.txt                      # torch 2.9.1 cu128, transformers 4.57.1, qwen-omni-utils 0.0.9, librosa 1.0 (versions tested)
huggingface-cli download Qwen/Qwen3-Omni-30B-A3B-Instruct --local-dir ./model/Qwen3-Omni-30B-A3B-Instruct     # 66 GB
export QWEN_PATH=$PWD/model/Qwen3-Omni-30B-A3B-Instruct
./start_servers.sh 1 8799                            # one server per GPU: GPU0 → :8799 (2 GPUs: ./start_servers.sh 2 8799 → :8799 and :8800)
python3 smoke_test.py --url http://127.0.0.1:8799    # text-only, local-path video, base64 video → three answers (loading takes 2–3 min)
```

`qwen_server.py` is single-threaded (requests queue). API: `GET /` → `{"ok": true}`; `POST /ask` with
`{"text", "media_path" | "media_b64", "system"?, "max_new_tokens"}` → `{"raw", "meta": {n_input_tokens, n_output_tokens, peak_gpu_mb, latency}}`.
`qwen_agent.py` holds the model code (talker disabled, ffmpeg-based audio loading, `FPS_MAX_FRAMES` = 600).
`qwen/README_zh.md` is the original (Chinese) note with the FAQ.

**Connecting the two.** The contracts carry `"qwen_url": "http://127.0.0.1:8799"`. Override without editing:
`export QWEN_URL=http://<gpu-host>:8799` (or an SSH tunnel `ssh -N -L 8799:127.0.0.1:8799 <gpu-host>`). If the GPU host cannot read the
benchmark host's clip files, set `"qwen_send_media": true` in the contract: the clip bytes are then sent inline (base64).
`python3 cli.py preflight --contract …` probes the server.

## 2. Run

```bash
./run_task.sh <prefix> <task> <arm> [<arm> ...]        # prefix: qwen_v17 | qwen_v18 | qwen_v18b | qwen_v16 | qwen_v14 ; also g4_* (Gemini solver) for the baseline
./run_task.sh qwen_v17 55 self                          # Gemini examiner, Qwen solver, v17 design, task 55 (bundled data)
REPLAY_LEVELS="L3 L4" ./run_task.sh qwen_v17 55 gold    # corrected arm
./run_task.sh qwen_v17 55 blind                         # Qwen's own blind (no clip, no history) baseline
```

Task 55 runs on the bundled data; tasks 13 (v18) and 09 (qwen_v14) need `./setup_full_data.sh` (and `--with-videos` for v18's
10 s L4 clips of a task that was never run with v18). Speed on one RTX PRO 6000 (96 GB, HF eager): Solver median 39 s per item
(p90 274 s for 180 s clips), Qwen-as-Examiner median 68 s per call; one v17 task (≈ 100 items, one answer each) ≈ 2–3 h for the self arm.
Qwen answers once (`solver_reps: 1`); Gemini answered three times with majority vote — remember this when comparing.

## 3. Versions on this branch

| prefix | date | Examiner / planner | Solver | design base | tasks run | status |
|---|---|---|---|---|---|---|
| `qwen_v14` | 2026-10-28 | **Qwen3-Omni** (+ scope planner), judge Gemini | Qwen3-Omni | v14 (task-scope examiner, prompt `1027_prompts_hdepic_e_v13.md`, no verification items) | 09 (P08_R07_S09) self + gold | done |
| `qwen_v16` | 2026-10-29 | **Qwen3-Omni**, judge Gemini | Qwen3-Omni | v16 (sub-goal structure), format fields auto-filled when the Examiner omits them | 55, 39 self + gold | done |
| `qwen_v17` | 2026-11-01 | Gemini 3.1 Pro | Qwen3-Omni | v17 (event traversal) — identical to `g4_v17_*` except the solver | 55, 39, 05 self / gold / blind | contracts ready, **not run** (paused: ≈ 4.5 h per task on one GPU) |
| `qwen_v18` | 2026-11-01 | Gemini 3.1 Pro | Qwen3-Omni | v17 + L4 clip = last 10 s + all lower-layer items as declarative facts (`history_render: facts`) | 13 self (L1–L4) + gold (L3 L4) | done |
| `qwen_v18b` | 2026-11-01 | Gemini 3.1 Pro | Qwen3-Omni | v18 + same history scope in both arms (`history_select: by_subgoal`) + L4 asks all decision points at tier 1 (`stair_fixed_level_skills`) | 13: L1/L2 copied from v18, L3/L4 self | **partial** (paused after 2 L3 items) |

Contract keys specific to Qwen: `solver_backend: "qwen_http"`, `solver_model: "qwen3-omni-30b-a3b-instruct"`, `qwen_url`, `solver_reps: 1`,
optional `qwen_send_media`; for Qwen as Examiner: `examiner_backend` / `scope_backend: "qwen_http"`, `examiner_max_tokens` 4096,
`scope_max_tokens` 6144, `examiner_ctx_budget_tokens` 50000, `examiner_history_rows` 20, `examiner_ctx_fallback: drop_last_cluster`
(context trimming to Qwen's 65 k token window: context records farthest from the question window are dropped first, then the lower-ranked
evidence cluster; `context.trim_for_budget`).

## 4. Results

**Qwen as Examiner does not work with these prompts.** `qwen_v14` task 09: 218 of 250 Examiner outputs were rejected by the output
validators (option text repeated in the question 16×, wrong format for the tier 10×, unasked `skill_scope` entries ≈ 36×, evidence refs not
in context 9×, missing viewpoint / reference object 18×); 17 of 24 skills ended in `examiner_failed`, 26 items were scored, pyramid 0.98
(Gemini-solver v14 on the same task: 114 items, 1.59). Qwen's scope planner itself was usable (L1 7 / L2 16 / L3 11 / L4 4 entries, no
warnings) and the context trimming worked (median 40 k input tokens). `qwen_v16`: task 55 pyramid 1.05 (39 scored / 36 invalid items),
task 39 0.69 (28 / 33); self ≈ gold.

**Qwen as Solver, Gemini as Examiner** (`qwen_v18`, task 13): L1 20/46, L2 64/80 (17 invalid items from a sub-goal matching bug of that
day), L3 2/5 → corrected arm 5/5 (but the two arms received different history scopes: 5–16 vs 36–97 statements — fixed in v18b),
L4 1/4 → 1/4 with identical answers (the staircase stopped at the floor after 4 of 10 decision points — fixed in v18b).

**Qwen vs Gemini 4 under the same Gemini Examiner** (older design v8, 10 tasks, same contracts except the solver; runs in the public
dataset, not in this branch): mastery per layer Gemini 0.65 / 0.68 / 0.73 / 0.36 vs Qwen 0.32 / 0.38 / 0.39 / 0.09, pyramid 2.38 vs 1.18,
Gemini higher on 10/10 tasks; the gap is almost uniform over the layers (+0.26 … +0.34). The v17 three-task comparison (`qwen_v17`) is
the prepared, not yet executed, repetition of this on the current design.

## 5. Layout differences from `gemini-solver`

```
qwen/                      qwen_server.py, qwen_agent.py, requirements.txt (GPU env), start_servers.sh, smoke_test.py, sample/clip_20s.mp4, README_zh.md
prompts/1027_prompts_hdepic_e_v13.md     prompt used by qwen_v14 (Qwen examiner)
pyramid_v2/contracts/p2_hdepicE_1023t_qwen_*   19 contracts (table above)
pyramid_v2/runs/p2_hdepicE_1023t_qwen_*        9 reference runs (qwen_v14, qwen_v16, qwen_v18, qwen_v18b)
code/bench/pyramid2/{solver,examiner,scope,cli}.py   honour $QWEN_URL
```

Data credit and licence: as on `gemini-solver` (HD-EPIC, CC BY-NC 4.0; generated questions are Gemini / Qwen outputs, not human-verified).
