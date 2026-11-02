"""Qwen3-Omni-30B-A3B-Instruct 本地推理(从 agent/bench/agents/qwen_agent.py 抽出,去掉对仓库 config 的依赖)。
必须 disable_talker + return_audio=False(spk_dict.pt 缺失);多轮中 use_audio_in_video 全程一致。
模型路径:环境变量 QWEN_PATH,或 QwenAgent(path=...)。"""
import time, os, hashlib, subprocess, tempfile, torch

USE_AUDIO_IN_VIDEO = True
_WAVDIR = None


def _patch_audio_backend():
    """qwen_omni_utils 用 audioread.ffdec.FFmpegAudioFile 包视频再交 librosa.load;librosa 1.0 去掉了 audioread 后端 → TypeError。
    这里换成「先用 ffmpeg 抽 16 kHz 单声道 wav」,librosa 走 soundfile 读 wav。需要系统有 ffmpeg。"""
    global _WAVDIR
    import qwen_omni_utils.v2_5.audio_process as ap
    if getattr(ap, "_wav_patched", False):
        return
    _WAVDIR = tempfile.mkdtemp(prefix="qwen_wav_")

    def to_wav(path):
        h = hashlib.sha1(str(path).encode()).hexdigest()[:16]
        out = os.path.join(_WAVDIR, h + ".wav")
        if not os.path.exists(out):
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", out], check=True, capture_output=True)
        return out

    class _Shim:
        FFmpegAudioFile = staticmethod(to_wav)
    ap.audioread.ffdec = _Shim
    ap._wav_patched = True


class QwenSession:
    def __init__(self, agent, media, memory=None):
        self.a, self.conv = agent, []
        self.media, self.memory = media, memory

    def ask(self, text, system=None):
        _patch_audio_backend()
        from qwen_omni_utils import process_mm_info
        content = []
        if not self.conv:
            if system:
                self.conv.append({"role": "system", "content": [{"type": "text", "text": system}]})
            if self.media is not None:
                content.append({"type": "video", "video": str(self.media)})
            elif self.memory:
                content.append({"type": "text", "text": self.memory})
        content.append({"type": "text", "text": text})
        self.conv.append({"role": "user", "content": content})
        p = self.a.processor
        prompt = p.apply_chat_template(self.conv, add_generation_prompt=True, tokenize=False)
        audios, images, videos = process_mm_info(self.conv, USE_AUDIO_IN_VIDEO)
        inputs = p(text=prompt, audio=audios, images=images, videos=videos, return_tensors="pt", padding=True, use_audio_in_video=USE_AUDIO_IN_VIDEO)
        inputs = inputs.to(self.a.model.device).to(self.a.model.dtype)
        t0 = time.time(); torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            ids, _ = self.a.model.generate(**inputs, thinker_return_dict_in_generate=True,
                                           thinker_max_new_tokens=getattr(self.a, "max_new_tokens", None) or 64, thinker_do_sample=False,
                                           use_audio_in_video=USE_AUDIO_IN_VIDEO, return_audio=False)
        n_in = int(inputs["input_ids"].shape[1])
        raw = p.batch_decode(ids.sequences[:, n_in:], skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        meta = {"latency_sec": round(time.time() - t0, 2), "peak_gpu_mb": int(torch.cuda.max_memory_allocated() / 1e6),
                "n_input_tokens": n_in, "n_output_tokens": int(ids.sequences.shape[1] - n_in)}
        self.conv.append({"role": "assistant", "content": [{"type": "text", "text": raw.strip()}]})
        return raw, meta


class QwenAgent:
    name = "qwen"

    def __init__(self, path=None):
        from transformers import Qwen3OmniMoeForConditionalGeneration, Qwen3OmniMoeProcessor
        os.environ.setdefault("FPS_MAX_FRAMES", "600")
        p = path or os.environ.get("QWEN_PATH") or "Qwen/Qwen3-Omni-30B-A3B-Instruct"
        print(f"[qwen] loading {p} ...", flush=True)
        self.model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(p, dtype="auto", device_map="auto")
        self.model.disable_talker()
        self.processor = Qwen3OmniMoeProcessor.from_pretrained(p)
        print(f"[qwen] ready device={self.model.device}", flush=True)

    def start(self, chain=None, media=None, memory=None):
        return QwenSession(self, media, memory)
