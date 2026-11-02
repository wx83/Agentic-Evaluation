"""格式题的 mock agent:oracle 按格式答对(校准必须 100%),random 按格式随机(应落在各格式 chance 附近)。
mc 题沿用 bench/agents/mock_agent.py 的行为。"""
import hashlib, random
from agents.base import Session


def _t(st, chain):
    wins = chain.get("windows")
    t = st["evidence_t"] if wins else st["evidence_t"] - chain["clip_start"]
    return f"Time: {int(t)//60}:{int(t)%60:02d}"


class MockFmtSession(Session):
    def __init__(self, oracle, chain):
        self.oracle, self.chain, self.i = oracle, chain, 0

    def ask(self, text):
        st = self.chain["steps"][self.i]; self.i += 1
        fmt = st.get("fmt") or "mc"
        rng = random.Random(int(hashlib.sha256((st["question_id"] + "m").encode()).hexdigest()[:8], 16))
        if fmt == "mc":
            L = st["correct_option"] if self.oracle else "ABCD"[rng.randrange(4)]
            return f"Answer: {L}\n{_t(st, self.chain)}", {"latency_sec": 0.0}
        if fmt == "yn":
            a = st["_yn_truth"] if self.oracle else rng.choice(["yes", "no"])
            return f"Answer: {a}\n{_t(st, self.chain)}", {"latency_sec": 0.0}
        if fmt == "ms":
            if self.oracle:
                a = ", ".join(st["_gold_set"])
            else:
                k = rng.randrange(1, 16)                       # 非空子集均匀
                a = ", ".join(L for i, L in enumerate("ABCD") if k >> i & 1)
            return f"Answer: {a}\n{_t(st, self.chain)}", {"latency_sec": 0.0}
        if fmt in ("tf4", "tf4_x"):
            g = "ABCD"[st["_gold_idx"]]
            lines = [f"{L}: {'true' if (L == g if self.oracle else rng.random() < 0.5) else 'false'}"
                     for L in "ABCD"]
            if fmt == "tf4_x":
                lines.append("Because: mock")
            return "\n".join(lines) + "\n" + _t(st, self.chain), {"latency_sec": 0.0}
        if fmt in ("open", "open_x"):
            a = st["answer"] if self.oracle else rng.choice(st["_distractors"])
            why = "\nBecause: mock" if fmt == "open_x" else ""
            return f"Answer: {a}{why}\n{_t(st, self.chain)}", {"latency_sec": 0.0}
        raise ValueError(fmt)

    def close(self):
        pass


class MockFmtAgent:
    name = "mock_fmt"

    def __init__(self, oracle=False):
        self.oracle = oracle

    def start(self, chain, media=None, memory=None):
        return MockFmtSession(self.oracle, chain)
