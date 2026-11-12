#!/usr/bin/env python3
"""review.py · 成片自审工具（只需要 ffmpeg / ffprobe；Mac、Windows、Linux 都能跑）

用法：
  python3 review.py sheet  <成片> [--every 0.5] [--cols 8]      联络表：每 N 秒一格，格上印秒数
  python3 review.py frames <成片> <秒> [<秒> …]                 原尺寸截帧：一个秒数一张，放大看
  python3 review.py burst  <成片> <起秒> <讫秒> [--every 0.1]   密集连拍：转场 / 3D / 粒子段逐格看
  python3 review.py freeze <成片> [--min 1.0]                   扫定格：连续不动超过 N 秒的段落

产出放在成片旁边的 review/<成片档名>/ 资料夹（每一版各一夹，不会互相盖掉）。看图要用眼睛看（把图读进来），不要只看「跑成功了」。
"""
import argparse
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path


def need(tool):
    if not shutil.which(tool):
        sys.exit(f"找不到 {tool}：请先安装 ffmpeg（里面带 ffprobe）再跑。")


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def duration(video):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(video)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        sys.exit(f"读不到片长：{video}\n{r.stderr.strip()}")


def outdir(video):
    v = Path(video).resolve()
    d = v.parent / "review" / v.stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def grid(video, start, end, every, cols, out, cell_w=270):
    n = max(1, int(math.floor((end - start) / every + 1e-6)) + 1)
    rows = math.ceil(n / cols)
    label = (r"drawtext=text='%{pts\:hms}':x=6:y=6:fontsize=20:"
             "fontcolor=yellow:box=1:boxcolor=black@0.6:boxborderw=4")
    vf = f"fps=1/{every},scale={cell_w}:-2,{label},tile={cols}x{rows}:padding=4:color=0x111111"
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start}", "-t", f"{end - start + every}",
           "-copyts", "-i", str(video), "-vf", vf, "-frames:v", "1", "-q:v", "3", str(out)]
    r = run(cmd)
    if r.returncode != 0:
        # 有些 ffmpeg 没有带字型（drawtext 用不了）：退回不印秒数的版本，并且明讲
        vf = f"fps=1/{every},scale={cell_w}:-2,tile={cols}x{rows}:padding=4:color=0x111111"
        cmd[cmd.index("-vf") + 1] = vf
        r2 = run(cmd)
        if r2.returncode != 0:
            sys.exit(f"出图失败：\n{r.stderr.strip()}\n{r2.stderr.strip()}")
        legend = Path(out).with_suffix(".txt")
        lines = [f"第 {r + 1} 列第 {c + 1} 格 = {start + (r * cols + c) * every:.2f} 秒"
                 for r in range(rows) for c in range(cols) if r * cols + c < n]
        legend.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("⚠️ 这台机器的 ffmpeg 印不了字，格子上没有秒数。"
              f"每一格是第几秒写在 {legend}（第 k 格 = {start} + k × {every} 秒，从 0 数）。")
    print(f"✅ {out}  （{n} 格 · {cols} 栏 × {rows} 列 · 每 {every} 秒一格 · 从 {start:.2f} 到 {end:.2f} 秒）")


def cmd_sheet(a):
    d = duration(a.video)
    grid(a.video, 0, d, a.every, a.cols, outdir(a.video) / "contact-sheet.jpg")
    print("下一步：把这张图读进来逐格看，再用 frames 把每一拍停住的那一帧原尺寸截出来。")


def cmd_frames(a):
    d = duration(a.video)
    od = outdir(a.video)
    for t in a.times:
        if t < 0 or t > d:
            print(f"⚠️ 跳过 {t} 秒：片长只有 {d:.2f} 秒")
            continue
        out = od / f"frame-{t:07.3f}s.png"
        r = run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t}", "-i", str(a.video),
                 "-frames:v", "1", str(out)])
        print(f"✅ {out}" if r.returncode == 0 else f"❌ {t} 秒截不出来：{r.stderr.strip()}")
    print("下一步：一张一张读进来看（原尺寸）。看字有没有贴边、被压到，人物与 3D 物件有没有崩。")


def cmd_burst(a):
    d = duration(a.video)
    s, e = max(0, a.start), min(d, a.end)
    if e <= s:
        sys.exit("讫秒要大于起秒。")
    out = outdir(a.video) / f"burst-{s:06.2f}-{e:06.2f}.jpg"
    grid(a.video, s, e, a.every, a.cols, out, cell_w=360)
    print("下一步：读进来看这一段是不是每一格都在变、物体有没有侧面、有没有哪一格突然缺东西。")


def cmd_freeze(a):
    d = duration(a.video)
    r = run(["ffmpeg", "-v", "info", "-i", str(a.video),
             "-vf", f"freezedetect=n=0.003:d={a.min}", "-map", "0:v:0", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", r.stderr)]
    durs = [float(x) for x in re.findall(r"freeze_duration: ([0-9.]+)", r.stderr)]
    if len(durs) < len(starts):          # 定格一直到片尾：ffmpeg 不印 duration
        durs.append(d - starts[-1])
    if not starts:
        print(f"✅ 没有连续 {a.min} 秒以上完全不动的段落（片长 {d:.2f} 秒）。")
        return
    total = sum(durs)
    print(f"⚠️ 有 {len(starts)} 段连续 {a.min} 秒以上完全不动（共 {total:.1f} 秒 / 片长 {d:.2f} 秒）：")
    for s, du in zip(starts, durs):
        print(f"   {s:6.2f} → {s + du:6.2f} 秒（{du:.2f} 秒）")
    print("逐段判断：是「主体停住让人读、背景本来就不动」可以接受；"
          "还是「该动的东西被冻住了」（影片、角色、镜头）。用 frames / burst 看那一段。")


def main():
    need("ffmpeg")
    need("ffprobe")
    p = argparse.ArgumentParser(description="成片自审工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sheet", help="联络表")
    s.add_argument("video")
    s.add_argument("--every", type=float, default=0.5)
    s.add_argument("--cols", type=int, default=8)
    s.set_defaults(fn=cmd_sheet)

    f = sub.add_parser("frames", help="原尺寸截帧")
    f.add_argument("video")
    f.add_argument("times", type=float, nargs="+")
    f.set_defaults(fn=cmd_frames)

    b = sub.add_parser("burst", help="密集连拍")
    b.add_argument("video")
    b.add_argument("start", type=float)
    b.add_argument("end", type=float)
    b.add_argument("--every", type=float, default=0.1)
    b.add_argument("--cols", type=int, default=8)
    b.set_defaults(fn=cmd_burst)

    z = sub.add_parser("freeze", help="扫定格")
    z.add_argument("video")
    z.add_argument("--min", type=float, default=1.0)
    z.set_defaults(fn=cmd_freeze)

    a = p.parse_args()
    if not Path(a.video).is_file():
        sys.exit(f"找不到成片：{a.video}")
    a.fn(a)


if __name__ == "__main__":
    main()
