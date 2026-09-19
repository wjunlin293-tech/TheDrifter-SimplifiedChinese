"""Batch workflow helpers.

  python batch.py status            - 进度总览
  python batch.py next [N]          - 导出下一批待翻译条目（按剧本文件分组）
  python batch.py file "<name>"     - 导出指定剧本文件的全部条目
"""
import os, sys, json, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import WORK

TRANS_DIR = os.path.join(WORK, "trans")
os.makedirs(TRANS_DIR, exist_ok=True)


def load_all():
    t = json.load(open(os.path.join(WORK, "systemtext.json"), encoding="utf-8"))
    return t["m_strings"]


def load_trans():
    out = {}
    for p in sorted(glob.glob(os.path.join(TRANS_DIR, "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        for k, v in d.items():
            if not k.startswith("_"):
                out[int(k)] = v
    return out


def status(ss, tr):
    done_by_file = collections.Counter()
    total_by_file = collections.Counter()
    for i, s in enumerate(ss):
        total_by_file[s["m_sourceFile"]] += 1
        if i in tr:
            done_by_file[s["m_sourceFile"]] += 1
    pct = len(tr) / len(ss) * 100
    print(f"总进度: {len(tr)} / {len(ss)}  ({pct:.1f}%)")
    remaining = [(f, total_by_file[f] - done_by_file[f]) for f in total_by_file]
    remaining = [(f, n) for f, n in remaining if n > 0]
    remaining.sort(key=lambda x: -x[1])
    print(f"未完成剧本文件: {len(remaining)}  剩余条目: {sum(n for _, n in remaining)}")
    print("\n剩余量最大的 25 个文件:")
    for f, n in remaining[:25]:
        print(f"  {n:5d}  {f}")
    return remaining


def dump(ss, tr, files, out_path):
    lines = []
    n = 0
    for fname in files:
        sel = [(i, s) for i, s in enumerate(ss)
               if s["m_sourceFile"] == fname and i not in tr]
        if not sel:
            continue
        lines.append(f"\n##### FILE: {fname}")
        cur = None
        for i, s in sel:
            if s["m_sourceFunction"] != cur:
                cur = s["m_sourceFunction"]
                lines.append(f"### {cur}")
            ch = s["m_character"]
            txt = s["m_string"].replace("\n", "\\n")
            lines.append(f"[{i}] {('<'+ch+'> ') if ch else ''}{txt}")
            n += 1
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"导出 {n} 条 -> {out_path}  ({os.path.getsize(out_path)/1024:.1f} KB)")
    return n


if __name__ == "__main__":
    ss = load_all()
    tr = load_trans()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        status(ss, tr)
    elif cmd == "next":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        rem = status(ss, tr)
        files = [f for f, _ in rem[:count]]
        print()
        dump(ss, tr, files, os.path.join(WORK, "batch_todo.txt"))
    elif cmd == "file":
        dump(ss, tr, [sys.argv[2]], os.path.join(WORK, "batch_todo.txt"))
    elif cmd == "seq":
        # next K untranslated entries in array order (≈ story order)
        k = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        sel = [(i, s) for i, s in enumerate(ss) if i not in tr][:k]
        lines, cur = [], None
        for i, s in sel:
            key = (s["m_sourceFile"], s["m_sourceFunction"])
            if key != cur:
                cur = key
                lines.append(f"\n##### {key[0]} :: {key[1]}")
            ch = s["m_character"]
            txt = s["m_string"].replace("\n", "\\n")
            lines.append(f"[{i}] {('<'+ch+'> ') if ch else ''}{txt}")
        out = os.path.join(WORK, "batch_todo.txt")
        open(out, "w", encoding="utf-8").write("\n".join(lines))
        print(f"导出 {len(sel)} 条 (下标 {sel[0][0]}..{sel[-1][0]}) -> {out}"
              f"  ({os.path.getsize(out)/1024:.1f} KB)")
