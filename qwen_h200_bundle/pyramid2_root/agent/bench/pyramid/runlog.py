"""运行留档:控制台输出同时写进文件,Gemini 原始调用逐条追加 jsonl。

控制台日志:logs/<tag>_<ts>.log —— 终端照常显示,同时落盘。
Gemini 调用:logs/gemini_calls.jsonl —— 每次调用一行,含完整 prompt 与原始回复,
             失败与重试也记。出题器写了什么、闸门为什么拒,事后全查得到。
"""
import sys, time, json, hashlib
import pconfig as P


def logs_dir(sub=""):
    d = P.LOGROOT / sub if sub else P.LOGROOT
    d.mkdir(parents=True, exist_ok=True)
    return d


class _Tee:
    """同时写终端与文件。缺失属性(encoding/fileno/isatty)一律代理给原流,
    否则第三方库探测 stdout 能力时会炸。"""

    def __init__(self, stream, fh):
        self._s, self._f = stream, fh

    def write(self, s):
        self._s.write(s)
        try:
            self._f.write(s)
        except ValueError:
            pass
        return len(s)

    def flush(self):
        self._s.flush()
        try:
            self._f.flush()
        except ValueError:
            pass

    def __getattr__(self, name):
        return getattr(self._s, name)


def start(tag, agent=None):
    """把 stdout/stderr 同时写到 logs/<agent>/<tag>_<ts>.log。返回日志路径。
    agent 为空时归到 orchestrate/ 子目录。"""
    ts = time.strftime("%Y%m%d-%H%M%S")
    tag = tag if P.SEED == 42 else f"{tag}_seed{P.SEED}"
    path = logs_dir(agent or "orchestrate") / f"{tag}_{ts}.log"
    fh = open(path, "a", buffering=1)
    sys.stdout = _Tee(sys.stdout, fh)
    sys.stderr = _Tee(sys.stderr, fh)
    print(f"[runlog] {time.strftime('%F %T')} argv={' '.join(sys.argv)}", flush=True)
    print(f"[runlog] 记录到 {path}", flush=True)
    return path


def _as_text(prompt):
    """视频档的 contents 是 [File, text] 列表 —— 转成可记录的文本,
    File 记成 file:<uri>。不这么做,_log 的 try/except 会把整条记录静默吞掉。"""
    if isinstance(prompt, str):
        return prompt
    parts = []
    for x in prompt if isinstance(prompt, (list, tuple)) else [prompt]:
        if isinstance(x, str):
            parts.append(x)
        elif getattr(x, "inline_data", None) is not None:
            # 内联媒体(NV 后端没有 Files API):只记类型与字节数,绝不把 base64 写进日志
            d = x.inline_data
            parts.append(f"<inline:{d.mime_type},{len(d.data or b'')}B>")
        else:
            parts.append(f"<file:{getattr(x, 'uri', None) or getattr(x, 'name', x)}>")
    return "\n".join(parts)


def gemini_call(prompt, response, model, latency, error=None, meta=None):
    """给 gemini_io 用:一次调用一行。prompt 与 response 全文保留。"""
    prompt = _as_text(prompt)
    rec = {"ts": time.strftime("%FT%T"), "model": model,
           "latency_sec": round(latency, 2),
           "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12],
           "prompt_chars": len(prompt), "error": error,
           "prompt": prompt, "response": response, **(meta or {})}
    # 出题器与被评测 agent 的调用分开存:前者归 generator/,后者归该 agent 名下
    role = (meta or {}).get("role")
    sub = {"agent": "gemini", "judge": "judge"}.get(role, "generator")
    with (logs_dir(sub) / "gemini_calls.jsonl").open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
