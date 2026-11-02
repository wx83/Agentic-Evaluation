"""金字塔专用的 gemini 被评测 agent。不改 bench/agents/gemini_agent.py
(0830 的结果依赖它,改了就不可比)。

与 bench 版的唯一区别:关掉 thinking。实测 bench 版在本轮 30 题里
26 题落到 gemini-3.1-flash-lite —— 3.5-flash 把 4096 输出配额烧在思考上返回空,
静默走了回退链,分数归属不到单一模型。本轮是纯文本单轮 MCQ,不需要思考预算。
每行结果都记 model,report 会打印模型分布;若出现回退,说明配额或可用性有问题。
"""
import os, time
import config as C
import gemini_io
from agents.base import Session

MAX_TOKENS = 64          # "Answer: B\nTime: 0:14" 足够;短输出也能压住跑题


class PyramidGeminiSession(Session):
    def __init__(self, agent, media, memory):
        self.a, self.memory, self.media = agent, memory, media
        self.uploaded = None
        if media is not None:
            self.uploaded = agent.upload(media)

    def ask(self, text):
        t0 = time.time()
        if self.uploaded is not None:
            # 多模态在前、文本在后(与 0830 的 Qwen 论文设置一致)
            contents = [self.uploaded, "\n" + text + "\n"]
        else:
            contents = "\n".join(([self.memory, ""] if self.memory else []) + [text])
        raw, mid = gemini_io.gen_text(contents, max_tokens=getattr(self.a, "max_tokens", None) or MAX_TOKENS,
                                      model=self.a.model)
        import pconfig as P
        return raw, {"latency_sec": round(time.time() - t0, 2), "model": mid,
                     "thinking": "on" if P.AGENT_THINKING else "off"}

    def close(self):
        # File API 的句柄用完就删,免得配额被上千个 30 秒 clip 占满;内联 Part 没有句柄
        if self.uploaded is not None and getattr(self.uploaded, "name", None):
            try:
                self.a.client().files.delete(name=self.uploaded.name)
            except Exception:
                pass
        self.uploaded = None


class PyramidGeminiAgent:
    name = "gemini"

    def __init__(self, model=None):
        import pconfig as P
        self.model = model or P.AGENT_MODEL      # GEMINI_AGENT_MODEL 可只换作答模型

    def client(self):
        return gemini_io.client()

    def upload(self, path):
        """上传 clip 并等它 ACTIVE。失败重试 3 次 —— 单次上传抖动不该毁掉整题。
        NV 后端没有 Files API(404),或 GEMINI_INLINE_MEDIA=1 时:改为内联 bytes(30 s 288p clip 约 1 MB,
        实测 19 MB 也能过)。"""
        if gemini_io.BACKEND == "nv" or os.environ.get("GEMINI_INLINE_MEDIA"):
            from google.genai import types
            path = str(path)
            mime = "video/mp4" if path.endswith(".mp4") else "audio/wav" if path.endswith(".wav") else "video/mp4"
            return types.Part.from_bytes(data=open(path, "rb").read(), mime_type=mime)
        last = None
        for attempt in range(3):
            try:
                up = self.client().files.upload(file=str(path))
                t0 = time.time()
                while (not up.state) or up.state.name == "PROCESSING":
                    if time.time() - t0 > 180:
                        raise RuntimeError("上传处理超时 180s")
                    time.sleep(2)
                    up = self.client().files.get(name=up.name)
                if up.state.name != "ACTIVE":
                    raise RuntimeError(f"上传状态 {up.state.name}")
                return up
            except Exception as e:
                last = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"clip 上传失败 {path}: {last}")

    def start(self, chain, media=None, memory=None):
        return PyramidGeminiSession(self, media, memory)
