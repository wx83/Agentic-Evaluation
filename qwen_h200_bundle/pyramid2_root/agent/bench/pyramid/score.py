"""答案解析的包装层。不改 bench/prompt.py —— 0830 的结果依赖它,改了就不可比。

补一条规则:首行是裸字母(如 "C\nTime: 00:19")。Qwen 在视频档常这么答,
bench 的 score_choice 只认「整串一个字母」或带 Answer:/option 前缀的形式,
多行裸字母会解析成 None,被一律算错 —— 实测 45 题里误杀 6 题(13%)。
"""
import re
import prompt as PR

BARE_FIRST_LINE = re.compile(r"^\s*\(?([ABCD])\)?\s*[\.\):,]?\s*$")


def score_choice(raw, options):
    idx = PR.score_choice(raw, options)
    if idx is not None or not raw:
        return idx
    for line in raw.strip().splitlines():          # 只看首个非空行,避免误抓正文里的字母
        if not line.strip():
            continue
        m = BARE_FIRST_LINE.match(line)
        return "ABCD".index(m.group(1).upper()) if m else None
    return None
