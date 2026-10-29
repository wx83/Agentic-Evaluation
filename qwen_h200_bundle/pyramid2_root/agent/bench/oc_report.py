"""八层链的逐层汇总。report.py 写死了四层，这里单独出一份。"""
import json, sys, glob, os
import config as C

def load(tag, mode):
    p = C.OUT / tag / f"chains_{mode}.jsonl"
    if not p.exists():
        return None
    return [json.loads(l) for l in p.open() if l.strip()]

def main():
    bench = json.loads((C.SHARED / "chains_oc.json").read_text())
    tiers = [s["tier"] for s in bench["chains"][0]["steps"]]
    rows = []
    for tag in sorted(os.listdir(C.OUT)):
        if not tag.endswith("_oc"):
            continue
        for mode in ("episodes", "memory", "clip30", "long5m"):
            rs = load(tag, mode)
            if rs:
                rows.append((tag, mode, rs))
    if not rows:
        print("还没有结果"); return

    print("%-18s %-9s %-6s %s" % ("agent", "mode", "depth", "  ".join("%-5s" % t for t in tiers)))
    print("-" * 96)
    for tag, mode, rs in rows:
        for r in rs:
            marks = []
            for t in r["turns"]:
                marks.append(("✓" if t["correct"] else "✗") + ("i" if t["injected"] else " "))
            marks += ["  "] * (len(tiers) - len(marks))
            print("%-18s %-9s %-6s %s" % (tag, mode, r["depth"], "  ".join("%-5s" % m for m in marks)))

    print()
    for tag, mode, rs in rows:
        r = rs[0]
        print("== %s / %s  depth=%s ==" % (tag, mode, r["depth"]))
        for t in r["turns"]:
            raw = (t["raw_response"] or "").replace("\n", " | ")[:58]
            print("  %-5s %s  gold=%s pred=%s  loc_err=%-8s lat=%-6s  raw: %s" % (
                t["tier"], "✓" if t["correct"] else "✗",
                "ABCD"[t["gold_index"]],
                "ABCD"[t["parsed_index"]] if t["parsed_index"] is not None else "-",
                t["localization_error_sec"], t.get("latency_sec"), raw))
            if t.get("emitted"):
                print("        emit -> %s" % t["emitted"])
        print()

if __name__ == "__main__":
    main()
