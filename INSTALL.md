# 怎么装

这是一个给 Claude Code 用的 skill：一包说明书、范例图、两支审片脚本。装好之后，你跟 Claude 说「帮我做一支动画」，它就会照这里面的思路做。

正本与最新版：https://github.com/suiyang-meta/sui-motion-graphic-reel

## 最省事的装法

把这一行贴给你的 Claude Code：

```
帮我装这个 skill：https://github.com/suiyang-meta/sui-motion-graphic-reel
放进我的 skills 资料夹，装好跟我说里面有什么。
```

## 自己装

Mac / Linux：

```bash
git clone https://github.com/suiyang-meta/sui-motion-graphic-reel ~/.claude/skills/sui-motion-graphic-reel
```

Windows PowerShell：

```powershell
git clone https://github.com/suiyang-meta/sui-motion-graphic-reel "$env:USERPROFILE\.claude\skills\sui-motion-graphic-reel"
```

拿到的是 zip：解开后把 `sui-motion-graphic-reel` 资料夹放到上面那个位置。

装完重开 Claude Code。之后要更新，在那个资料夹里 `git pull`。

## 要准备的

- Claude Code（付费方案）。
- ffmpeg。没有就请 Claude 帮你装。
- 做片的引擎（HyperFrames 或 Remotion）与配音服务：Claude 会照 `references/engines.md` 带你装，装之前会先讲每样是做什么的。

## 第一次用

直接讲你要做什么，例如：

> 帮我做一支 15 秒的直式动画，介绍我店里新出的 ___。气质要 ___，颜色我想用 ___。

它会先找你有没有现成的 design system；没有就问你几题或看你的参考，出三套风格给你挑。接着给你看分镜，你点头它才开始做。出片之前它会先替你审一遍。

不满意就直接讲感觉（「很干」「很 static」「不够高级」），它会查对照表知道该改哪里。

作者：Sui Yang · IG @asksui.ai · 授权 CC BY 4.0（要标明出处）
