"""单套题的评测:每题新开会话,memory 文本 + MCQ prompt -> 答案字母。
jsonl 以 question_id 为键可续跑;每题存完整 log。
在对应 conda 解释器下运行(gemini 环境跑 gemini,timechatcap 环境跑 qwen)。
"""
import json, time, hashlib, argparse
from pathlib import Path
import pconfig as P
import memory as MEM
import prompt as PR
import score          # 解析包装:补「首行裸字母」,见 score.py
import clips
import formats as FM
from timeline_index import TimelineIndex

_IX = {}


def ix_of(video):
    if video not in _IX:
        _IX[video] = TimelineIndex(video)
    return _IX[video]


def make_agent(name):
    if name in ("mock", "mock_oracle"):
        from agents.mock_agent import MockAgent
        return MockAgent(oracle=(name == "mock_oracle"))
    if name == "gemini":
        # 不用 bench/agents/gemini_agent.py:它没关 thinking,3.5-flash 会返回空
        # 并静默回退到 flash-lite,分数归属不到单一模型(实测 30 题里 26 题如此)
        from agent_gemini import PyramidGeminiAgent
        return PyramidGeminiAgent()
    if name == "qwen":
        from agents.qwen_agent import QwenAgent
        return QwenAgent()
    raise ValueError(name)


def precut(qs, workers=8):
    """先把该套题要用的 30 秒 clip 并行裁好(内容寻址缓存,已存在的直接跳过),
    免得裁剪延迟混进每题的 latency 里。"""
    from concurrent.futures import ThreadPoolExecutor
    wins = sorted({(q["video_id"], q["t0"], q["t1"]) for q in qs if not q.get("windows")})
    todo = [w for w in wins if not clips.clip_path(*w).exists()]
    # 跨场景题:两段 30 s 各自裁好再拼成一条(clips.ensure_episodes)
    eps = sorted({(q["video_id"], tuple(tuple(w) for w in q["windows"])) for q in qs if q.get("windows")})
    todo_ep = [e for e in eps if not clips.episodes_path(e[0], list(e[1])).exists()]
    if not todo and not todo_ep:
        return
    print(f"    裁剪 {len(todo)}/{len(wins)} 个 clip、拼接 {len(todo_ep)}/{len(eps)} 个跨场景片段 ...",
          flush=True)
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda w: clips.ensure_clip(*w), todo))
        list(ex.map(lambda e: clips.ensure_episodes(e[0], [tuple(w) for w in e[1]]), todo_ep))


def muted(path):
    """同一 clip、音轨换成等长静音(不直接去掉音轨:Qwen3-Omni 开着 use_audio_in_video,
    无音轨会在 process_mm_info 里报错)。视频流原样拷贝,只有声音不同。"""
    import subprocess
    path = Path(path)
    out = path.with_name(path.stem + "_mute" + path.suffix)
    if not out.exists():
        import os
        tmp = out.with_name(f"{out.stem}.tmp{os.getpid()}{out.suffix}")   # 并行进程各用各的 tmp
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(path),
                        "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-shortest", str(tmp)], check=True)
        if out.exists():
            tmp.unlink(missing_ok=True)
        else:
            tmp.rename(out)
    return out


