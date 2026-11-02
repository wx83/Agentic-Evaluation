"""OpenAI examiner: same contract as gemini_io.gen (JSON text, model id), text-only.

The examiner never sees the clip, so any text model can write the questions. Calls are
logged to logs/generator/openai_calls.jsonl (kept apart from gemini_calls.jsonl so
gemini_usage.py stays Gemini-only). The key lives in OPENAI_API_KEY, never on disk.
"""
import os, json, time, hashlib
import pconfig as P
import runlog

MODEL = os.environ.get("OPENAI_EXAMINER_MODEL", "gpt-4o-mini")
_client = None


def client():
    global _client
    if _client is None:
        assert os.environ.get("OPENAI_API_KEY"), "请先 export OPENAI_API_KEY=...(不要写进任何文件)"
        from openai import OpenAI
        _client = OpenAI(timeout=120, max_retries=0)
    return _client


def key_id():
    k = os.environ.get("OPENAI_API_KEY") or ""
    return hashlib.sha256(k.encode()).hexdigest()[:8] if k else None


def _log(prompt, response, model, latency, error, meta):
    try:
        rec = {"ts": time.strftime("%FT%T"), "model": model, "latency_sec": round(latency, 2),
               "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12],
               "prompt_chars": len(prompt), "error": error, "prompt": prompt, "response": response,
               **(meta or {}), "key_id": key_id()}
        with (runlog.logs_dir("generator") / "openai_calls.jsonl").open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def gen(prompt, max_tokens=2048, model=None, role=None):
    """返回 (text, model_id)。不回退到别的模型;全部重试失败则抛 RuntimeError。"""
    mid = model or MODEL
    last = None
    for attempt in range(4):
        t0 = time.time()
        try:
            r = client().chat.completions.create(
                model=mid, messages=[{"role": "user", "content": prompt}],
                temperature=0.0, seed=P.SEED, max_tokens=max_tokens,
                response_format={"type": "json_object"})
            text = r.choices[0].message.content
            u = r.usage
            _log(prompt, text, mid, time.time() - t0, None if text else "empty",
                 {"attempt": attempt, "finish_reason": r.choices[0].finish_reason, "role": role,
                  "tok_in": u.prompt_tokens, "tok_out": u.completion_tokens, "tok_total": u.total_tokens})
            if text:
                return text, mid
            last = RuntimeError("empty response")
        except Exception as e:
            last = e
            _log(prompt, None, mid, time.time() - t0, f"{type(e).__name__}: {str(e)[:300]}",
                 {"attempt": attempt, "role": role})
            if any(s in str(e) for s in ("insufficient_quota", "invalid_api_key", "model_not_found")):
                break
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenAI examiner failed: {last}")
