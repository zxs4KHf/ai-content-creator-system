---
name: zimeiti-video
description: "阶段③下半 视频剪辑。把一组插画加旁白加字幕，用 ffmpeg 自动合成 1080x1920 竖版短视频，含 Ken Burns 运镜、转场、烧录字幕、BGM 侧链闪避；也能生成剪映草稿工程文件供人工精修爆款。触发词：合成视频、出片、剪视频、做视频、生成视频、ffmpeg、Ken Burns、烧字幕、加 BGM、剪映草稿、剪映工程。图片停留时长会自动按旁白分段对齐。不负责生成图片和配音，那是 zimeiti-visual 的事；不负责写多平台发布文案，那是 zimeiti-publish 的事。"
license: MIT
metadata:
  version: "1.0.0"
  stage: "3-editing"
---

# 视频合成（阶段③下半）

## 双路线

| 路线 | 用途 | 何时用 |
|---|---|---|
| **ffmpeg 全自动** | 主流水线，批量出片 | **默认**。每条内容都走这条 |
| **剪映草稿** | 人工精修 | 只给数据回流后的**前 5% 爆款候选**，加花字/气泡/官方特效包 |

**不要一上来就用剪映**：剪映 7+ 封了 UI 自动化，每条都要手动点导出等渲染，批量时是纯线性人力。ffmpeg 一条命令出片，60 秒成片约 90 秒渲染。

## 路线 A：ffmpeg 全自动（默认）

### A1. 字幕时间轴

我们有口播原文，**不需要 ASR 识别，只需要对齐**。三种方式，按优先级：

1. **直接用 edge-tts 的词级时间戳**（`素材/audio/manifest.json`）—— 最准，白送，**首选**
2. `stable-ts` 强制对齐 —— 当配音不是 edge-tts 生成时用
3. 按字数加权机械切分 —— 兜底，同时可作为前两者的 sanity check（差异 >2 秒说明对齐炸了）

```bash
cd 92_工具箱
python align_subtitles.py --manifest "../02_制作中/xxx/素材/audio/manifest.json" \
  --out "../02_制作中/xxx/素材/narration.srt"
```

### A2. 合成

```bash
python build_video.py \
  --images "../02_制作中/xxx/素材/img/*.png" \
  --audio  "../02_制作中/xxx/素材/audio/narration.mp3" \
  --srt    "../02_制作中/xxx/素材/narration.srt" \
  --bgm    "../90_模板库/bgm/warm_01.mp3" \
  --out    "../02_制作中/xxx/素材/final.mp4"
```

先加 `--print-only` 看分段是否合理，再实跑。

脚本做的事：每张图正好覆盖对应旁白段落 → Ken Burns 运镜（4 倍预放大抗抖动）→ xfade 转场 → 烧录字幕 → BGM 侧链闪避 + 响度归一化 → 输出 faststart MP4。

**实测**：8 图 / 24 条字幕 / 60.03 秒音频 → 成片精确 60.00 秒。

### A3. 速度与画质档

| 档位 | 参数 | 60 秒成片耗时 |
|---|---|---|
| 快速预览 | `--no-kenburns`（concat demuxer） | **约 7 秒** |
| 批量生产 | `--upscale 2` | 约 60 秒 |
| 画质优先 | `--upscale 4`（默认） | 约 90-150 秒 |

`--upscale 8` 比 4 慢 3.5 倍收益极小，不要用。

### A4. 三个已实测的坑

1. **SRT 路径的尺寸要 ×0.15**。ffmpeg 把 SRT 转 ASS 时用 `PlayResX:384, PlayResY:288`，直接写 `MarginV=380` 字幕会**完全消失**。
   → **推荐直接用 `.ass` 路径**（`92_工具箱/subtitle_1080x1920.ass`），数值即 1920 坐标系，所见即所得。脚本已默认走 ass。
2. **字体名写错是静默的**。写一个不存在的字体名零警告，fontconfig 直接换个 CJK 字体照常出字——你不会知道用错了。**跨平台最稳：把字体文件随项目走。**
3. **`fontsdir` 指向 `.ttc` 无效**，必须放 `.otf`/`.ttf` 单体字体。

### A5. 字幕样式规范

用 `92_工具箱/subtitle_1080x1920.ass`，已逐像素验证：

