"""校验刚写完的批次 -> 生成 CSV -> 装进游戏 -> 导出下一批。

用法：python tools/finish_batch.py work/trans/008_xxx.json [下一批条数，默认400]
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\The Drifter\translation.csv")
PY = sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
MARKERS = [r"\{\d+\}", r"<color[^>]*>", r"</color>", r"\[(?:START|Y|A|B|LB|RB|LT|RT)\]", r"\\n"]


def run(*args):
    r = subprocess.run([PY, *args], capture_output=True, text=True, encoding="utf-8", cwd=ROOT, env=ENV)
    return r.stdout + r.stderr


def main():
    path = ROOT / sys.argv[1]
    nxt = sys.argv[2] if len(sys.argv) > 2 else "400"
    d = json.load(open(path, encoding="utf-8"))
    keys = sorted(int(k) for k in d if not k.startswith("_"))

    src = {}
    todo = ROOT / "work" / "batch_todo.txt"
    for line in open(todo, encoding="utf-8"):
        m = re.match(r"\[(\d+)\] (.*)", line.rstrip("\n"))
        if m:
            src[int(m.group(1))] = m.group(2)

    problems = []
    missing = [i for i in src if i not in d and str(i) not in d]
    extra = [k for k in keys if k not in src]
    if missing:
        problems.append(f"漏译 {len(missing)} 条: {missing[:20]}")
    if extra:
        problems.append(f"多余下标 {len(extra)} 条: {extra[:20]}")
    for k in keys:
        if k not in src:
            continue
        for pat in MARKERS:
            if re.findall(pat, src[k]) != re.findall(pat, d[str(k)]):
                problems.append(f"标记不一致 [{k}] {pat}")
        if not d[str(k)].strip():
            problems.append(f"空译文 [{k}]")
    if problems:
        print("校验失败:")
        print("\n".join(problems[:40]))
        sys.exit(1)
    print(f"校验通过: {len(keys)} 条")

    print(run("tools/make_csv.py").strip().splitlines()[0])
    shutil.copyfile(ROOT / "work" / "translation.csv", GAME)
    print("已装入游戏目录")
    print(run("tools/batch.py", "status").strip().splitlines()[0])
    if nxt != "0":
        print(run("tools/batch.py", "seq", nxt).strip().splitlines()[-1])


if __name__ == "__main__":
    main()
