#!/usr/bin/env python3
"""preflight.py · 渲染前审片：只看几张静态截图，不出整支片

先用你的引擎把「静态截图」截出来（不是出片）：每一拍停住的那一刻各一张，
开场与转场每 0.1–0.2 秒一张（字落地、压扁这种一下就过的动作，那半秒要每帧一张）。
档名里要带秒数（例：at-1.5s.png、at-12.25s.png）。截图放一个干净的资料夹：
有些引擎会顺手在同一夹写联络表，档名带 contact / sheet 的本脚本会跳过。
然后：

  python3 preflight.py <截图资料夹> --stops 1.2,4.5,7.0,10.2 \
      [--bursts 0-4,6.8-7.6] [--safe 90,220,90,380] [--out <资料夹>]

  --stops   每一拍主体停住的秒数（照分镜表填）
  --bursts  要看「有没有在动」的区间，起-讫秒；资料夹里这段区间的截图都会用上
  --safe    安全边：左,上,右,下（像素）。不给就用 左右 8%、上 12%、下 20%
  --out     产出放哪（默认：截图资料夹/preflight）

产出：
  stops.jpg        每一拍停住帧并排，画上安全边的框线（框外不该有要读的东西）
  burst-*.jpg      每个区间的连拍
  report.md        机器量到的「提醒」清单

机器量到的都只是提醒，不是判决：它量得出「边上有东西」「两拍长得一样」「这段没在动」，
量不出「好不好看」，也量不出动作够不够大。每一条提醒都要回去看那张图，用眼睛判。
每一拍停住后的 1.2 秒内不动算「故意停住让人读」，不报。

需要 Pillow（没有就：python3 -m pip install pillow）。
"""
import argparse
import math
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageStat
except ImportError:
    sys.exit("需要 Pillow：python3 -m pip install pillow")

TIME_RE = re.compile(r"(\d+(?:\.\d+)?)")
AT_RE = re.compile(r"at-(\d+(?:\.\d+)?)s", re.I)
NOT_STILLS = ("contact", "sheet", "burst", "stops", "pair", "compare")


def load(folder):
    """资料夹里每张图 → (秒数, 路径)，照秒数排。
    认 at-<秒>s 这种档名；没有这种档名时才退回「档名里最后一个数字」。
    联络表、并排图这类不是单张截图的档（档名带 contact / sheet…）一律跳过。"""
    files = [p for p in sorted(Path(folder).iterdir())
             if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
             and not any(w in p.stem.lower() for w in NOT_STILLS)]
    out = [(float(m.group(1)), p) for p in files if (m := AT_RE.search(p.stem))]
    if not out:
        out = [(float(n[-1]), p) for p in files if (n := TIME_RE.findall(p.stem))]
    seen, uniq = set(), []
    for t, p in sorted(out):
        if round(t, 3) not in seen:
            seen.add(round(t, 3))
            uniq.append((t, p))
    return uniq


def nearest(stills, t, tol=0.051):
    best = min(stills, key=lambda s: abs(s[0] - t), default=None)
    return best if best and abs(best[0] - t) <= tol else None


def small(img, w=96):
    h = max(1, round(img.height * w / img.width))
    return img.convert("L").resize((w, h))


def diff(a, b):
    """两张图差多少：0 = 一样，255 = 全反。先缩小再比，对压缩杂讯不敏感。"""
    return ImageStat.Stat(ImageChops.difference(small(a), small(b))).mean[0]


def bg_color(img):
    """底色：缩小后出现最多的颜色。"""
    s = img.convert("RGB").resize((64, 114)).quantize(8).convert("RGB")
    return max(s.getcolors(64 * 114), key=lambda c: c[0])[1]


