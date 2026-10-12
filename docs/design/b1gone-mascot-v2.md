# B1GONE 首页吉祥物概念 v2

使用内置 imagegen 工具生成。本图为视觉概念，尚未接入首页；v1 保留。

- 输入方向：黑色研究 prompt 从机器人左侧进入。
- 输入示例：Transformer 架构最近两年内的创新。
- 范围：以本次采样日期 2026-10-11 为基准，指定 2024-10-11 至 2026-10-11。
- 输出方向：彩色子问题从右侧展开，文字按不同倾角形成扇面，移除所有线束与箭头。
- 形式：保留奶白外壳、炭黑面屏、方形眼睛及 2.5D 像素机器人头；增大问题字体。
- 输出配色：由红橙黄绿渐变至蓝紫，以彩色文字表现问题分光。
- 概念图：b1gone-mascot-v2.png。
- 原始拆解记录：b1gone-mascot-v2-questions.json。

## 子问题来源

实际调用项目的 `backend.agents.orchestrator.orchestrate` 两轮，每轮 5 个查询；第二轮在 current_task 中要求补充不同角度。模型为 `deepseek-flash`，两轮 finish_reason 均为 stop，原始模型正文和 usage 已记录在 JSON 中。仅运行问题拆解，没有执行论文搜索、阅读、事实验证或综述生成；不将子问题视为研究结论。

初次使用节点默认参数的两次调用触发了解析兜底，其确定性查询已排除。本次采用原节点及其提示词，仅在临时采样进程中把 max_tokens 调整为 4000，并对 DeepSeek 主机发送 reasoning_effort=none、thinking=disabled。临时脚本位于被忽略的 tmp/generate_mascot_questions.py；没有修改后端源码、实际配置文件或数据库。不能据此声称默认节点已经修复，也未诊断初次兜底的具体原因。

图中文字是原始拆解结果的展示简写，由表中记录逐一映射；共同主题和时间范围由输入问题限定。完整子查询优先于概念图中的短文案。未来首页应将文案作为 HTML/SVG 层，可动态换成真实任务数据，并维持可访问性和移动端可读性。

| 来源轮次与序号 | 原始子查询 | 图中展示文案 |
| --- | --- | --- |
| 1.1 | 近两年Transformer架构有哪些基础性创新？ | Transformer 有哪些基础性创新？ |
| 1.2 | 2024-2026年Transformer有哪些新方法？ | 近两年有哪些新架构方法？ |
| 1.3 | 近两年Transformer架构有哪些评测基准？ | 如何评测这些架构创新？ |
| 1.4 | 2024-2026年Transformer架构改进了哪些性能？ | 架构改进提升了哪些性能？ |
| 1.5 | 近两年Transformer架构创新有哪些局限？ | 这些架构创新有哪些局限？ |
| 2.1 | 2024-2026年Transformer在长序列建模与注意力机制方面有哪些基础性创新？ | 长序列与注意力机制有哪些创新？ |
| 2.2 | 2024-2026年Transformer稀疏化、线性化及混合架构等高效变体有哪些新方法？ | 稀疏、线性及混合架构如何演进？ |
| 2.3 | 近两年有哪些针对Transformer架构创新的评测基准与实证数据集？ | 哪些基准和数据集提供实证？ |
| 2.4 | 2024-2026年不同Transformer变体在推理效率与精度上有哪些对比改进？ | 推理效率与精度如何权衡？ |
| 2.5 | 2024-2026年Transformer架构创新在计算成本、泛化与可扩展性上有何局限？ | 计算成本、泛化与扩展有何局限？ |

## 生成提示词