| 项 | 值 |
|---|---|
| 字号 | **Fontsize=104**（Noto Sans CJK 下汉字 advance = 0.691 × Fontsize，一行 12 字需 104，不是社区常说的 72） |
| 底部留白 | MarginV=380（三平台通投）/ 260（只发小红书）/ 300-320（抖音+小红书） |
| 左右留白 | ≥80px（抖音右侧交互栏宽 120-140px） |
| 每行 | **10-13 字，最佳 12**；最多 2 行 |
| 字体 | 思源黑体 / Noto Sans CJK SC（SIL OFL 免费商用）。**苹方不可用于分发** |

⚠️ 0.691 这个系数**依赖字体度量，换字体必须重新标定**。

## 路线 B：剪映草稿（爆款精修）

```bash
python make_jy_draft.py \
  --images "../02_制作中/xxx/素材/img/*.png" \
  --audio  "../02_制作中/xxx/素材/audio/narration.wav" \
  --srt    "../02_制作中/xxx/素材/narration.srt" \
  --draft-folder "C:/Users/xxx/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"
```

生成后在剪映里打开 → **这就是 G3 门**（人工看一遍 + 微调 + 手动导出）。

### 必须知道的版本限制

| 功能 | 支持版本 |
|---|---|
| **草稿生成（我们用的）** | **剪映 5 及以上全版本** ✅ 没被封 |
| 模板模式（读已有草稿） | 仅 ≤5.9 ❌ 6+ 已加密 |
| 批量自动导出 | 仅 ≤6 ❌ 7+ 隐藏了 UI 控件 |

**不要尝试自动导出。** 剪映主流版本已到 10.x，硬做会一直碎。手动点导出正好是 G3 人工门，反而契合流程设计。

### 三个坑

1. **音频必须用 WAV 不用 MP3**。已知 issue：VBR MP3 读时长会少于实际并报错，对 TTS 场景致命。
2. **锁定版本 `pyJianYingDraft==0.2.7`**。v0.3.0 有破坏性变更（`add_track` → `append_track`）。
3. **中文枚举成员名各版本在变**。跑之前先 `print([m.name for m in draft.TransitionType])` 打印实际可用枚举，不要照抄 `叠化`/`渐显`。

草稿目录路径从剪映「全局设置 → 草稿位置」复制，**不要猜**。

## 动效增强（可选，零成本）

生图出的是静态插画，让它"活"起来有几条零成本路子（全部 ffmpeg，已实测）：

| 需求 | 方案 | 成本 |
|---|---|---|
| 镜头推拉/横移 | Ken Burns（已内置） | ¥0 |
| 空间纵深感 | Depth Anything 出深度图 + `displace` 视差 | ¥0 |
| 云雾/水面局部流动 | 遮罩 + `displace`（人脸纹丝不动） | ¥0 |
| 画面"活度" | `noise=alls=6:allf=t+u` 时域颗粒 | ¥0，**效果被严重低估** |
| 眨眼/微表情 | LivePortrait | ¥0 |

**不建议全片用图生视频（I2V）**：I2V 本质是重绘，会破坏你辛苦锁定的角色和画风——恰好摧毁最贵的资产。真要用，只给 3-4 个关键镜头（开场、情绪转折、有物理运动的镜头），成本能压到全 I2V 的 1/3。

## 输出规格

```
-c:v libx264 -preset medium -crf 20
-profile:v high -level 4.1 -pix_fmt yuv420p
-r 25 -g 50 -keyint_min 25 -sc_threshold 0
-c:a aac -b:a 192k -ar 44100 -ac 2
-movflags +faststart
```

## 质量自检

- [ ] 成片时长 = 音频时长（误差 <0.1 秒）
- [ ] 字幕每行 ≤12 字、最多 2 行、无越界
- [ ] 底部留白足够（三平台通投用 380）
- [ ] 单张图停留 3-6 秒，无超过 8 秒的
- [ ] 旁白与 BGM 音量平衡（侧链闪避生效，人声清晰）
- [ ] 首帧就是钩子画面，不是黑场或 Logo
- [ ] 用 ffprobe 确认 `1080x1920 / h264 High / yuv420p / faststart 生效`

## 参考

- `92_工具箱/build_video.py` —— 主合成脚本（已实跑验证）
- `92_工具箱/subtitle_1080x1920.ass` —— 逐像素验证的字幕样式
- `92_工具箱/align_subtitles.py` —— 字幕时间轴
- `92_工具箱/make_jy_draft.py` —— 剪映草稿生成
