# 引擎怎么接

这份 skill 的思路跟引擎无关。「用代码做影片」的引擎都在做同两件事：告诉你的程式**现在第几帧**，然后把那一帧**拍下来**。真正画画的是浏览器（HTML / CSS / SVG / canvas / three.js）。所以换引擎只换「时钟」，画面的写法几乎照搬。

**不管哪个引擎，先做这三件事**：

1. **去读官方文件**，确认现在安装与出片的正确指令（工具更新很快，不要凭记忆）。
2. 引擎如果有给 AI 读的官方说明（agent skill / rules / 专案里生成的 AGENTS.md），**读完并照它的规矩写**。要不要把它装进用户的电脑，照那份说明自己写的做法；它说由用户自己装，就告诉用户、不要代装。
3. 先跑一次空白专案的出片，确认整条线是通的，再开始做画面。

装完跟用户讲：装了哪几样、每样做什么，一样一句话。

## 选哪个

| | HyperFrames | Remotion | 其他 |
|---|---|---|---|
| 写法 | 一页 HTML + 一条暂停的时间轴，出片时拨到第 t 秒 | React 元件 + `useCurrentFrame()` | 任何能「给帧数 → 截一帧」的做法都行 |
| 授权 | 开源、免费（Apache-2.0） | 个人与小团队免费；公司超过一定人数要买授权 | 各自查 |
| 适合 | 不想碰 React、想要免费可商用 | 已经熟 React | — |

授权是 2026 年 11 月读到的，会变：**出片拿去商用之前，到官网的授权页现查一次**，把读到的结果告诉用户。作者现在用 HyperFrames。

## HyperFrames：怎么接成「给帧数就画出那一帧」

官方文件教的多半是用 GSAP 一段一段补间。要照 SKILL.md §4⑧ 的写法（整个画面是时间的函数），最小骨架是这样 —— 一条暂停的时间轴只推一个数字 `t`，每次 `t` 变就整个重画（2026-11 用 HyperFrames 0.9 实跑过；版本不同以 `hyperframes docs` 为准）：

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>
<div id="root" data-composition-id="main" data-start="0" data-duration="15"
     data-width="1080" data-height="1920">
  <div id="stage" class="clip" data-start="0" data-duration="15"></div>
</div>
<script>
  const FPS = 30;
  function render(time) {
    const f = Math.round(time * FPS);      // 第几帧
    // …照 f 算出每一样东西的位置、大小、透明度，写回 #stage 里的元素…
  }
  const st = { t: 0 };
  const tl = gsap.timeline({ paused: true });
  tl.to(st, { t: 15, duration: 15, ease: "none", onUpdate: () => render(st.t) }, 0);
  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  render(0);
</script>
```

- 片长在三个地方要一致：`data-duration`、`tl.to` 的 `t` 与 `duration`。
- 出片前先用它的单张截图指令（`hyperframes snapshot`）截几个时间点看，比每次出整支片快；它的 `lint` / `check` 也先跑。
- **中文字体**：只写系统字体名（宋体、苹方）在本机出片是对的，但 lint 会报错、换一台机器或云端出片会退成别的字。稳的做法是把字档放进专案、用 `@font-face` 指过去，或用有中文的网页字体。字体的授权照它自己的条款。

## 共同规矩（哪个引擎都一样）

- **画面由帧数算**（SKILL.md §4⑧）。不用 CSS animation / transition，不用自己跑的计时器。
- **图片常驻**：图片元素建一次就留着，每帧只改位置与样式。每帧重建的图片会来不及画就被截图，结果是某些帧缺图。
- **资料先算好**：文字取样点、粒子目标位置、角色的像素表，先在本机算好存成档再载入。
- **片长写死在引擎认的地方**，跟配音长度对上。配音一改，片长要跟着改。
- **字体先载完再截图**。
- 专案资料夹名不要有空格（有些脚本会坏）。

## 真 3D（three.js）

- 不到真 3D 的程度（只是要前后层次与飞入）可以用 2.5D：每个物件给一个深度 z，镜头也有 z，画的时候照 `焦距 / (z − 镜头z)` 缩放与位移。它做得出视差与穿过前景，做不出绕着物体看侧面 —— 要看侧面就用下面的真 3D，不要拿 2.5D 冒充。
- 用真的 `PerspectiveCamera`。摄影机路径写成关键帧（偏航角、半径、高度、看向哪、视角），每段慢起慢停插值，每帧设 `position` / `lookAt` / `fov` 再 `updateProjectionMatrix()`。
- **不要让 three.js 自己跑动画循环**（`requestAnimationFrame`、React Three Fiber 的 `useFrame`）。改成：引擎告诉你第几帧 → 你摆好摄影机与物件 → 手动 `renderer.render(scene, camera)` 一次。
- 3D 接 2D 要无缝：第一个关键帧把摄影机放在「1 个单位 = 1 个萤幕像素」的距离（`画面高的一半 / tan(视角 / 2)`），这样 3D 画面与前一幕的 2D 画面大小对得上。
- 粒子：自订 shader 的点。景深（离焦越远越大越淡）、拖尾（多画几个过去位置的残影）、大小与透明度带随机、聚成的字要有厚度。
- 每个出片分页的第一帧容易缺东西：等画布真的画过一次再放行截图。
- 做完一定逐 0.1–0.2 秒放大看（SKILL.md §6 第 3 步）。

## 配音

- 稿整段一次送去生成，要求回传**每个字的时间**（带时间戳的 TTS 接口）。
- 语速照 design system。要加速就整条一起加速，逐字时间同比例缩。
- 钥匙（API key）放在专案的 `.env`，只读不印，不要写进程式或提交到版本库。
- **商用授权**：很多 TTS 服务的免费方案不能商用、或要求标注出处。要发在会赚钱的帐号上，请用户先确认自己的方案能不能商用（作者用 ElevenLabs，2026 年 11 月读到的是：免费方案不能商用）。
- TTS 回传的逐字时间有时会晚 0.1–0.2 秒。对不准时，用音量曲线或语音转文字的字级时间交叉核对。
- 出片后把成片的声音听写一次对稿。

## 音效与配乐

- 音效可以用程式合成（镜头移动的呼声、元素落地的点击声），照节拍表的时间放。**有声音的地方画面一定要有对应的动作**：放了转场的呼声，镜头就要真的在动。
- 配乐用自己有授权的。人声永远在最前面。

## 出片后

跑 `scripts/review.py`（SKILL.md §6）。需要本机有 ffmpeg；没有就请 AI 帮你装。
