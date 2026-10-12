# B1GONE 首页效果图 v1

根据用户的首页草图和选定吉祥物，使用内置 imagegen 生成。最终图为 b1gone-homepage-v1.png。本轮仅制作静态效果图，没有修改页面代码。

## 设计构成

- 顶部黑色导航：左侧依次为“文档”“设置”，右侧为 GitHub 图标。
- GitHub 图标目标：https://github.com/0ase/ResearchAgent。地址由当前项目 Git remote origin 确认。
- 左侧：奶白像素 B1GONE 标志、项目简介和现有 Graph 节点的简要说明。
- 右侧：选定的正面像素机器人、实际 Transformer 用例的英文展示文案和四个彩色子问题。
- 吉祥物下方：奶白研究问题输入框、右对齐的“开始研究”按键；预期提交后进入会话页面并开始研究。
- 画布：沿用会话页面的灰蓝色；以很轻的边缘曲面感、余辉和扫描线表达 CRT 显示屏。
- 动效表达：静态图中的少量 ASCII 字符残影示意随机字符逐步生成按钮标签的过渡状态；实际动画与点击行为需在页面实现。

## 简要设计规则

- 配色：canvas #8FA1A4，ink #151A1B，navigation #202223，keys #E7DEC5，rules #6C7C7F。
- 字体：Existing blocky B1GONE wordmark; pixel Chinese controls and monospace graph node names; normal readable Chinese body; selected mascot keeps uppercase square-cut English font.
- 布局：Full-width black top navigation; left 35% brand and graph-node introduction; right 55% selected mascot and research entry controls; grey-blue canvas with ample margins.
- 原则：Let the selected question-dispersion mascot carry the color; keep the chrome quiet. CRT curvature, afterglow and scanlines stay subtle on the homepage. ASCII button animation is represented as a static transitional frame.

Graph 介绍基于 backend/agents/graph.py 和 backend/agents/retrieval_graph.py。图中展示的是节点职责摘要：supervisor 调度、retrieval 拆解与筛读、analysis 比较证据、writer 综述、critic 审查。完整图中的调度返回与检索反馈分支没有在首页介绍中逐一绘制。

## 参考资料

- homepage-wireframe.png：用户的页面布局草图。
- homepage-wireframe-annotated.png：用户对布局区域的解释。
- homepage-mascot-reference.png：用户选定的吉祥物及英文用例。
- 英文文案的实际拆解来源与翻译映射：../b1gone-mascot-v2-questions.json、../b1gone-mascot-v7-labels.json。

## 生成提示词

