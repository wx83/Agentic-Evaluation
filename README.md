# Agentic Evaluation — pyramid2 adaptive four-layer benchmark on HD-EPIC

Two branches hold the complete, runnable snapshots (code, prompts, contracts, reference runs, one-video data bundle, scripts):

| branch | Solver (model under test) | Examiner / planner / judge | versions documented |
|---|---|---|---|
| [`gemini-solver`](../../tree/gemini-solver) | Gemini 4 | Gemini 3.1 Pro | v16, v16qa, v17, v18 (10 tasks; self / goldlive / gold / blind arms) |
| [`qwen-solver`](../../tree/qwen-solver) | Qwen3-Omni-30B-A3B-Instruct (local HTTP server, `qwen/`) | Gemini 3.1 Pro, or Qwen3-Omni itself | qwen_v14, qwen_v16 (Qwen examiner), qwen_v17, qwen_v18, qwen_v18b |

Start with the README of the branch you need; `main` only keeps this index and the original v17 one-task bundle history.
Full evidence store and pre-cut clips for all tasks: public Hugging Face dataset `WitneyWW/pyramid2-qwen-data-1028` (`setup_full_data.sh` on either branch).
`qwen-h200-bundle` is the older Qwen-server-only branch (superseded by `qwen-solver`).
