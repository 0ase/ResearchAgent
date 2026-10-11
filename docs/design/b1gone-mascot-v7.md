# B1GONE 选定吉祥物：英文 Transformer 用例

用户选定本次附图中的正面 2D 像素机器人作为吉祥物样式。保留奶白圆角像素头、黑色面罩与外轮廓、竖向眼睛、微笑和橙色天线灯。

本次使用内置 imagegen 替换原音乐示例文案，并将输出从五个减少为四个。字体参照附图中的全大写方角几何字形，采用分行排版。

- 原始参考：b1gone-mascot-selected-reference.png。
- 英文版本：b1gone-mascot-v7.png。
- 英文文案与来源映射：b1gone-mascot-v7-labels.json。
- 原始实际拆解记录：b1gone-mascot-v2-questions.json，第二轮第 1–4 个查询。
- 研究时间范围：2024-10-11 至 2026-10-11；图中用 THE PAST TWO YEARS 表达原用例。
- 输出颜色：橙红、黄色、青蓝、紫色，共四条光带和四个问题。
- 图中文字采用英文展示简写，完整中文原查询与完整英文翻译见下表。实际拆解仅为子查询生成，不是论文检索结果或研究结论。
- 本次生成并保存设计素材，尚未接入首页。

## 输入文案

```text
TRANSFORMER
ARCHITECTURE:
WHAT'S NEW OVER
THE PAST TWO YEARS?
```

## 四个子问题

| 原始采样轮次与序号 | 原始模型子查询 | 完整英文翻译 | 图中分行简写 |
| --- | --- | --- | --- |
| 2.1 | 2024-2026年Transformer在长序列建模与注意力机制方面有哪些基础性创新？ | What innovations in long-sequence modeling and attention mechanisms have emerged in Transformer architectures from 2024 to 2026? | NEW ATTENTION / MECHANISMS? |
| 2.2 | 2024-2026年Transformer稀疏化、线性化及混合架构等高效变体有哪些新方法？ | What new methods have emerged in efficient Transformer variants, including sparse, linear and hybrid architectures, from 2024 to 2026? | NEW EFFICIENT / VARIANTS? |
| 2.3 | 近两年有哪些针对Transformer架构创新的评测基准与实证数据集？ | Which benchmarks and empirical datasets evaluate Transformer architecture innovations over the past two years? | WHICH BENCHMARKS / AND DATASETS? |
| 2.4 | 2024-2026年不同Transformer变体在推理效率与精度上有哪些对比改进？ | How have different Transformer variants improved inference efficiency and accuracy from 2024 to 2026? | EFFICIENCY AND / ACCURACY GAINS? |

## 编辑提示词

```text
Use case: text-localization and precise-object-edit.
Asset type: selected B1GONE homepage mascot illustration.
Input image 1 is the user's SELECTED MASCOT AND DESIGN. Preserve THIS image's flat FRONT-FACING 2D pixel robot EXACTLY: cream rounded-square stepped pixel head with heavy black outline, simple black face visor, two cream vertical rectangular eyes, small black smiling pixel mouth, left and right cream ear disks within black borders, black antenna stem with orange square indicator. Preserve its identity, frontal orientation, size, position and flat pixel-art rendering. Do not substitute any earlier 3D CRT mascot.

The user chooses this design and wants ONLY to change its research text to a real Transformer example, translated into English, and reduce five output subquestions to EXACTLY FOUR.

TYPOGRAPHY: Match the provided image's distinctive BOLD UPPERCASE squared geometric retro computer lettering, with angular square-cut corners and uniform blocky strokes. The black input and colored labels must look like the same font as the attached image. Do not replace it with a generic sans serif, a serif, rounded lettering, cursive, or thin monospace. Match existing visual font size as closely as practical, using the specified line breaks for longer copy. No Chinese text.

INPUT:
Remove "HOW DOES MUSIC AFFECT MEMORY?" entirely.
Replace with EXACTLY these four lines of black text, positioned in the left text area above the existing straight black input line:
"TRANSFORMER"
"ARCHITECTURE:"
"WHAT'S NEW OVER"
"THE PAST TWO YEARS?"
Together they form the input "TRANSFORMER ARCHITECTURE: WHAT'S NEW OVER THE PAST TWO YEARS?".
Keep all four lines comfortably within the existing left-side area. The last line must stay above the black input beam. Preserve the existing straight horizontal black input beam reaching the robot's left ear; no arrows. Enough vertical space exists to stack the four lines above the beam, without shifting or shrinking the robot.

OUTPUT:
Remove ALL the old music-related output labels and all five original color bands.
Render EXACTLY FOUR filled colored wedge-like light bands, all originating from the same point at the robot's right ear, fanning toward the right. Preserve the original image's simple broad filled triangular/tapered beam style (not thin wires, not curved cables, not arrowheads).
Use four retained original-spectrum colors, top to bottom: vivid orange-red, golden yellow, teal blue, violet purple. Fan them at balanced separated angles within the original spread. No fifth green band.
At the far right end of each color band, place one accurate matching-color uppercase label, in the reference image's font, using exactly these TWO-LINE labels from top to bottom:
orange-red:
"NEW ATTENTION"
"MECHANISMS?"
golden-yellow:
"NEW EFFICIENT"
"VARIANTS?"
teal blue:
"WHICH BENCHMARKS"
"AND DATASETS?"
violet purple:
"EFFICIENCY AND"
"ACCURACY GAINS?"
Every label appears exactly once, total FOUR labels. These represent faithful short display translations of four actual research decomposition queries. Do not invent any fifth question. Ensure every word and question mark is spelled correctly and fully visible, with comfortable right margins. Labels remain upright, arranged similarly to the original image, with enough spacing between the two-line blocks.

INVARIANTS:
Keep the selected front-facing robot character, cream/black/orange details, grey-blue backdrop, original overall composition, ample negative space and calm retro look. Keep a wide landscape canvas. Reflow only text and the four output wedges as needed to fit the English translations. No headline, B1GONE wordmark, watermark, dates, UI, extra characters, extra ports, glow, arrows, wires, textured cables, 3D mascot or Chinese. Output a faithful English Transformer research variant of the selected reference.
Preserve the reference image's approximately 3:2 landscape aspect ratio and relative head placement. Do not crop any part of the mascot or captions.
```