def busy_ratio(img, box, bg, thr=38):
    """box 里有多少比例的像素明显不是底色（缩小后量）。"""
    crop = img.convert("RGB").crop(box)
    if crop.width < 2 or crop.height < 2:
        return 0.0
    crop = crop.resize((max(2, crop.width // 6), max(2, crop.height // 6)))
    raw = crop.tobytes()
    total = len(raw) // 3
    n = sum(1 for i in range(0, len(raw), 3)
            if abs(raw[i] - bg[0]) + abs(raw[i + 1] - bg[1]) + abs(raw[i + 2] - bg[2]) > thr)
    return n / total


def sheet(items, out, cell_w, cols, safe=None):
    """items: [(标签, PIL 图)] → 并排图。safe 给了就画安全边框线。"""
    if not items:
        return
    w0, h0 = items[0][1].size
    cell_h = round(h0 * cell_w / w0)
    rows = math.ceil(len(items) / cols)
    pad, head = 8, 26
    canvas = Image.new("RGB", (cols * (cell_w + pad) + pad, rows * (cell_h + head + pad) + pad), (17, 17, 17))
    d = ImageDraw.Draw(canvas)
    for i, (label, img) in enumerate(items):
        x = pad + (i % cols) * (cell_w + pad)
        y = pad + (i // cols) * (cell_h + head + pad)
        d.text((x + 2, y + 6), label, fill=(255, 214, 10))
        thumb = img.convert("RGB").resize((cell_w, cell_h))
        if safe:
            k = cell_w / w0
            l, t, r, b = safe
            td = ImageDraw.Draw(thumb)
            td.rectangle([l * k, t * k, cell_w - r * k, cell_h - b * k], outline=(255, 59, 48), width=2)
        canvas.paste(thumb, (x, y + head))
    canvas.save(out, quality=88)


def main():
    ap = argparse.ArgumentParser(description="渲染前审片：只看静态截图")
    ap.add_argument("folder")
    ap.add_argument("--stops", required=True)
    ap.add_argument("--bursts", default="")
    ap.add_argument("--safe", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    stills = load(a.folder)
    if not stills:
        sys.exit(f"{a.folder} 里没有档名带秒数的截图。")
    out = Path(a.out) if a.out else Path(a.folder) / "preflight"
    out.mkdir(parents=True, exist_ok=True)
    W, H = Image.open(stills[0][1]).size
    safe = [int(x) for x in a.safe.split(",")] if a.safe else [round(W * .08), round(H * .12), round(W * .08), round(H * .20)]
    L, T, R, B = safe
    notes, lines = [], [f"# 渲染前审片 · 机器量到的提醒\n", f"画布 {W}×{H} · 安全边 左 {L} 上 {T} 右 {R} 下 {B}\n"]

    # ── 停住帧 ──
    stops, missing = [], []
    for t in [float(x) for x in a.stops.split(",") if x.strip()]:
        hit = nearest(stills, t)
        (stops.append((t, Image.open(hit[1]))) if hit else missing.append(t))
    if missing:
        notes.append(f"缺截图：停住点 {missing} 秒在资料夹里找不到对应的图（±0.05 秒）。补截再跑。")
    sheet([(f"{t:g}s", im) for t, im in stops], out / "stops.jpg", 300, min(6, max(1, len(stops))), safe)

    lines.append("\n## 每一拍停住帧\n\n| 秒 | 左边 | 右边 | 上方 | 下方 | 主区有东西的比例 |\n|---|---|---|---|---|---|")
    for t, im in stops:
        bg = bg_color(im)
        bands = {"左边": (0, T, L, H - B), "右边": (W - R, T, W, H - B), "上方": (0, 0, W, T), "下方": (0, H - B, W, H)}
        r = {k: busy_ratio(im, v, bg) for k, v in bands.items()}
        main_r = busy_ratio(im, (L, T, W - R, H - B), bg)
        lines.append(f"| {t:g} | {r['左边']:.0%} | {r['右边']:.0%} | {r['上方']:.0%} | {r['下方']:.0%} | {main_r:.0%} |")
        for k in ("左边", "右边"):
            if r[k] > 0.03:
                notes.append(f"{t:g} 秒：{k}安全边里有东西（{r[k]:.0%}）。看 stops.jpg 那一格：是会被读的字、还是故意出血的背景 / 前景？")
        for k in ("上方", "下方"):
            if r[k] > 0.10:
                notes.append(f"{t:g} 秒：{k}会被平台介面盖住的区域里有东西（{r[k]:.0%}）。确认里面没有要读的字。")
        low_r = busy_ratio(im, (L, (T + H - B) // 2, W - R, H - B), bg)
        if main_r >= 0.06 and low_r < 0.02:
            notes.append(f"{t:g} 秒：主区下半几乎是空的（{low_r:.0%}）。主视觉有没有往下长到够？")
        if main_r < 0.06:
            notes.append(f"{t:g} 秒：主区只有 {main_r:.0%} 有东西，画面可能太空（少了远景 / 前景 / 资讯层？），或主角太小。")
    for (t1, a1), (t2, a2) in zip(stops, stops[1:]):
        dv = diff(a1, a2)
        if dv < 6:
            notes.append(f"{t1:g} 秒与 {t2:g} 秒两拍的画面几乎一样（差 {dv:.1f}）。这两拍是不是同一个版面只换了字？做法有没有换？")

    # ── 连拍区间 ──
    stop_times = [t for t, _ in stops]

    def held(t1, t2):
        """这一格落在某一拍停住之后的 1.2 秒内：算故意停住让人读，不算死掉。"""
        return any(st - 0.15 <= t1 and t2 <= st + 1.2 for st in stop_times)

    for spec in [s for s in a.bursts.split(",") if s.strip()]:
        s0, s1 = [float(x) for x in spec.split("-")]
        seg = [(t, Image.open(p)) for t, p in stills if s0 - 1e-6 <= t <= s1 + 1e-6]
        if len(seg) < 3:
            notes.append(f"连拍 {spec}：这段只有 {len(seg)} 张截图，看不出有没有在动。至少每 0.2 秒一张。")
            continue
        sheet([(f"{t:.2f}s", im) for t, im in seg], out / f"burst-{s0:g}-{s1:g}.jpg", 220, 8)
        still_run, worst, moving = 0.0, 0.0, 0.0
        for (t1, a1), (t2, a2) in zip(seg, seg[1:]):
            if diff(a1, a2) < 1.2 and held(t1, t2):
                still_run = 0.0
            elif diff(a1, a2) < 1.2:
                still_run += t2 - t1
                worst = max(worst, still_run)
            else:
                still_run = 0.0
                moving += t2 - t1
        lines.append(f"\n## 连拍 {s0:g}–{s1:g} 秒\n\n{len(seg)} 张 · 画面在动的时间约 {moving:.1f} 秒 / {s1 - s0:.1f} 秒 · 最长连续不动 {worst:.1f} 秒")
        if worst >= 1.0:
            notes.append(f"连拍 {spec}：有连续 {worst:.1f} 秒几乎不动。这一段本来该动吗（开场、转场、3D 运镜都该）？")
        if s0 <= 0.01 and s1 >= 3.9:
            w1 = sum(t2 - t1 for (t1, a1), (t2, a2) in zip(seg, seg[1:]) if t2 <= 1.0 and diff(a1, a2) >= 1.2)
            w2 = sum(t2 - t1 for (t1, a1), (t2, a2) in zip(seg, seg[1:]) if t1 >= 1.5 and t2 <= 4.0 and diff(a1, a2) >= 1.2)
            big1 = max([diff(a1, a2) for (t1, a1), (t2, a2) in zip(seg, seg[1:]) if t2 <= 1.0] or [0])
            big2 = max([diff(a1, a2) for (t1, a1), (t2, a2) in zip(seg, seg[1:]) if t1 >= 1.5 and t2 <= 4.0] or [0])
            lines.append(f"开场两波：0–1 秒在动 {w1:.1f} 秒（最大一格变化 {big1:.0f}）· 1.5–4 秒在动 {w2:.1f} 秒（最大一格变化 {big2:.0f}）")
            if big1 and big2 < big1 * 0.25:
                notes.append(f"开场第二波比第一波小很多（{big2:.0f} 对 {big1:.0f}）：1.5 秒之后是真的有一波，还是只剩一点点漂移？")
            if w2 < 1.0:
                notes.append(f"开场第二波偏弱：1.5–4 秒只有 {w2:.1f} 秒在动。飞进来之后是不是就停住了？")

    lines.append("\n## 提醒（每一条都回去看图，用眼睛判）\n")
    lines += [f"- {n}" for n in notes] or ["- 机器没量到要提醒的。这不代表可以出片：把 stops.jpg 与连拍读进来，照审片习惯档逐条看。"]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n产出在 {out}")


if __name__ == "__main__":
    main()
