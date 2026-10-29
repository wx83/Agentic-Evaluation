"""Gemini cost estimate for two routes over HD-EPIC (or any number of video hours):

  A. object-centric labeling  (object_memory/pipeline stage 2: object list + optional per-object appearance;
                               the stage-14 question-writing calls are excluded unless --oc-qa)
  B. the question pyramid     (4 levels x 5 answer formats x {video, blind}), Gemini as writer + judge + test-taker

    python3 cost_estimate.py                       # full HD-EPIC, defaults below
    python3 cost_estimate.py --hours 4.3 --formats 1 --blind 0   # one seed-43 pyramid, single choice only, video tier only
    python3 cost_estimate.py --tier batch --thinking-mult 2 --frames

Every per-call token figure is measured from logs/*/gemini_calls.jsonl (usage_metadata, recorded since 2026-09-28)
unless marked "estimated". Prices from ai.google.dev/gemini-api/docs/pricing (gemini-3.5-flash, 2026-09-29).
"""
import argparse, json

PRICE = {  # USD per 1M tokens; output includes thinking tokens
    "standard": {"in": 1.50, "out": 9.00},
    "batch":    {"in": 0.75, "out": 4.50},
    "flex":     {"in": 0.75, "out": 4.50},
    "priority": {"in": 2.70, "out": 16.20},
}
HDEPIC_HOURS = 41.2          # 156 videos, sum of last narration stop time per video (HD_EPIC_Narrations.pkl)
HDEPIC_VIDEOS = 156
CURRENT_HOURS = 4.3          # the 5 videos used so far
CURRENT_BASE_Q = 400         # 100 questions x 4 levels per pyramid (one seed)

# ---- pyramid: measured per-call tokens ----
TOK = {
    "answer_video": (2921, 17),     # mean of 1,570 video calls (30 s clip + question)
    "answer_blind": (103, 11),      # median of 1,076 blind calls
    "phrase":       (1700, 470),    # single choice: estimated from median 6,843 / 1,876 chars at ~4 chars per token (776 calls)
    "phrase_fmt":   (1859, 613),    # other formats (yn / select-all statements, open stems): mean of 76 measured calls, 2026-09-29
    "judge":        (186, 30),      # median of 268 judge calls
}
RETRY = 0.01                 # 9 retries in 986 calls
PHRASE_CALLS_PER_BASE_Q = 140 / 100 / 10    # single choice: 140 candidates per 100 kept, 10 facts per call
PHRASE_FMT_CALLS_PER_BASE_Q = 76 / 160      # measured: 742 packets (1 yn statement + ~3 select-all statements + open stem) = 76 calls for 160 base questions
MARGIN = 1.5                                # headroom for rejections re-phrased, extra candidates, retries; applied when --flexible
JUDGE_CALLS_PER_BASE_Q_PER_MODEL = 2 * 0.48 * 0.45   # 2 open slots x 48% open-eligible x 45% rules undecided

# ---- object-centric: per 30 s chunk (extrapolated from the single chunk that exists, P03 0-30 s) ----
FLEX = False
CHUNK_SEC = 30
OC = {  # calls per chunk, (in, out) tokens per call
    "objects_text":   (1, (1800, 300)),
    "appearance_img": (6, (800, 50)),        # only with --frames; 6 objects in chunk_000, one crop each
    "qa_trajectory":  (1, (10500, 9000)),
    "qa_lookup":      (1, (10500, 7500)),
}


def pyramid(hours, formats, blind, models, tier, density, phrase_formats=None):
    """phrase_formats: how many of the formats Gemini writes the wording for (decided 2026-09-29: all of them)."""
    if phrase_formats is None:
        phrase_formats = formats
    base_q = density * hours
    ans_video = base_q * formats
    ans_blind = base_q * formats * (1 if blind else 0)
    phrase = base_q * PHRASE_CALLS_PER_BASE_Q
    phrase_fmt = base_q * PHRASE_FMT_CALLS_PER_BASE_Q if phrase_formats > 1 else 0
    judge = base_q * JUDGE_CALLS_PER_BASE_Q_PER_MODEL * models * (2 if blind else 1) / 2 * (formats / 5 if formats < 5 else 1)
    # judge only applies to the open-answer slots; with formats < 5 scale down proportionally (0 when single choice only)
    if formats == 1:
        judge = 0
    rows = [("answer, with video", ans_video, TOK["answer_video"]),
            ("answer, blind", ans_blind, TOK["answer_blind"]),
            ("write single-choice question", phrase, TOK["phrase"]),
            ("write the other formats (statements, open stems)", phrase_fmt, TOK["phrase_fmt"]),
            ("judge short answers", judge, TOK["judge"])]
    return base_q, _total(rows, tier, MARGIN if FLEX else 1.0)


