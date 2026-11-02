"""确定性 Gemini JSON 生成:temperature 0.0、top_p 0.001、seed 42,多模型回退 + 重试。
参照 object_memory/pipeline/stage_qa_gemini.py 的 gen/jparse(那边顶部 import omcore,不便直接 import)。
"""
import os, json, time
import pconfig as P
import config as C

FATAL = ("PerDay", "RequestsPerDay", "RESOURCE_EXHAUSTED", "429", "NOT_FOUND", "404")
_client = None

# ---- 后端(2026-10-10)----
# GEMINI_BACKEND=nv(默认):走 NVIDIA 网关 https://inference-api.nvidia.com 的 Gemini 原生透传,
#   key 由 gemini/nv_gemini.load_key() 解析(env NVIDIA_API_KEY → 文件),模型名自动加 gcp/google/ 前缀。
#   网关没有 Files API,视频必须内联(agent_gemini.upload 已处理)。
# GEMINI_BACKEND=google:原来的 generativelanguage 直连,key 来自 GEMINI_API_KEY / GOOGLE_API_KEY。
BACKEND = P.BACKEND
_NV_DIR = "/mnt/work_new/weihanxu/gemini"


def _nv():
    import sys
    if _NV_DIR not in sys.path:
        sys.path.insert(0, _NV_DIR)
    import nv_gemini
    return nv_gemini


def model_id(model):
    """按后端规范化模型名:nv 要 gcp/google/ 前缀,google 要去掉。"""
    if BACKEND == "nv":
        return model if model.startswith("gcp/") else "gcp/google/" + model
    return model.split("/")[-1] if model.startswith("gcp/") else model


def client():
    global _client
    if _client is None:
        from google import genai
        from google.genai import types
        # 必须带超时:09-29 00:00 一次请求挂在 socket 上不返回,整条队列卡了 11 小时。
        # 超时抛异常后由 gen / gen_text 的重试循环接住。
        if BACKEND == "nv":
            nv = _nv()
            _client = genai.Client(api_key=nv.load_key(),
                                   http_options=types.HttpOptions(base_url=nv.BASE_URL, api_version="v1beta",
                                                                  timeout=120_000))
        else:
            # GEMINI_API_KEY_FILE=path:进程内读文件,key 不经过 shell / 不进命令行
            kf = os.environ.get("GEMINI_API_KEY_FILE")
            if kf and not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = open(kf).read().strip()
            assert os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"), \
                "请先 export GEMINI_API_KEY=... 或 GEMINI_API_KEY_FILE=path;或 GEMINI_BACKEND=nv 走 NVIDIA"
            _client = genai.Client(http_options=types.HttpOptions(timeout=120_000))
    return _client


def key_id():
    """当前 key 的指纹(sha256 前 8 位),用来按 key 统计用量;key 本身绝不落盘。"""
    import hashlib
    if BACKEND == "nv":
        try:
            return _nv().key_id()
        except Exception:
            return None
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    return hashlib.sha256(k.encode()).hexdigest()[:8] if k else None


def usage(r):
    """response.usage_metadata -> token 计数(字段缺失记 None)。"""
    u = getattr(r, "usage_metadata", None)
    g = lambda k: getattr(u, k, None) if u is not None else None
    return {"tok_in": g("prompt_token_count"), "tok_out": g("candidates_token_count"),
            "tok_think": g("thoughts_token_count"), "tok_total": g("total_token_count"),
            "model_version": getattr(r, "model_version", None)}


def _log(prompt, response, model, latency, error, meta):
    """留档不能反过来把主流程搞挂。"""
    meta = {**(meta or {}), "key_id": key_id(), "backend": BACKEND}
    try:
        import runlog
        runlog.gemini_call(prompt, response, model, latency, error, meta)
    except Exception:
        pass


