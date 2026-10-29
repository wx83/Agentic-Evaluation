"""Same-prompt examiner comparison: replay the exact examiner prompts of a finished run
against other text models and validate every proposal with the run's item validator.

    export OPENAI_API_KEY=...
    PYRAMID_SEED=43 $PY examiner_replay.py --run-id real_1001 --level 1 --models gpt-4o gpt-4o-mini

The prompts (and the original Gemini answers) come from logs/generator/gemini_calls.jsonl;
no target model is called. Output: <adaptive>/replay_<run>_L<k>/<model>.jsonl
"""
import argparse, json, re
from concurrent.futures import ThreadPoolExecutor

import pconfig as P
import assemble_formats as AF
import facts as F
import gemini_io
import openai_io
import adaptive as AD

CARDS_RE = re.compile(r"EVIDENCE_POOL \(verified cards available this turn\):\n(.*?)\n\nEVALUATION_HISTORY:", re.S)


def run_prompts(run_id, level):
    """First-attempt examiner prompt of every scored turn, in turn order, with Gemini's reply."""
    items = [json.loads(l) for l in (P.POUT / "adaptive" / run_id / f"L{level}" / "items.jsonl").open()]
    t0, t1 = items[0]["ts"], items[-1]["ts"]
    out = []
    for l in (P.LOGROOT / "generator" / "gemini_calls.jsonl").open():
        r = json.loads(l)
        if r.get("role") != "generator" or r.get("error") or f"CURRENT_LEVEL: L{level}" not in r["prompt"]:
            continue
        if "ITEM VALIDATION RESULT" in r["prompt"] or not ("2026-10-01T00:31" <= r["ts"] <= t1):
            continue
        out.append(r)
    return out


def validate(prop, cards, facts):
    """(format, errors). MC / short-answer go through adaptive.make_item; multi-select is checked
    against the truth values printed on the card (the statements are program-built)."""
    if not isinstance(prop, dict):
        return None, ["no parsable JSON object"]
    if prop.get("action") != "ASK":
        return None, [f"action {prop.get('action')!r}"]
    cid = prop.get("evidence_cluster_id")
    card = next((c for c in cards if c["evidence_cluster_id"] == cid), None)
    if card is None:
        return None, ["cluster not among offered cards"]
    pub, prv = prop.get("public") or {}, prop.get("private") or {}
    fmt = AD.FMT_OF.get(str(pub.get("format", "")).lower().replace("-", "_"))
    if fmt is None:
        return None, ["unknown format"]
    name = AD.FMT_NAME[fmt]
    errs = []
    if name not in card["allowed_formats"]:
        errs.append("format not allowed for this card")
    if prop.get("skill") and prop["skill"] != card["skill"]:
        errs.append("skill does not match card")
    if fmt == "ms":
        if "multi_select_statements" in card:
            gold = "".join(s["letter"] for s in card["multi_select_statements"] if s["true"])
            ref = "".join(sorted(set(re.findall(r"\b([ABCD])\b", str(prv.get("reference_answer", "")).upper()))))
            if ref != gold:
                errs.append("multi-select reference letters != verified true statements")
        return name, errs
    _, e = AD.make_item(prop, facts, {}, "replay", 0, "replay")
    for x in e:
        x = re.sub(r"'[^']*'|\"[^\"]*\"", "_", x)
        if x not in errs and "skill" not in x:
            errs.append(x)
    return name, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="real_1001")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--models", nargs="+", default=["gpt-4o", "gpt-4o-mini"])
    a = ap.parse_args()
    by_id, _ = AF.load_facts()
    recs = run_prompts(a.run_id, a.level)
    out_dir = P.POUT / "adaptive" / f"replay_{a.run_id}_L{a.level}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(recs)} examiner prompts from {a.run_id} L{a.level}", flush=True)

    def one(model, i, r):
        cards = json.loads(CARDS_RE.search(r["prompt"]).group(1))
        facts = {c["evidence_cluster_id"]: by_id[c["evidence_cluster_id"]] for c in cards
                 if c["evidence_cluster_id"] in by_id}
        if model == "gemini":
            raw, usage = r["response"], {"tok_in": r.get("tok_in"), "tok_out": r.get("tok_out")}
        else:
            try:
                raw, _ = openai_io.gen(r["prompt"], max_tokens=2048, model=model, role="replay")
            except RuntimeError as e:
                raw = f"ERROR {e}"
            usage = {}
        prop = gemini_io.jparse(raw) if not raw.startswith("ERROR") else None
        if isinstance(prop, list):
            prop = prop[0] if prop else None
        fmt, errs = validate(prop, cards, facts)
        card = next((c for c in cards if c["evidence_cluster_id"] == (prop or {}).get("evidence_cluster_id")), {})
        return {"turn": i + 1, "model": model, "prompt_sha": r["prompt_sha"], "n_cards": len(cards),
                "cluster": (prop or {}).get("evidence_cluster_id"), "skill": card.get("skill"),
                "format": fmt, "revisit": "already_tested" in card, "errors": errs,
                "question": ((prop or {}).get("public") or {}).get("question"),
                "strategy": (prop or {}).get("strategy"), "unresolved_issue": (prop or {}).get("unresolved_issue"),
                "selection_reason": (prop or {}).get("selection_reason"), "raw": raw, **usage}

    for model in ["gemini"] + a.models:
        with ThreadPoolExecutor(1 if model == "gemini" else 4) as ex:
            rows = list(ex.map(lambda ir: one(model, *ir), enumerate(recs)))
        name = model.replace("/", "_")
        (out_dir / f"{name}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))
        print(f"{model}: valid {sum(not x['errors'] for x in rows)}/{len(rows)}", flush=True)


if __name__ == "__main__":
    main()
