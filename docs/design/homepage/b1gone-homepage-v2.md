# B1GONE 首页效果图 v2

本轮基于 b1gone-homepage-v1.png 使用内置 imagegen 编辑，最终效果图为 b1gone-homepage-v2.png。保留第一版文件。本轮仅修改静态效果图，没有编写首页代码。

## 本轮调整

- 中文改为清晰的像素艺术字，包括导航、简介、节点职责、输入提示和开始研究按钮。英文节点名、吉祥物英文用例及 B1GONE 标志沿用原风格。
- 左侧延续第一版的标志、两行简介和五行节点布局。
- 右侧吉祥物、四条彩色子问题及研究输入区域向下调整。
- 吉祥物左侧黑色入射线延伸至屏幕左缘，同时作为简介与下方 agent 节点之间的分隔线。
- 校准黑线衔接及上下留白，保持平直，并避开文字与图标。
- 保留灰蓝画布、黑色导航、奶白按键和轻微 CRT 质感。按钮上的 ASCII 字符仅为静态动效示意。

最终图采用第三次编辑输出。像素级位置由图像生成近似表达；后续代码实现时应使用同一条水平线及布局约束控制对齐。

## 延续的信息

- GitHub 目标沿用第一版已核实的 https://github.com/0ase/ResearchAgent。
- 五行节点职责与实际 Transformer 拆解用例来源见 b1gone-homepage-v1.md 及其引用记录。
- 本轮没有重新执行研究任务，也没有修改后端、配置、前端页面代码或 Git 提交。

## 编辑提示词

### 初次修改提示词

```text
Use case: precise-object-edit / ui-mockup revision.
Image 1 is the edit target: the existing B1GONE desktop homepage screenshot. Make ONLY these requested refinements; keep the rest faithfully unchanged. Output one revised screenshot at the same wide 16:9 framing.

1. CHINESE TYPOGRAPHY
Render all Chinese glyphs in a legible retro low-resolution Chinese pixel-art typeface, with square terminals and clearly stepped strokes, matching the existing B1GONE and terminal aesthetic. Do not make the words blurry or use unreadable pseudo-Chinese. Preserve the EXACT wording, font sizes, text blocks, line breaks and approximate ink footprints. This affects the top buttons "文档" and "设置", the two-line introduction, five node descriptions, the input placeholder and "开始研究". Keep the English graph node names and the mascot's uppercase English example in their existing styles.
Chinese text verbatim:
"拆解问题、检索文献、比较证据，"
"生成可追溯的研究综述。"
"任务规划与调度"
"问题拆解、检索、筛选与阅读"
"比较共识、差异与研究空白"
"整理证据并撰写综述"
"检查论证与引用"
"输入研究问题，开始探索... |<"
"开始研究"

2. LOWER THE COMPLETE RIGHT GROUP
Move the entire right illustration and its question-entry controls DOWN together by approximately 60 pixels on the 1672x940 reference, roughly 6.4% of screen height. Translate the robot, orange antenna, incoming English prompt, all four colored wedges and labels, cream input field and cream action button as ONE group. Preserve their horizontal positions, widths, sizes, spacing and proportions. All content must remain visible inside the screenshot with a modest bottom margin. No resizing, horizontal shifting or changes to the robot's face or pose.
The black horizontal input beam should end up around y=450 (48% of full image height).

3. EXTEND THE BLACK INPUT BEAM TO THE LEFT SCREEN EDGE
Extend the mascot's existing straight black incoming beam LEFTWARD until it meets x=0, the very left edge of the screen. Keep the same black thickness (around 6 px), horizontal orientation and uninterrupted geometry, connected to the robot's LEFT ear at the shifted vertical position. This one continuous beam must double as a long visual divider: in the LEFT column it passes exactly through the empty gap BETWEEN the two-line introduction and the first supervisor node. Thus the introduction is above this line and all five agent node rows are below it. Never run the line through text, icons, the B1GONE nameplate or a node. Do NOT add a second disconnected divider or arrows.
Keep the English input split snugly around the beam in its existing position in the right column:
above "TRANSFORMER" / "ARCHITECTURE:"
below "WHAT'S NEW OVER" / "THE PAST TWO YEARS?"

INVARIANTS
The LEFT COLUMN stays in its original position and layout: same B1GONE cream-on-black pixel wordmark, its black plaque, two-line introductory copy, five icon/node rows and vertical connecting rail. Change only the Chinese letterform style there; do not move or resize the left content to accommodate the beam. Locate the beam in the EXISTING gap.
Keep the black navigation bar, button placement/order and GitHub icon unchanged.
Keep the established grey-dominant grey-blue canvas #8FA1A4, cream #E7DEC5 keys, charcoal #202223 chrome and ink #151A1B.
Keep the restrained CRT curvature/edge falloff, faint afterglow and barely visible scanlines.
Keep all four outgoing labels and colors exactly: orange-red "NEW ATTENTION / MECHANISMS?", yellow "NEW EFFICIENT / VARIANTS?", teal "WHICH BENCHMARKS / AND DATASETS?", violet "EFFICIENCY AND / ACCURACY GAINS?".
Preserve the current subtle ASCII ghost glyphs by the primary key as a static animation hint. No extra content, new controls, labels, borders, annotations, physical monitor, browser chrome or watermark.
```