def gen(prompt, max_tokens=8192, model=None, role=None):
    """返回 (text, model_id)。全模型全重试失败则抛 RuntimeError。role="judge" 时用量单独归档。"""
    from google.genai import types
    models = [model_id(m) for m in [model or C.GEMINI_MODEL]
              + [m for m in C.GEMINI_FALLBACKS if m != (model or C.GEMINI_MODEL)]]
    last = None
    for mid in models:
        # flash 系是 thinking 模型,思考 token 会吃掉 max_output_tokens 配额
        # (实测 256 token 只吐出 '[1, ' 就 MAX_TOKENS)。出题是数据不是散文,关掉。
        # 个别模型不允许 thinking_budget=0,报错后去掉该配置重试。
        use_thinking_off = True
        for attempt in range(4):
            t0 = time.time()
            try:
                kw = dict(temperature=0.0, top_p=0.001, seed=P.SEED,
                          max_output_tokens=max_tokens,
                          response_mime_type="application/json")
                if use_thinking_off:
                    kw["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                r = client().models.generate_content(
                    model=mid, contents=prompt,
                    config=types.GenerateContentConfig(**kw))
                fin = str(getattr(r, "candidates", None) and r.candidates[0].finish_reason)
                _log(prompt, r.text, mid, time.time() - t0,
                     None if r.text else f"empty ({fin})",
                     {"attempt": attempt, "finish_reason": fin,
                      "thinking_off": use_thinking_off, "role": role, **usage(r)})
                if r.text:
                    return r.text, mid
                last = RuntimeError(f"empty response ({fin})")
            except Exception as e:
                last = e
                _log(prompt, None, mid, time.time() - t0, f"{type(e).__name__}: {str(e)[:300]}",
                     {"attempt": attempt, "thinking_off": use_thinking_off, "role": role})
                if use_thinking_off and "thinking" in str(e).lower():
                    use_thinking_off = False
                    continue
                if any(f in str(e) for f in FATAL):
                    print(f"  [gemini_io] {mid}: {str(e)[:80]} -> 下一个模型", flush=True)
                    break
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"all Gemini models failed: {last}")


def gen_text(prompt, max_tokens=256, model=None):
    """纯文本版(不强制 JSON mime),给被评测的 gemini agent 用。
    同样关 thinking —— 否则 3.5-flash 会把输出配额烧在思考上返回空,
    静默回退到 flash-lite,分数就归属不到单一模型了。"""
    from google.genai import types
    mid0 = model_id(model or C.GEMINI_MODEL)
    # GEMINI_THINKING=on:不关 thinking;思考 token 计入 max_output_tokens,所以把上限放大到 4096
    think_on = P.AGENT_THINKING
    if think_on:
        max_tokens = max(max_tokens, 4096)
    # 被评测的 agent **不回退**到别的模型:09-29 免费档 key 配额用尽(429)后,212 道题被
    # gemini-3.1-flash-lite 静默代答,分数就不是同一个模型的了。宁可报错、续跑时重试。
    models = [mid0]
    last = None
    for mid in models:
        use_thinking_off = not think_on
        for attempt in range(3):
            t0 = time.time()
            try:
                kw = dict(temperature=0.0, top_p=0.001, seed=P.SEED,
                          max_output_tokens=max_tokens)
                if use_thinking_off:
                    kw["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                r = client().models.generate_content(
                    model=mid, contents=prompt,
                    config=types.GenerateContentConfig(**kw))
                fin = str(getattr(r, "candidates", None) and r.candidates[0].finish_reason)
                _log(prompt, r.text, mid, time.time() - t0,
                     None if r.text else f"empty ({fin})",
                     {"role": "agent", "attempt": attempt, "finish_reason": fin,
                      "thinking_off": use_thinking_off, **usage(r)})
                if r.text:
                    return r.text, mid
                last = RuntimeError(f"empty response ({fin})")
            except Exception as e:
                last = e
                _log(prompt, None, mid, time.time() - t0,
                     f"{type(e).__name__}: {str(e)[:300]}",
                     {"role": "agent", "attempt": attempt})
                if use_thinking_off and "thinking" in str(e).lower():
                    use_thinking_off = False
                    continue
                if any(f in str(e) for f in FATAL):
                    break
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"all Gemini models failed: {last}")


def jparse(text):
    """解析 JSON;截断的数组砍回最后一个完整的 '},' 抢救。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        i = text.rfind("},")
        if text.lstrip().startswith("[") and i > 0:
            try:
                return json.loads(text[:i + 1] + "]")
            except json.JSONDecodeError:
                pass
        return None
