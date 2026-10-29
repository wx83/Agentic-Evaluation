"""把 timeline 窗口渲染成 memory 档的文本。必须与出题器共用同一套措辞映射。"""
import config as C


def render(ix, t0, t1, max_lines=250):
    rows = []
    for e in ix.in_window(t0, t1):
        a, b = max(0.0, e.t_start - t0), min(t1 - t0, e.t_end - t0)
        if e.source == "sound":
            if e.label in C.SKIP_SOUNDS:
                continue
            rows.append((a, b, "SOUND", C.SOUND_PHRASE.get(e.label, e.label)))
        elif e.source == "narration":
            rows.append((a, b, "ACTION", f"{e.text}  [{e.label}]"))
        else:
            fr = ix.fixture_pretty(e.extra.get("from_fixture")) or "somewhere"
            to = ix.fixture_pretty(e.extra.get("to_fixture")) or "somewhere"
            nm = e.extra.get("object_name", e.text)
            rows.append((a, b, "MOVE", f"{nm}: {fr} -> {to}"))
    rows.sort()
    trunc = len(rows) > max_lines
    rows = rows[:max_lines]
    head = (f"MEMORY (annotation-derived) for a {t1-t0:.0f} s clip. "
            f"Times are seconds from the start of the clip.\n")
    body = "\n".join(f"[{a:6.1f}-{b:6.1f}] {k:6s} {txt}" for a, b, k, txt in rows)
    return head + body, {"lines": len(rows), "truncated": trunc}


def contains_gold(text, answer):
    return answer.lower() in text.lower()