def run_set(agent, agent_name, setdata, out_jsonl, limit=0, mode="memory"):
    out_jsonl = Path(out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    logdir = out_jsonl.parent / "logs"
    logdir.mkdir(exist_ok=True)
    done, stale = set(), []
    if out_jsonl.exists():
        for l in out_jsonl.open():
            if not l.strip():
                continue
            r = json.loads(l)
            # 报错的行不算作答:续跑时重试(429/503 不是「答错」)
            if r.get("error"):
                stale.append(r["question_id"])
            else:
                done.add(r["question_id"])
        if stale:
            # 重写 jsonl,剔除待重试的报错行,避免同一题留下两行
            keep = [l for l in out_jsonl.open()
                    if l.strip() and not json.loads(l).get("error")]
            out_jsonl.write_text("".join(keep))
            print(f"  [{agent_name}] 重试上次报错的 {len(stale)} 题", flush=True)
    qs = setdata["questions"][:limit] if limit else setdata["questions"]
    if mode in ("clip30", "clip30_mute") and not all(q.get("clip_path") for q in qs):
        precut([q for q in qs if q["question_id"] not in done])
    n_correct = n = 0
    for q in qs:
        if q["question_id"] in done:
            continue
        ix = ix_of(q["video_id"]) if mode == "memory" else None
        media = memtext = None
        if mode == "blind":
            sha = None             # 盲答:不给视频也不给标注,只有题面与选项
        elif mode == "memory":
            memtext, _ = MEM.render(ix, q["t0"], q["t1"])
            sha = hashlib.sha256(memtext.encode()).hexdigest()[:16]
            assert sha == q["memory_sha"], \
                f"memory 渲染与组卷时不一致 {q['question_id']}: {sha} != {q['memory_sha']}"
        elif q.get("clip_path"):
            media = Path(q["clip_path"])      # 非 HD-EPIC 数据(EPIC-Sounds):题目自带裁好的 clip
            sha = None
        else:
            media = (clips.ensure_episodes(q["video_id"], [tuple(w) for w in q["windows"]])
                     if q.get("windows") else clips.ensure_clip(q["video_id"], q["t0"], q["t1"]))
            if mode == "clip30_mute":
                media = muted(media)
            sha = None
        pseudo_chain = {"steps": [q], "clip_start": q["t0"]}
        fmt = q.get("fmt") if q.get("fmt") not in (None, "mc") else None
        if fmt:
            text = FM.build_prompt(q)
        else:
            text = PR.build(q["question"], q["options"])
        # 格式题按格式设输出上限(open_x 要写解释);agent 没这个属性就用各自默认
        for attr in ("max_tokens", "max_new_tokens"):
            setattr(agent, attr, P.FMT_MAX_TOKENS[fmt] if fmt else None)
        sess = None
        try:
            # start() 里会上传视频;上传偶发 500 INTERNAL(实测 pilot 2 第 31 题)。放进 try:
            # 记为该题的 API 错误、续跑时自动重试,而不是让整个进程退出、后面几层全停。
            sess = agent.start(pseudo_chain, media=media, memory=memtext)
            raw, meta = sess.ask(text)
            err = None
        except Exception as e:
            raw, meta, err = "", {}, f"{type(e).__name__}: {str(e)[:1500]}"  # 别截太短:429 的配额指标名(free_tier 与否)就在后半段
        finally:
            if sess is not None:
                sess.close()
        if fmt:
            parsed, expl = FM.parse(fmt, raw)
            correct, sc, by, detail = FM.score(fmt, parsed, q)
            if err is not None:
                correct, sc, by = False, 0.0, "rule"
            idx = None
            fmt_fields = {"fmt": fmt, "parsed": parsed, "score": sc, "score_by": by,
                          "score_detail": detail, "explanation": expl,
                          "base_id": q.get("base_id"), "_distractors": q["_distractors"]}
        else:
            idx = score.score_choice(raw, q["options"])
            correct = (idx == q["_gold_idx"]) and err is None
            fmt_fields = {}
        row = {"question_id": q["question_id"], "arm": setdata["arm"],
               "scope": setdata["scope"], "level": setdata["level"],
               # 输入档与题面直接写进每一行:事后光看 jsonl 就知道问了什么、用的哪档输入
               "input": mode, "seed": P.SEED,
               "tier": q["tier"], "subtype": q["subtype"],
               "question": q["question"], "answer": q["answer"],
               "options": q["options"], "window": [q["t0"], q["t1"]],
               "media": str(media) if media else None,
               "agent": agent_name, "video_id": q["video_id"],
               "parsed_index": idx, "gold_index": q.get("_gold_idx"),
               "correct": correct, "parsed_time": PR.parse_time(raw),
               "error": err, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **fmt_fields, **meta}
        with out_jsonl.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        (logdir / f"{q['question_id']}.json").write_text(json.dumps(
            {**row, "prompt": text, "memory_sha": sha, "raw_response": raw,
             "memory_text": memtext},
            ensure_ascii=False, indent=1))
        n += 1
        n_correct += bool(correct)
        if n % 10 == 0:
            print(f"    [{agent_name}] {n} 题, 对 {n_correct}", flush=True)
    # 汇总以 jsonl 全量为准(含之前续跑的部分)
    rows = [json.loads(l) for l in out_jsonl.open() if l.strip()]
    ans = [r for r in rows if not r.get("error")]
    n_err = len(rows) - len(ans)
    tot_c = sum(bool(r["correct"]) for r in ans)
    n_pend = sum(r.get("score_by") == "pending" for r in ans)   # open 简答待 judge
    print(f"  [{agent_name}/{mode}] {setdata['arm']}/{setdata['scope']}/L{setdata['level']}: "
          f"{tot_c}/{len(ans)}" + (f"  (另有 {n_err} 题 API 报错,不计入分母)" if n_err else "")
          + (f"  ({n_pend} 题规则无结论,待 judge_formats.py)" if n_pend else ""),
          flush=True)
    return tot_c, len(ans), n_err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True,
                    choices=["gemini", "qwen", "mock", "mock_oracle"])
    ap.add_argument("--questions", required=True, nargs="+",
                    help="题套 json;给多个时 --out 视为目录,每套写 <目录>/<题套文件名>.jsonl(模型只加载一次)")
    ap.add_argument("--out", required=True, help="结果 jsonl 路径(多题套时为目录)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--mode", default="memory", choices=P.MODES)
    a = ap.parse_args()
    import runlog
    runlog.start(f"evaluate_{a.agent}_{a.mode}", agent=a.agent)
    agent = make_agent(a.agent)
    for qp in a.questions:
        setdata = json.loads(open(qp).read())
        out = a.out if len(a.questions) == 1 else str(Path(a.out) / (Path(qp).stem + ".jsonl"))
        print(f"  输入档={a.mode}  题套={qp}", flush=True)
        run_set(agent, a.agent, setdata, out, limit=a.limit, mode=a.mode)


if __name__ == "__main__":
    main()