```text
Use case: ui-mockup.
Asset type: first finished desktop homepage visual concept for B1GONE, an academic research agent. Output one high-fidelity website screenshot, wide 16:9 landscape, ideally 2560x1440 or 2048x1152. Do not show a physical monitor, laptop, browser window or desk.

INPUT REFERENCES:
Image 1 is the user's clean homepage WIREFRAME: top navigation strip, a left brand/introduction column, a large right mascot area, and research entry controls below the mascot.
Image 2 is the user's ANNOTATED layout explanation. Use it for layout intent only. Do NOT render its red annotation text or sketch boxes literally.
Image 3 is the FINAL SELECTED MASCOT illustration to integrate faithfully into the right-side illustration area: front-facing 2D cream pixel robot with black visor and smile, orange antenna, black input prompt from the left and FOUR colored question wedges to the right. Preserve its character, English example, font, colors and four questions. Do not substitute a 3D CRT head, remove its research example, add extra beams, or alter its smile.

CORE STYLE:
A restrained 1970s early-computer research terminal aesthetic. Grey-dominant GREY-BLUE canvas #8FA1A4, charcoal top navigation #202223, ink-black #151A1B text, warm cream #E7DEC5 interactive keys with shallow retro bevels and dark outlines. No green cast, neon, synthwave, disco, cyberpunk, purple background, modern glassmorphism, SaaS cards or dramatic gradients. The mascot's spectrum is the concentrated color accent.
The homepage itself has a very subtle CRT glass-screen treatment: barely convex/bowed visual field near outer edges, extremely faint fine horizontal scanlines (roughly 2–3% opacity), a delicate local phosphor afterglow around cream strokes, and very light edge falloff. Keep central content and letterforms crisp and readable. No strong barrel distortion, blurred text, RGB splitting, flickering black bands, noisy static, deep vignette or large reflection. No literal old TV housing.

TOP NAVIGATION:
A full-width black horizontal bar around 64–76px tall in this desktop design. On the LEFT, exactly TWO cream retro rectangular key buttons, in this exact order:
a small pixel document icon + "文档"
a small pixel gear icon + "设置"
On the far RIGHT, a small cream GitHub Octocat silhouette/icon, recognizable and visually clickable, inside a quiet compact square hit area. No additional top-navigation choices, large header wordmark, social icons, account menu, search bar or centered links.
The intended GitHub destination is https://github.com/0ase/ResearchAgent, but do not print the URL on the page.

MAIN LAYOUT:
Respect the user's two-column wireframe. Generous horizontal margins, about 6% of canvas width, main content vertically centered within the first screen. LEFT column about 34–36% of main width; RIGHT column about 55–58%, with a comfortable gutter.
LEFT:
A large existing-style chunky PIXEL B1GONE brand wordmark, spelled B + digit 1 + G + O + N + E, cream on a simple black rectangular nameplate. This occupies the top of the left column, similar to the logo rectangle in the wireframe. No decorative slogan above the logo. The wordmark has deliberate low-resolution stepped block letterforms, not a modern sans wordmark.
Below it, a short readable Chinese introduction, exactly:
"拆解问题、检索文献、比较证据，"
"生成可追溯的研究综述。"
Use a normal readable Chinese body font rather than tiny pixel body text.
Then a compact ordered description of the EXISTING graph nodes, with a small pixel role icon per row, lower-case monospace English node name and short readable Chinese description. This should feel like an explanatory terminal pipeline, not five oversized rounded cards. Use restrained fine connecting marks or a simple vertical rail if helpful. Exact node rows:
"supervisor" — "任务规划与调度"
"retrieval" — "问题拆解、检索、筛选与阅读"
"analysis" — "比较共识、差异与研究空白"
"writer" — "整理证据并撰写综述"
"critic" — "检查论证与引用"
Each row is visually compact, with generous readable line spacing and no fabricated live progress states or counts.

RIGHT:
A large illustration region with the selected mascot from Image 3, blending its grey-blue background naturally into the canvas. Use the wireframe's large right rectangle as its bounding area, not as a thick black frame. The mascot should remain the memorable hero. Keep its input and all four output labels fully visible and readable. Preserve the provided blocky uppercase squared geometric English font.
English input text remains split above and below the black input line:
above: "TRANSFORMER" / "ARCHITECTURE:"
below: "WHAT'S NEW OVER" / "THE PAST TWO YEARS?"
The four output labels remain:
"NEW ATTENTION" / "MECHANISMS?"
"NEW EFFICIENT" / "VARIANTS?"
"WHICH BENCHMARKS" / "AND DATASETS?"
"EFFICIENCY AND" / "ACCURACY GAINS?"
Do not convert this illustration into a generic decorative robot without the decomposition example.

Below the illustration, a long warm-cream research question input field with dark ink pixel-style placeholder, exactly:
"输入研究问题，开始探索… |<"
Keep it large enough for a real question and visually distinct from the illustration.
A compact warm-cream retro primary key labelled "开始研究" sits immediately below the field, aligned to the right edge, echoing the wireframe's separate controls. This starts research in the conversation screen when implemented. Do not add sign-in, pricing, upload, demo, export or other actions.
Buttons will eventually animate by random ASCII glyphs resolving into their labels. Since this is a STILL IMAGE, keep all button labels legible and show only a few very faint short ASCII ghost glyphs such as "#", "<", "_" beside the last character of the primary action as a subtle moment of the decoding transition; no gibberish paragraphs, code snippets, motion arrows or explanatory animation badges.

QUALITY:
One coherent polished desktop homepage screenshot, no sketch annotations or comparison panels. Preserve the visual connection with the existing grey-blue conversation workspace. Clear Chinese text, accurately spelled English labels, readable type scale, restrained CRT effects and generous negative space. No huge empty hero headline, excessive metadata labels, footer clutter, watermark, fake browser chrome, fake stats or modern template ornaments.
```

## 画布与 CRT 效果细化提示词

```text
Use case: precise-object-edit / color-and-screen-treatment refinement.
Image 1 is the edit target: the first B1GONE homepage mockup with black top navigation, cream buttons, left B1GONE logo and five graph rows, right pixel mascot and question entry.

Make a targeted BACKGROUND / CRT TREATMENT adjustment only:
1. The main canvas currently looks too blue. Rebalance it to the established conversation workspace's GREY-DOMINANT GREY-BLUE #8FA1A4 (RGB 143,161,164). It should read as neutral grey with a small cool blue undertone, not a blue screen. Use this color across the main body.
2. Greatly reduce the strength of the full-page horizontal scanline pattern. At normal viewing scale the canvas should appear mostly calm and smooth; scanning lines are only barely perceptible on close inspection (around 1% opacity). Remove the dense dark horizontal banding and obvious screen texture. Keep only a very slight curved-glass edge falloff and a delicate small afterglow around cream elements. No heavy blur, added noise, green tint, vignette or obvious barrel distortion.

Preserve EVERY OTHER element EXACTLY:
- same layout, 16:9 canvas, margins, black top bar
- left cream "文档" and "设置" buttons in that order, cream GitHub icon on the right
- cream-on-black blocky B1GONE wordmark
- every existing Chinese introduction and graph-node text, all five pixel node icons and their positioning
- the selected front-facing pixel robot and its four colored wedges, every English Transformer label
- the cream question input, placeholder and cream "开始研究" key, its small ASCII ghost glyphs
- exact existing fonts, text sizes, line breaks and colors of all labels
Do not redraw/reposition components, alter the mascot, add content, change wordmark spelling, remove controls or crop the screenshot. Only bring the main canvas color closer to #8FA1A4 and make the CRT scanning treatment much subtler.
```
