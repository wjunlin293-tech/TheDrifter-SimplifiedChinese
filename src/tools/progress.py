"""实时进度条：每 2 秒刷新一次，读取 batch.py status 的结果。

用法（在另一个终端窗口）：
    python tools/progress.py
按 Ctrl+C 退出。
"""
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIDTH = 40


def read_status():
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "batch.py"), "status"],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
        env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
    ).stdout
    m = re.search(r"(\d+)\s*/\s*(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else None


def main():
    start = time.time()
    first = None
    while True:
        st = read_status()
        if st:
            done, total = st
            if first is None:
                first = done
            pct = done / total
            filled = int(WIDTH * pct)
            bar = "█" * filled + "░" * (WIDTH - filled)
            mins = (time.time() - start) / 60
            line = f"\r汉化进度 [{bar}] {pct*100:5.1f}%  {done}/{total}  剩余 {total-done}  本次新增 {done-first}  ({mins:.0f} 分钟)"
            sys.stdout.write(line)
            sys.stdout.flush()
            if done >= total:
                print("\n全部完成！")
                return
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