### 黑线与布局校准提示词

```text
Use case: precise-object-edit / geometric alignment correction.
Image 1 is the EDIT TARGET, the revised grey-blue B1GONE homepage with Chinese pixel type and lowered right side. Image 2 is only a POSITION REFERENCE for the original left-column node list. Do not revert Image 1's pixel Chinese typography.

Correct only the beam alignment and the slight positioning drift, with these concrete coordinates on the 1672x940 composition:
- The black input beam must be ONE perfectly STRAIGHT HORIZONTAL stroke, approximately 6px thick, centered at y=450, extending continuously from x=0 to the robot's LEFT ear around x=970. No elbow, step, kink, vertical jog, slope, arrow, disconnected segment or second horizontal divider. It should visually cut the grey-blue body into the left introduction above and left agent-node list below, using the existing gap.
- Translate ONLY the right mascot ILLUSTRATION group up approximately 50 pixels relative to Image 1, so the input beam and robot's ear/visor center are aligned around y=450. Translate together the robot including orange antenna, incoming English words, four colored wedges and their English labels. Preserve size, horizontal position, geometry, wording, typefaces and colors. This still leaves the illustration about 60px LOWER than its original Image 2 position. "TRANSFORMER / ARCHITECTURE:" remains above the beam with the bottom of "ARCHITECTURE:" snugly above y=450. "WHAT'S NEW OVER / THE PAST TWO YEARS?" remains just below it.
- Restore the LEFT COLUMN five node icons/names/descriptions/vertical rail to the original positions shown in Image 2: first supervisor icon around top y=477 and the final critic icon around y=782. The node list in Image 1 has drifted down about 24px; move the entire five-row list up about 24px. Do not change any icon, width, column position, spacing or wording. Keep the new Chinese pixel type.
- Leave the already lowered cream research INPUT FIELD and START BUTTON EXACTLY at their Image 1 positions (input top approximately y=690; button top approximately y=789). Their lowering is already correct; do not move them again.

Everything else is LOCKED to Image 1: B1GONE logo and plaque at original coordinates, two-line Chinese introduction at original coordinates, pixel Chinese typography, top black navigation with cream 文档 / 设置 keys and GitHub icon, grey-dominant grey-blue #8FA1A4 canvas, mild CRT edge curvature/afterglow/barely perceptible scanlines, cream controls, input placeholder, "开始研究" and small ASCII ghost glyphs.
Do not add or remove any content. No lettering changes, size changes, overall layout redesign, cropping, annotations or watermark. The essential correction is a single straight black line at y=450 with the illustration centered on it and all left nodes safely below.
```

### 最终留白校准提示词

```text
对图1做最后一次局部排版校准，保持这张 B1GONE 首页的全部内容、像素中文字体、配色、导航、尺寸不变。

关键构图：黑色入射线是一条水平直线，从画面最左边缘一直进入机器人左侧耳朵的正中心。这条线在左栏应当处于两行简介与第一行 supervisor 图标之间的空白正中，上下都有舒适留白，不能贴着简介的字底。当前黑线离简介太近，而且没有通过机器人左耳中心，请校准。

具体移动：
- 左侧 B1GONE 标志及两行简介完全不动。
- 黑线下移约18px，到整幅940px高画面的 y=450 左右，线宽约6px，笔直连续，无折角、无箭头。
- 将机器人头、天线、四条彩色子问题线束及其英文标签一起向下移动约37px，使机器人的左耳中心与该黑线同高，线真正进入耳朵中心。角色、四条彩色束的造型以及所有英文词句一律不改。
- 黑线上下的英文入射问题两块文字也下移，仍然靠着黑线上下排布，避免碰到左栏文字，保持其现有横向位置、字体、两行分组。
- 左侧五行agent节点和竖直连接线整体向下回移约14px，恢复第一版列表的高度：第一枚 supervisor 图标顶部约477px，最后 critic 图标顶部约782px，仍然保持行距、大小、横向位置及其像素中文。
- 右下已经位于y=690左右的奶白输入框与y=789左右的“开始研究”按钮不要移动，它们已在正确的下移位置。

其他全部保持图1原样：黑色顶部栏、文档/设置/GitHub、奶白 B1GONE 标志、灰中带淡蓝的背景、清楚易辨的像素中文、左栏内容、轻微CRT曲面与余晖、很淡扫描线、奶白交互按键及少量ASCII残影。不要重新设计画面、改变文案、删除元素或添加注释。
```
