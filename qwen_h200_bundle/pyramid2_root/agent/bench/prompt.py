"""MCQ prompt、答案字母解析、时间戳解析。"""
import re

INSTR = ("Select the best answer from the options above.\n"
         "Reply on exactly two lines, nothing else:\n"
         "Answer: <A/B/C/D>\n"
         "Time: <M:SS>   (when in the clip the evidence you used occurs)")


def build(question, options):
    return f"Question: {question}\nOptions:\n" + "\n".join(options) + "\n\n" + INSTR


def score_choice(raw, options):
    """把自由文本答案映射到选项下标。'B. 3.367 s' 和 '3.367 s' 都要能对上。"""
    if not raw:
        return None
    t = raw.strip()
    m = re.search(r"(?im)^\s*answer\s*[:：]\s*([ABCD])\b", t)
    if m:
        return "ABCD".index(m.group(1).upper())
    m = re.match(r"^\s*\(?([ABCD])[\.\)\:]?\s*$", t, re.I)
    if m:
        return "ABCD".index(m.group(1).upper())
    m = re.search(r"(?:answer\s+is\s+|option\s+)\(?([ABCD])\b", t, re.I)
    if m:
        return "ABCD".index(m.group(1).upper())
    m = re.search(r"\b([ABCD])[\.\)](?:\s|$)", t)
    if m:
        return "ABCD".index(m.group(1).upper())
    # 退回文本匹配选项正文
    body = [o[3:].strip().lower() for o in options]
    low = t.lower()
    hits = [i for i, b in enumerate(body) if b and b in low]
    if len(hits) == 1:
        return hits[0]
    m = re.search(r"(?im)^\s*answer\s*[:：]\s*(.+)$", t)
    if m:
        a = m.group(1).strip().lower()
        for i, b in enumerate(body):
            if b and (a == b or b in a):
                return i
    return None


def parse_time(raw):
    """接受 2:47 / 167s / 167。返回秒。"""
    if not raw:
        return None
    m = re.search(r"(?im)^\s*time\s*[:：]\s*(.+)$", raw)
    seg = m.group(1) if m else raw
    m = re.search(r"(\d{1,2}):(\d{2})", seg)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*s", seg, re.I) or re.search(r"\b(\d+(?:\.\d+)?)\b", seg)
    return float(m.group(1)) if m else None
