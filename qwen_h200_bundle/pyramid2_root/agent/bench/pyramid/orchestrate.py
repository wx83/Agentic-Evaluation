"""臂驱动器:逐层 生成 -> 校准 -> 评测 -> 摘要 -> 闸门。

三臂:
- shared_l1 : L1 一套共享题全体都答;L2+ 各 agent 用自己的错误画像单独出题。
- per_agent : 每层都按 agent 单独出题(L1 无条件,与共享 L1 只差采样种子)。
- pooled    : 一座金字塔全体共用;L(k+1) 的生成要等所有存活 agent 的 L(k) 结果
              (同步屏障);某 agent 淘汰后只以幸存者为条件,淘汰者分数冻结。

评测用 subprocess 分发到各自的 conda 解释器(gemini 环境 / timechatcap 环境)。
每套题先跑 mock_oracle(必须 100%)与 mock random(记录校准值)再给真 agent。
"""
import json, subprocess, argparse, sys
from pathlib import Path
import pconfig as P
import assemble, adapt, evaluate

HERE = Path(__file__).resolve().parent


def _state_path(arm):
    return P.STATE / f"{arm}.json"


def _load_state(arm, agents):
    f = _state_path(arm)
    if f.exists():
        st = json.loads(f.read_text())
        # 允许分批加入 agent(视频档下 gemini 2s/题、qwen 60s/题,必须分开跑):
        # 没跑过的补进 survivors;已经止步的保持止步。
        for ag in agents:
            if ag not in st["agents"]:
                st["agents"].append(ag)
                if ag not in st["stopped"]:
                    st["survivors"].append(ag)
        return st
    return {"agents": list(agents), "survivors": list(agents), "stopped": {}, "levels": {}}


def _save_state(arm, st):
    P.ensure_dirs()
    _state_path(arm).write_text(json.dumps(st, ensure_ascii=False, indent=1))


def _scopes(arm, level, survivors):
    """该层需要哪些 (scope, 答题的 agents)。"""
    if arm == "pooled":
        return [("pooled", survivors)]
    if arm == "shared_l1" and level == 1:
        return [("shared", survivors)]
    return [(ag, [ag]) for ag in survivors]


def _prev_scope(arm, scope, level):
    """上一层的 set 在哪个 scope 下(shared_l1 的 L2 要回看共享的 L1)。"""
    if arm == "shared_l1" and level == 2:
        return "shared"
    return scope


SELECT_SUFFIX = {"program": "", "gemini": "_cur", "heuristic": "_heur"}


def _key(arm, mode, select="program"):
    """每个输入档 × 选材方式独立成闭环:题套、结果、摘要、状态全部按
    <arm>[_<mode>][_cur|_heur] 分开存,互不覆盖,同一 seed 下可直接 A/B。
    memory 档 + program 选材保持裸 arm,已发表的结果路径不变。"""
    return (arm if mode == "memory" else f"{arm}_{mode}") + SELECT_SUFFIX[select]


def _results_path(arm, agent, level, mode="memory", select="program"):
    return P.RESULTS / _key(arm, mode, select) / agent / f"L{level}.jsonl"


def _summary_for(arm, scope, level, agents, mode="memory", select="program"):
    """构建(或读取)以 L(level-1) 结果为条件的摘要。scope=agent 时只用该 agent 的结果。

    路径全部走 _key(arm, mode) —— 摘要必须由**本档自己**上一层的作答生成,
    否则 clip30 会去读根本不存在的 memory 结果。
    """
    akey = _key(arm, mode, select)
    f = P.ADAPT / akey / scope / f"L{level - 1}_summary.json"
    if f.exists():
        return json.loads(f.read_text())
    ps = _prev_scope(arm, scope, level)
    set_path = P.SETS / akey / ps / f"L{level - 1}.json"
    res = {ag: _results_path(arm, ag, level - 1, mode, select) for ag in agents}
    res = {ag: p for ag, p in res.items() if p.exists()}
    assert res, f"缺少 L{level-1} 结果,无法为 {akey}/{scope}/L{level} 出题"
    return adapt.build_summary(akey, scope, level - 1, set_path, res)


def _calibrate(akey, scope, level, set_path, limit):
    setdata = json.loads(open(set_path).read())
    cdir = P.STATE / "calib" / akey
    cdir.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in ("mock_oracle", "mock"):
        jl = cdir / f"{scope}_L{level}_{name}.jsonl"
        c, n, _ = evaluate.run_set(evaluate.make_agent(name), name, setdata, jl, limit=limit)
        out[name] = {"n_correct": c, "n": n}
    assert out["mock_oracle"]["n_correct"] == out["mock_oracle"]["n"], \
        f"mock_oracle 未达 100% —— 题目结构有 bug,停:{set_path}"
    return out


