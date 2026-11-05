#!/usr/bin/env python3
"""11-03 comp 模式离线 dry run:python3 comp_dry.py 55 13 39 [--profile-runs r1,r2,...]
对每个 task:适用 event 数、候选依赖数、通过检查数(换锚点 gold 必变)、可配对数、淘汰原因;展示一条通过的链与一条被拒的链。不调模型。"""
import sys, json, random, collections, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import cli, sg, v24, comp, store as S, p2config as P

ap = argparse.ArgumentParser(); ap.add_argument("tasks", nargs="+"); ap.add_argument("--profile-runs", default=None); ap.add_argument("--contract-prefix", default="p2_hdepicE_1023t_g4_v24_self__")
a = ap.parse_args()
C = P.ROOT / "contracts"
st = S.Store(); _ = st.evidence
rd = Path("/tmp/claude-1005/-mnt-work-new/10aaa04e-8ac0-4078-bf64-d74fdac237f0/scratchpad/v24_dry"); rd.mkdir(parents=True, exist_ok=True)
prof_runs = (a.profile_runs.split(",") if a.profile_runs else [f"p2_hdepicE_1023t_g4_v24_self__{t}" for t in a.tasks])
profile = comp.build_profile([P.RUNS / r for r in prof_runs])
print(f"profile version {profile['version']} from {prof_runs}")
for sk, pats in profile["skills"].items():
    sts = collections.Counter(comp.status(profile, sk, k)["status"] for k in pats)
    print(f"  {sk}: {len(pats)} patterns {dict(sts)}; weak: {[k for k in pats if comp.status(profile, sk, k)['status']=='weak']}; strong: {[k for k in pats if comp.status(profile, sk, k)['status']=='strong'][:8]}")


def fake_out(c, ev, fmt, q):
    return {"action": "PROPOSE_DIAGNOSTIC", "evidence_cluster_id": c["evidence_cluster_id"], "strategy": "coverage", "selection_reason": "dry",
            "public": {"format": fmt, "question": q, "options": ["A. x", "B. y", "C. z", "D. w"], "media_refs": [{"media_id": c["media_id"], "windows": [list(c["window"])]}], "task_conditions": None},
            "private": {"sg_event_id": ev["event_id"], "proposed_reference_answer": "A", "evidence_refs": [r["evidence_id"] for r in c["core"][:1]], "gold_answer": None,
                        "gold_verification_status": "needs_verification", "validation_status": "PENDING_VALIDATION"}}


tot = collections.Counter()
for t in a.tasks:
    c0 = cli.load_contract(str(C / f"{a.contract_prefix}{t}.json"))
    c0 = dict(c0, comp_mode=True, comp_profile_runs=prof_runs, run_id=f"dry_comp_{t}")
    tid = c0["task_sample_id"]; plans = sg.ensure(c0, st, run_dir=rd, task_ids=[tid]); plan = plans[tid]; ti = sg.task_info(st, tid)
    v24._PROFILE[c0["run_id"]] = profile
    print(f"\n== task {t} ({tid})")
    shown_ok = shown_bad = False
    for layer, skills in (("L2", ["action_recognition", "event_object_role"]), ("L3", ["object_state_change", "object_location_at_time"])):
        pools = sg.build_pools(st, c0, plans, skills, layer, seed=1023)
        for cap, cl in pools.items():
            n_ev = n_comp = n_pass = 0; reasons = collections.Counter(); pairs = collections.defaultdict(lambda: collections.Counter())
            for c in cl:
                for ev in c["sg"]["events"]:
                    n_ev += 1
                    comp_ = c["sg"]["comp_by_event"].get(ev["event_id"]) or {}
                    if comp_.get("fallback"): reasons[comp_["fallback"]] += 1; continue
                    n_comp += 1
                    # 模拟出题:程序补齐后,替代锚点的 gold 必须 ≠ 目标 gold
                    ctx = {"difficulty": v24.spec_for(cap, 2, c, contract=c0), "verified_evidence": c["core"] + c["context"]}
                    out = fake_out(c, ev, "single_choice", f"placeholder about {comp_['target']['object']}")
                    sg.autofill(out, ctx, c)
                    pri = out["private"]; cp = pri.get("comp")
                    if cp:
                        alt_ok = [g for g in cp["alt_gold"].values() if g is not None and g != cp["target_gold"]]
                        if alt_ok: n_pass += 1; pairs[cp["pair_key"]][cp["prereq"]["status"]] += 1
                        else: reasons["alt_gold_equal_or_missing"] += 1
                        if not shown_ok and alt_ok:
                            shown_ok = True
                            print(f"  [PASS] {cap} event {ev['event_id']} chain {cp['chain']}\n         question stub: {out['public']['question']!r}\n         options {out['public']['options']} ref {pri['proposed_reference_answer']}\n         target {json.dumps(cp['target'], ensure_ascii=False)[:220]}\n         alts {[(x['kind'], x.get('object'), x.get('ordinal'), x['span']) for x in cp['alts']]} alt_gold {cp['alt_gold']}\n         prereq {cp['prereq']['skill']}={cp['prereq']['pattern']} -> {cp['prereq']['status']} ({cp['prereq']['n_wrong_events']}/{cp['prereq']['n_events']}) excluded {cp['excluded_from_profile']}")
                    else:
                        reasons[pri.get("comp_fallback") or "autofill_no_comp"] += 1
            n_pair = sum(1 for pk, cnt in pairs.items() if cnt.get("weak") and cnt.get("strong"))
            tot.update({"events": n_ev, "composed": n_comp, "passed": n_pass})
            print(f"  {layer} {cap}: applicable events {n_ev}, candidate deps {n_comp}, passed gold-sensitivity {n_pass}, pair groups {len(pairs)} (weak+strong both present: {n_pair}), rejections {dict(reasons)}")
            if not shown_bad and reasons:
                bad = next(((c, ev) for c in cl for ev in c["sg"]["events"] if (c["sg"]["comp_by_event"].get(ev["event_id"]) or {}).get("fallback")), None)
                if bad:
                    c, ev = bad; shown_bad = True
                    print(f"  [REJECT] {cap} event {ev['event_id']} ({ev['description'][:60]!r}): {c['sg']['comp_by_event'][ev['event_id']]['fallback']}")
print("\nTOTAL", dict(tot))