```text
Use case: precise-object-edit / stylized-concept.
Asset type: a revised B1GONE homepage mascot hero concept, wide landscape 16:9, ideally 2400x1350.
Input image 1 is the edit target. Preserve the identity of its charming cream 2.5D chunky PIXEL ROBOT HEAD: ivory cuboid CRT-like shell, charcoal screen, two square pixel eyes, simple processing slot, restrained stepped voxel shading. Recompose the illustration into LEFT INPUT -> ROBOT -> RIGHT OUTPUT. Keep grey-dominant muted grey-blue background #8FA1A4 and cream #E7DEC5 with charcoal #202223. Use a clean flat grey-blue canvas and only a localized restrained pixel shadow below the floating head. No body, arms, legs, new mascot, glossy finish or neon.

Primary change: REMOVE EVERY LINE, LIGHT BEAM, RAY, CABLE, ARROW and old question label from the target image. Communicate the prism/dispersion metaphor ONLY WITH WORDS. No connectors, colored line bundles, literal rainbow arcs, triangle, bullet list, cards or rectangular text containers.

Composition: the original robot head is now near the horizontal center, slightly left of center, about 23% of canvas width, so there is real space for a black incoming prompt on its LEFT and a dense radiating word fan on its RIGHT. Keep original three-quarter view showing the face and right side. Incoming black prompt is on the viewer's LEFT, upright and large (not tiny caption), split over exactly two visually clear lines:
"Transformer 架构"
"最近两年内的创新"
The right end of this incoming text almost touches or slightly disappears into the head's left edge, clearly suggesting WORDS going directly into the machine. No incoming beam or arrow. Input letters are charcoal black, calm readable slightly pixelated Chinese type, around 40px equivalent on a 2400px-wide image.

Right output: ten different academic subquestions actually sampled from our research decomposition node and faithfully shortened for display. Render these exact ten labels ONCE EACH with accurate Chinese characters, no invented additional wording. They must be visibly larger than the labels in the reference, approximately 30-34px equivalent on a 2400px-wide image, restrained pixel-like type with good legibility. All ten text runs start close to the robot's right-side outlet, at subtly staggered distances, radiate across the right half like a spreading spectrum, fill a visually coherent DENSE WEDGE of colored WORDS. Their baselines have genuinely differing angles, e.g. upper rows rise diagonally (-34, -26, -18 degrees), middle rows approach horizontal (-12, -5, +2 degrees), lower rows descend (+9, +17, +25, +33 degrees). Vary the lengths and spacing organically while keeping every label readable with no overlaps. They must not look like ten parallel horizontal rows or a bullet list. Top-to-bottom color transitions through muted brick red, rust-orange, amber, mustard, olive, sage green, dusty teal, steel blue, indigo and violet. Colors are vibrant enough to distinguish the spectrum yet have the restrained 1970s instrument palette. It is the colored text that forms the dispersing sunlight/rainbow, without any drawn ray underneath.

Exact outgoing text from top to bottom:
"Transformer 有哪些基础性创新？"
"近两年有哪些新架构方法？"
"如何评测这些架构创新？"
"架构改进提升了哪些性能？"
"这些架构创新有哪些局限？"
"长序列与注意力机制有哪些创新？"
"稀疏、线性及混合架构如何演进？"
"哪些基准和数据集提供实证？"
"推理效率与精度如何权衡？"
"计算成本、泛化与扩展有何局限？"

The output text fan must originate to the viewer's RIGHT, with all wording fully on canvas. Allow the densest part near the outlet, progressively separating toward the right edge, taking advantage of each rotated line's different length; natural angular dispersion instead of rigid symmetry. Preserve whitespace above and below the overall illustration but no enormous empty gulf between mascot and questions.
Do not include UI chrome, menus, branding titles, watermark, captions, date labels, CRT screen effects, scanlines, particles, background texture, disco, synthwave, cyberpunk, reproduced album-cover art, literal optical prism, arrows or line beams. Output one coherent polished mascot-and-question composition.
```

## 去除残留线段的细化提示词

```text
Use case: precise-object-edit.
Image 1 is the edit target: the cream pixel robot with a black Transformer research prompt on the LEFT and ten colored subquestion text rows fanning out to the RIGHT.
Make ONE targeted correction: DELETE ALL THE SHORT COLORED LINE SEGMENTS between the head's right edge and the beginnings of the colored text. Fill those deleted segments with the surrounding grey-blue background. There must be no beam, ray, line, connector, colored stroke, arrow, colored dash or cable remaining anywhere. The spectrum must consist of Chinese QUESTION TEXT ONLY.
Preserve EVERY OTHER aspect exactly: the robot head and pixel eyes, its position and scale, the two-line black input on the left, all ten outgoing Chinese subquestions verbatim, every text color, typography, size, angle and position, the overall diagonal text fan, background and localized robot shadow, and wide 16:9 canvas. Do not shift or reflow any question text. Do not change the mascot or add anything. No new lines or graphic elements.
```
