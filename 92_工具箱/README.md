# 92 工具箱

> 脚本即能力。AI 调这些脚本，而不是每次重写代码。
> 所有脚本只依赖 Python 标准库 + 少量第三方包 + ffmpeg。

---

## 一、一次性安装

### 1. Python 依赖

```bash
cd 92_工具箱
pip install -r requirements.txt
```

### 2. ffmpeg

Windows：`winget install Gyan.FFmpeg`，或到 ffmpeg.org 下载后把 `bin` 加进 PATH。
验证：`ffmpeg -version` 和 `ffprobe -version` 都能输出版本号。

### 3. 中文字体

字幕烧录需要中文字体。**跨平台最稳的做法：把字体文件随项目走。**

下载思源黑体 `SourceHanSansSC-Bold.otf`（SIL OFL 协议，免费商用）放进 `92_工具箱/fonts/`，
合成时加 `--fontsdir fonts`。

⚠️ **两个坑**：
- **字体名写错是静默的**——写一个不存在的字体名零警告，fontconfig 会直接换个 CJK 字体照常出字，你不会知道用错了。
- **`fontsdir` 指向 `.ttc` 无效**，必须放 `.otf` / `.ttf` 单体字体。
- 苹方（PingFang）**不可用于分发**，不要用。

### 4. API Key

生图需要 Gemini API Key（**图像生成没有免费额度，必须绑定计费账户**）：

```bash
# Windows
setx GEMINI_API_KEY "你的key"
# Linux/Mac
export GEMINI_API_KEY=你的key
```

---

## 二、脚本清单

| 脚本 | 阶段 | 做什么 |
|---|---|---|
| `gen_images.py` | ③素材 | 批量生图（Gemini/Nano Banana），定妆照 + 分镜 + **滚动锚定** |
| `tts_batch.py` | ③素材 | 批量中文配音（edge-tts）+ **词级时间戳** + 分段拼接 |
| `align_subtitles.py` | ③剪辑 | 字幕时间轴（三条路径：manifest / stable-ts 对齐 / 机械切分） |
| `build_video.py` | ③剪辑 | ffmpeg 合成竖版成片（Ken Burns + 转场 + 烧字幕 + 侧链闪避） |
| `make_jy_draft.py` | ③剪辑 | 剪映草稿工程（仅爆款精修用） |
| `matrix_tracker.py` | ⑤复盘 | 校验矩阵实验 CSV、样本覆盖与同平台分组中位数；不制造万能分数 |
| `subtitle_1080x1920.ass` | ③剪辑 | 逐像素验证过的竖版字幕样式 |

---

## 三、标准流水线（一条内容从素材到成片）

```bash
cd 92_工具箱
D="../02_制作中/2026-07-26_故事线_最后一位图书管理员"

# 1) 角色定妆照（新角色才需要，一个角色一辈子做一次）
python gen_images.py --mode sheet \
  --character ../00_账号定位/角色资产库/C001_图书管理员.md \
  --out ../00_账号定位/角色资产库/C001_素材/ \
  --n 4 --model pro --size 4K --ratio 16:9
# → 人工挑 1 张，裁成 front/three_quarter/profile 存回该目录

# 2) 批量出分镜（滚动锚定保持风格连续）
python gen_images.py --mode shots \
  --script "$D/02_分镜脚本.md" \
  --refs ../00_账号定位/角色资产库/C001_素材/ \
  --out "$D/素材/img/" --model flash --size 2K --ratio 9:16
# → 人工过一遍：手指 / 文字乱码 / 角色漂移 / 构图越界
# → 单张不满意：加 --redo 5

# 3) 配音（自带词级时间戳）
python tts_batch.py --script "$D/02_分镜脚本.md" \
  --out "$D/素材/audio/" --voice zh-CN-XiaoxiaoNeural --preset 温柔

# 4) 字幕时间轴
python align_subtitles.py --manifest "$D/素材/audio/manifest.json" \
  --out "$D/素材/subtitle/narration" --ai-label

# 5) 合成（先 --print-only 看分段，再实跑）
python build_video.py \
  --images "$D/素材/img/*.png" \
  --audio  "$D/素材/audio/narration.mp3" \
  --srt    "$D/素材/subtitle/narration.ass" \
  --manifest "$D/素材/audio/manifest.json" \
  --motion-plan "$D/素材/motion_plan.json" \
  --bgm    "../90_模板库/bgm/warm_01.mp3" \
  --fontsdir fonts \
  --out    "$D/素材/final.mp4"
```