def object_centric(hours, frames, thinking_mult, tier, qa=False):
    """Annotation only by default (stage 2). --oc-qa adds the stage-14 question-writing calls."""
    chunks = hours * 3600 / CHUNK_SEC
    rows = []
    for name, (n, (ti, to)) in OC.items():
        if name == "appearance_img" and not frames:
            continue
        if name.startswith("qa") and not qa:
            continue
        mult = thinking_mult if name.startswith("qa") else 1.0
        rows.append((name, n * chunks, (ti, to * mult)))
    return chunks, _total(rows, tier, MARGIN if FLEX else 1.0)


def _total(rows, tier, margin=1.0):
    p = PRICE[tier]
    out, T = [], {"calls": 0, "tok_in": 0, "tok_out": 0, "usd": 0.0}
    for name, calls, (ti, to) in rows:
        calls *= (1 + RETRY) * margin
        tin, tout = calls * ti, calls * to
        usd = (tin * p["in"] + tout * p["out"]) / 1e6
        out.append({"item": name, "calls": round(calls), "tok_in": round(tin), "tok_out": round(tout), "usd": round(usd, 2)})
        T["calls"] += calls; T["tok_in"] += tin; T["tok_out"] += tout; T["usd"] += usd
    T = {k: (round(v, 2) if k == "usd" else round(v)) for k, v in T.items()}
    return {"rows": out, "total": T}


def md_table(res):
    L = ["| item | calls | input tokens | output tokens | USD |", "|---|---:|---:|---:|---:|"]
    for r in res["rows"]:
        L.append(f"| {r['item']} | {r['calls']:,} | {r['tok_in']:,} | {r['tok_out']:,} | {r['usd']:,.2f} |")
    t = res["total"]
    L.append(f"| **total** | **{t['calls']:,}** | **{t['tok_in']:,}** | **{t['tok_out']:,}** | **{t['usd']:,.2f}** |")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=HDEPIC_HOURS)
    ap.add_argument("--density", type=float, default=CURRENT_BASE_Q / CURRENT_HOURS, help="base questions per video hour")
    ap.add_argument("--formats", type=int, default=5, help="answer formats per base question (1 = single choice only)")
    ap.add_argument("--blind", type=int, default=1, help="1 = also ask every question without the clip")
    ap.add_argument("--models", type=int, default=1, help="tested models whose short answers Gemini judges")
    ap.add_argument("--phrase-formats", type=int, default=None,
                    help="formats whose wording Gemini writes (default: all of --formats; 1 = single choice only, as run so far)")
    ap.add_argument("--tier", default="standard", choices=list(PRICE))
    ap.add_argument("--thinking-mult", type=float, default=1.0, help="multiply object-centric QA output tokens (thinking unknown)")
    ap.add_argument("--frames", action="store_true", help="object-centric: include the per-object image appearance calls")
    ap.add_argument("--oc-qa", action="store_true", help="object-centric: also include the stage-14 question-writing calls")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--flexible", action="store_true", help=f"multiply every call count by {MARGIN} for headroom")
    a = ap.parse_args()
    global FLEX
    FLEX = a.flexible
    base_q, P = pyramid(a.hours, a.formats, a.blind, a.models, a.tier, a.density, a.phrase_formats)
    chunks, O = object_centric(a.hours, a.frames, a.thinking_mult, a.tier, a.oc_qa)
    if a.json:
        print(json.dumps({"args": vars(a), "pyramid": {"base_questions": round(base_q), **P},
                          "object_centric": {"chunks": round(chunks), **O}}, indent=1))
        return
    print(f"## Route A: object-centric labeling, {a.hours} h = {chunks:,.0f} chunks of 30 s, tier={a.tier}, "
          f"frames={'yes' if a.frames else 'no'}, question writing={'yes' if a.oc_qa else 'no'}\n")
    print(md_table(O))
    print(f"\n## Route B: pyramid, {a.hours} h at {a.density:.1f} base questions/h = {base_q:,.0f} base questions, "
          f"{a.formats} formats ({a.phrase_formats or a.formats} worded by Gemini), blind={'yes' if a.blind else 'no'}, "
          f"{a.models} judged model(s), tier={a.tier}\n")
    print(md_table(P))


if __name__ == "__main__":
    main()