def run_arm(arm, agents, offline=False, limit=0, skip_calib=False, mode="memory",
            no_gate=False, select="program"):
    akey = _key(arm, mode, select)
    st = _load_state(akey, agents)
    if no_gate:
        # 不设闸门时「止步」本就不该生效:把此前被闸门淘汰的 agent 放回来,
        # 好把缺的层补齐(每层独立准确率才是视频档的指标)。
        for ag in agents:
            st["stopped"].pop(ag, None)
            if ag not in st["survivors"]:
                st["survivors"].append(ag)
    for level in (k for _, k in P.LEVELS):
        survivors = [ag for ag in st["survivors"] if ag in agents]
        if not survivors:
            print(f"[{arm}] 无存活 agent,金字塔在 L{level} 前结束", flush=True)
            break
        print(f"[{arm}/{mode}] === L{level} (存活: {survivors}) ===", flush=True)
        lv = st["levels"].setdefault(str(level), {})
        for scope, scope_agents in _scopes(arm, level, survivors):
            summary = None
            if level > 1:
                cond = survivors if scope in ("pooled", "shared") else [scope]
                summary = _summary_for(arm, scope, level, cond, mode, select)
            # 每个档自己出题、自己自适应。原先 clip30 复用 memory 的题套,是为了让
            # memory - clip30 的落差干净可归因;现在只跑 clip30,那条约束只剩负担 ——
            # 而且出题本就该按「看视频的模型错在哪」自适应,不是按读文本的模型。
            set_path = assemble.build_set(akey, scope, level, summary=summary,
                                          offline=offline, n_target=limit or None,
                                          select=select)
            rec = lv.setdefault(scope, {"set": str(set_path)})
            if not skip_calib and "calib" not in rec:
                rec["calib"] = _calibrate(akey, scope, level, set_path, limit)
                _save_state(akey, st)
            for ag in scope_agents:
                out = _results_path(arm, ag, level, mode, select)
                interp = P.AGENT_INTERPRETER.get(ag, sys.executable)
                cmd = [interp, str(HERE / "evaluate.py"), "--agent", ag,
                       "--questions", str(set_path), "--out", str(out),
                       "--mode", mode]
                if limit:
                    cmd += ["--limit", str(limit)]
                print(f"  [{arm}/{mode}] eval {ag} L{level} ...", flush=True)
                r = subprocess.run(cmd, cwd=str(HERE))
                assert r.returncode == 0, f"evaluate 失败: {ag} L{level}"
                rows = [json.loads(l) for l in out.open() if l.strip()]
                ans = [x for x in rows if not x.get("error")]
                c, n, n_err = sum(x["correct"] for x in ans), len(ans), len(rows) - len(ans)
                rec.setdefault("per_agent", {})[ag] = {"n_correct": c, "n": n,
                                                       "n_error": n_err}
                # API 故障不是「答错」。报错超过 10% 时分数不可解读,停下让人处理,
                # 而不是让 agent 被配额问题淘汰出金字塔。
                assert n and n_err <= 0.1 * (n + n_err), \
                    f"{ag} L{level}: {n_err} 题 API 报错(共 {n + n_err}),先查配额再续跑"
                gate = adapt._gate(n)
                # no_gate:答不过也继续下一层。视频档下两个 agent 都会卡在 L1,
                # 停止层级全为 0 就没有区分度了 —— 这时每层的独立准确率才是指标
                # (0830 的「兵分两路」同一思路:让每层都有完整 n=100 样本)。
                if c < gate and no_gate:
                    print(f"  [{arm}/{mode}] {ag} 未过 L{level} ({c}/{n} < {gate}),"
                          f"但 --no-gate,继续下一层", flush=True)
                    st.setdefault("failed_at", {}).setdefault(ag, level)
                elif c < gate:
                    print(f"  [{arm}] {ag} 在 L{level} 止步 ({c}/{n} < {gate})", flush=True)
                    st["survivors"] = [x for x in st["survivors"] if x != ag]
                    st["stopped"][ag] = level
                else:
                    print(f"  [{arm}] {ag} 通过 L{level} ({c}/{n})", flush=True)
                _save_state(akey, st)
    _save_state(akey, st)
    print(f"[{arm}/{mode}] 完成。stopped={st['stopped']}", flush=True)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=P.ARMS)
    ap.add_argument("--agents", default="gemini,qwen",
                    help="逗号分隔;冒烟测试可用 mock / mock_oracle")
    ap.add_argument("--offline", action="store_true", help="措辞用模板,不调 Gemini")
    ap.add_argument("--limit", type=int, default=0, help="每套题数(冒烟测试用小值)")
    ap.add_argument("--skip-calib", action="store_true")
    ap.add_argument("--mode", default="memory", choices=P.MODES,
                    help="memory=标注文本;clip30=同窗口的 30 秒视频(复用同一批题)")
    ap.add_argument("--no-gate", action="store_true",
                    help="不因未过 80%% 而终止,跑满四层(视频档下取每层独立准确率)")
    ap.add_argument("--select", default="gemini", choices=P.SELECT_MODES,
                    help="选材:gemini=按层间 memory 由 Gemini 挑题(--offline 时退为启发式);"
                         "heuristic=题族加权启发式;program=原加权抽样(复现旧结果)")
    a = ap.parse_args()
    import runlog
    runlog.start(f"orchestrate_{a.arm}_{a.mode}_{a.select}")   # -> logs/orchestrate/
    run_arm(a.arm, a.agents.split(","), offline=a.offline, limit=a.limit,
            skip_calib=a.skip_calib, mode=a.mode, no_gate=a.no_gate, select=a.select)


if __name__ == "__main__":
    main()