若一个旁白段需要拆成多个画面，使用 `--timeline "$D/素材/image_timeline.json"` 取代
`--manifest`。显式时轴会按 `segments[].image/start_s/end_s` 排序图片并检查首尾连续性。

`motion_plan.json` 推荐 schema v2：分开 `subject_motion / environment_motion / camera_motion`，并记录
`method / endpoint_binding / fallback / hero_candidate`。脚本仍兼容旧版 `mode/amount/settle`，但只渲染
静帧/Ken Burns 确定性基线；I2V/V2V 必须先离线生成并通过 K8 五点/接触帧 QA。

---

## 四、速度与画质档

| 档位 | 命令 | 60 秒成片耗时 |
|---|---|---|
| 快速预览 | `--no-kenburns` | **约 7 秒** |
| 批量生产 | `--upscale 2` | 约 60 秒 |
| 画质优先 | 默认 `--upscale 4` | 约 90-150 秒 |

`--upscale 8` 比 4 慢 3.5 倍、收益极小，不要用。

---

## 五、字幕样式速查

| 项 | 值 | 说明 |
|---|---|---|
| 字号 | **Fontsize=104** | Noto Sans CJK 下汉字 advance = **0.691 × Fontsize**，一行 12 字需 104。社区常说的 72 是错的 |
| 底部留白 | MarginV **380** | 三平台通投。只发小红书用 260；抖音+小红书用 300-320 |
| 左右留白 | ≥80px | 抖音右侧交互栏宽 120-140px |
| 每行 | **10-13 字，最佳 12**；最多 2 行 | `WrapStyle:2` 不自动换行、只认 `\N`，字数必须在生成时保证 |

⚠️ **0.691 这个系数依赖字体度量，换字体必须重新标定。**

⚠️ **发布成片生成字幕时固定加 `--ai-label`，并用 `.ass` 不要用 `.srt`**：ffmpeg 的 `subtitles` 滤镜把 SRT 转 ASS 时用
`PlayResX:384, PlayResY:288` 的坐标系，`MarginV=380` 会把字幕直接推出画面**完全消失**。
`build_video.py` 已经对 SRT 路径做了 ×0.15 缩放兜底，但 `.ass` 路径是所见即所得，更省心。

---

## 六、可选：本地生图

见 `本地生图部署.md`。云端 API 已经很便宜（12 张分镜约 ¥3-11），
**本地方案只在两种情况下值得**：出图量非常大，或者需要完全离线。

## 七、可选：发布服务

见 `发布服务部署.md`。**这些服务只在你本地 Windows 上跑**，
云端会话一律不碰登录态。

## 八、矩阵实验校验

```powershell
python matrix_tracker.py ../01_想法库/矩阵实验数据.csv --min-samples 3
python matrix_tracker.py --self-test
```

报告按 `platform + experiment + variant + window` 给中位数和覆盖警告。它不会替人宣布胜者，也不会把不同平台压成一个分数。

## 九、语音 A/B

统一基准文本为 `90_模板库/T10_语音盲测基准.txt`，评审卡为 T9，路线与许可边界见 K10。
当前 Edge 女声样本只作不覆盖正式旁白的内部基线；本地模型优先试 Qwen3-TTS 0.6B `Serena/Vivian`，
权重下载和正式云 API 均在单独确认磁盘、账号和预算后执行。
