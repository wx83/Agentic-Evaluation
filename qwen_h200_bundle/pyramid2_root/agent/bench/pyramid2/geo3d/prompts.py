"""每条样本写 sam3/prompts.json(= Gemini 4 探针列出的物体名 + hand)。"""
import json, argparse
from . import cfg


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--samples", nargs="*", default=["all"]); a = ap.parse_args()
    for s in cfg.samples(a.samples):
        cd = cfg.clip_dir(s["sample_id"]); (cd / "sam3").mkdir(exist_ok=True)
        names = []
        for o in (s["gemini"].get("objects") or []):
            n = (o.get("name") or "").strip().lower()
            if n and n not in names: names.append(n)
        if "hand" not in names: names.append("hand")
        (cd / "sam3" / "prompts.json").write_text(json.dumps(names)); print(s["scenario"], len(names), names)


if __name__ == "__main__":
    main()
