"""闯关 runner：逐链 4 轮，答对才进下一层；答错记 depth 后注入正确答案继续（兵分两路）。"""
import json, argparse, time, importlib, os, sys, re
import config as C
from timeline_index import TimelineIndex
import prompt as PR, memory as MEM, clips

TIERS = ["Easy", "Low", "Medium", "High"]        # 只给 report.py 用；本文件按 steps 迭代，与层数无关


def run_chain(agent, chain, ix, mode, propagate=False):
    media = memtext = None
    wins = [tuple(w) for w in chain.get("windows", [])]
    if mode == "memory":
        if wins:                                   # 多窗口链：每个窗口各渲一段
            memtext = "\n\n".join(
                "[excerpt %d, %.0f-%.0f s of the recording]\n%s" % (i + 1, a, b, MEM.render(ix, a, b)[0])
                for i, (a, b) in enumerate(wins))
        else:
            memtext, _ = MEM.render(ix, chain["clip_start"], chain["clip_end"])
    elif mode == "episodes":
        assert wins, "episodes 档要求链里有 windows 字段"
        media = clips.episodes_path(chain["video_id"], wins, chain.get("region_box"))
    elif mode == "clip30":
        media = clips.clip_path(chain["video_id"], chain["clip_start"], chain["clip_end"])
    else:
        media = clips.clip_path(chain["video_id"], chain["long_start"], chain["long_end"])
    origin = chain["long_start"] if mode == "long5m" else chain["clip_start"]

    sess = agent.start(chain, media=media, memory=memtext)
    depth, turns, slots = None, [], {}      # slots: <PREV:OC-k.field> -> agent 自己给出的值
    try:
        for k, st in enumerate(chain["steps"]):
            # 某些层在不同输入档下题面不同（memory 档没有画面，画不出 <REGION>）
            qtext = st.get("question_by_mode", {}).get(mode) or \
                    st.get("question_template") or st["question"]
            # 用 agent 自己在前几层给出的答案填槽。缺槽说明上游没答出来，退回 gold 渲染版。
            for tok, val in slots.items():
                qtext = qtext.replace(tok, val)
            if "<PREV:" in qtext:
                qtext = st["question"]
            q = PR.build(qtext, st["options"])
            if k == 0:
                pb = chain.get("preamble_by_mode") or {}
                pre = pb.get(mode, pb.get("_default")) or chain.get("preamble")
                if pre:
                    q = pre + "\n\n" + q
            try:
                raw, meta = sess.ask(q)
                err = None
            except Exception as e:
                raw, meta, err = "", {}, f"{type(e).__name__}: {str(e)[:200]}"
            idx = PR.score_choice(raw, st["options"])
            t_hat = PR.parse_time(raw)
            gold = "ABCD".index(st["correct_option"])
            correct = (idx == gold)
            loc_err = None
            if t_hat is not None:
                # 多窗口链一律要求报原片绝对时间：片内时间在 memory 档根本没有对应物，
                # 两档用不同语义会让 localization_error 不可比。
                t_abs = t_hat if wins else origin + t_hat
                loc_err = round(abs(t_abs - st["evidence_t"]), 2)
            injected = False
            # 本层实际向下游传的答案：答对就是它自己的，答错按兵分两路注入正确答案
            eff = st["answer"] if not correct else st["options"][idx][3:].strip()
            if not correct and propagate and idx is not None:
                eff = st["options"][idx][3:].strip()
            emitted = st.get("emit", {}).get(eff, {})
            for f, v in emitted.items():
                slots[f"<PREV:{st['tier']}.{f}>"] = v
            if not correct:
                if depth is None:
                    depth = k                       # 通关深度：第一次答错处定格
                injected = True
                # 兵分两路：注入正确答案，让后续层仍有独立样本。
                # 注入文本必须与要求的输出格式一致 —— 原写法只注入 "Answer: X"，等于往
                # history 里塞了一条不带 Time: 行的示范；实测 Qwen 从下一轮起就照着那个短格式
                # 作答，而且答对的轮次也不再恢复，8 轮里 6 轮报不出时间，直接废掉
                # localization_error 这个指标。保留 agent 自己报的那行时间（不是 gold 的，
                # 否则等于白送它正确定位），只换答案字母。
                keep = ""
                m = re.search(r"(?im)^\s*time\s*[:：].*$", raw or "")
                if m:
                    keep = "\n" + m.group(0).strip()
                inj = f"Answer: {st['correct_option']}{keep}"
                if hasattr(sess, "history") and sess.history:
                    sess.history[-1] = (q, inj)
                elif hasattr(sess, "conv") and sess.conv:
                    sess.conv[-1] = {"role": "assistant", "content":
                                     [{"type": "text", "text": inj}]}
            turns.append({"tier": st["tier"], "question_id": st["question_id"],
                          "rendered_question": qtext, "effective_answer": eff,
                          "emitted": emitted,
                          "prompt": q, "raw_response": raw, "parsed_index": idx,
                          "parsed_time": t_hat, "localization_error_sec": loc_err,
                          "gold_index": gold, "correct": correct, "injected": injected,
                          "error": err, **meta})
            if err:
                break
    finally:
        sess.close()
    if depth is None:
        depth = len([t for t in turns if t["correct"]])
    return {"chain_id": chain["chain_id"], "video_id": chain["video_id"], "mode": mode,
            "media": str(media) if media else None, "origin_sec": origin,
            "depth": depth, "needle_position": chain["needle_position"],
            "clip_start": chain["clip_start"], "turns": turns}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True,
                    choices=["gemini", "qwen", "mock", "videollama2", "minicpmo"])
    ap.add_argument("--mode", required=True,
                    choices=["memory", "clip30", "long5m", "episodes", "all"])
    ap.add_argument("--bench", default="chains.json", help="题库文件名，位于 _shared/")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--propagate", action="store_true",
                    help="答错时把 agent 自己的错答案传给下一层（默认注入正确答案，兵分两路）")
    a = ap.parse_args()

    data = json.loads((C.SHARED / a.bench).read_text())
    chains = data["chains"][:a.limit] if a.limit else data["chains"]
    ix = TimelineIndex(data["video_id"])

    if a.agent == "mock":
        from agents.mock_agent import MockAgent
        agent = MockAgent(oracle=a.oracle)
        tag = "mock_oracle" if a.oracle else "mock"
    elif a.agent == "gemini":
        from agents.gemini_agent import GeminiAgent
        agent = GeminiAgent(); tag = "gemini"
    elif a.agent == "qwen":
        from agents.qwen_agent import QwenAgent
        agent = QwenAgent(); tag = "qwen"
    elif a.agent == "videollama2":
        from agents.videollama2_agent import VideoLLaMA2Agent
        agent = VideoLLaMA2Agent(); tag = "videollama2"
    else:
        from agents.minicpm_agent import MiniCPMOAgent
        agent = MiniCPMOAgent(); tag = "minicpmo"

    modes = ["memory", "clip30", "long5m"] if a.mode == "all" else [a.mode]
    tag = tag if a.bench == "chains.json" else f"{tag}_{a.bench.replace('chains_','').replace('.json','')}"
    outdir = C.OUT / tag
    (outdir / "logs").mkdir(parents=True, exist_ok=True)

    for mode in modes:
        shard = outdir / f"chains_{mode}.jsonl"
        done = set()
        if shard.exists():
            done = {json.loads(l)["chain_id"] for l in shard.open() if l.strip()}
        t0 = time.time()
        for c in chains:
            if c["chain_id"] in done:
                continue
            r = run_chain(agent, c, ix, mode, propagate=a.propagate)
            with shard.open("a") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            (outdir / "logs" / f"{c['chain_id']}_{mode}.json").write_text(
                json.dumps(r, ensure_ascii=False, indent=1))
            ok = sum(t["correct"] for t in r["turns"])
            print(f"  [{mode}] {c['chain_id']}  depth={r['depth']}  对 {ok}/{len(c['steps'])}", flush=True)
        print(f"[{tag}/{mode}] 完成，用时 {time.time()-t0:.0f}s -> {shard}")


if __name__ == "__main__":
    main()
