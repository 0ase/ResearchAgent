# B1GONE 首页吉祥物概念 v1

使用内置 imagegen 工具生成。本图为视觉概念，尚未接入首页。

- 形式：带轻微立体感的像素机器人头，奶白外壳、炭黑屏幕、两个方形眼睛。
- 画布：沿用用户提供的灰蓝配色。
- 光路：按用户文字描述，右上方的黑色研究问题进入；同侧下方输出四条彩色子问题，以分光隐喻问题拆解。
- 用色：暖红、赭黄、灰青、蓝色，保持复古仪器的气质。
- 图片：b1gone-mascot-v1.png。
- 后续接入时，可把输入问题、子问题和光路独立为 HTML/SVG 层，方便动态替换及移动端排版。

## 生成提示词

```text
Use case: stylized-concept.
Create a finished homepage mascot concept illustration for B1GONE, an academic research agent. Use the attached image as the exact flat background color reference: muted grey-blue #8FA1A4, grey dominant. Extend the color across a clean wide landscape 16:9 canvas.
Subject: one original retro pixel robot HEAD only, no body, in the center-left of the composition. A charming, intelligent, quiet 1970s laboratory-computer personality. A chunky ivory / warm cream #E7DEC5 cuboid shell, dark charcoal #202223 face display, two simple square pixel eyes, small understated processing slot. Minimal human features. Clear coarse pixel-art / voxel geometry, stepped silhouette, visible deliberate square pixels, limited-palette pixel shading that gives restrained 2.5D depth. Three-quarter view with the robot's right-side intake and output visible. No glossy plastic, no photoreal textures, no busy mechanical greebles. The mascot must be memorable and legible at small sizes.

Processing/prism concept and STRICT layout: the user wants BOTH the input and outputs on the VIEWER'S RIGHT of the head, separated vertically. Do NOT put the input on the left. A single thin black horizontal stream comes from the upper-right, points LEFT into an upper port on the head's right side. On that incoming black stream, place a small, understated black research prompt in readable pixel-like Chinese type: "如何提高文献筛选的相关性？". Below the intake, four clean colored rays EXIT a separate lower port on the same right side of the head and spread diagonally to the right in a fan, visually expressing one research question decomposed into four subquestions, a restrained homage to Newton's dispersion experiment and the prism/light metaphor. Keep the input line ABOVE the output fan with ample separation so the pathways do not cross. Each outgoing ray is made of crisp pixel steps or tiny connected square blocks, with a small direction cue pointing away from the head. Use warm burnt red, amber ochre, dusty teal, and muted cornflower blue; make these clearly colorful but harmonious with a 70s instrument palette rather than neon. At the far ends of the four colored rays place small lightweight Chinese subquestion labels, each in its corresponding ray color, exactly:
"如何定义相关性？"
"哪些元数据有帮助？"
"如何设计评分维度？"
"如何验证筛选效果？"
The labels should feel like research text being transmitted, not cards or UI buttons.

Composition: airy, graphic, bold simple silhouette, plenty of flat untouched grey-blue negative space around the robot and all five streams. The robot head occupies approximately one quarter of canvas width; beams and text are subordinate to the mascot but clearly readable. Very soft limited pixel shadow immediately under the floating head is acceptable. Do not add headline, brand wordmark, captions, decorative logo, cards, panels, borders, starfield, particles, scanner overlays, glowing bloom, cyberpunk, synthwave, disco, a literal triangular prism, or any copied album-cover composition. This is a fresh robot-and-research interpretation, not a reconstruction of an album cover. Output one coherent illustration, not a comparison board.
```

## 背景细化提示词

```text
Use case: lighting-weather / precise background refinement.
Image 1 is the edit target: the B1GONE pixel robot head concept with black incoming research prompt on the upper right and four colored outgoing subquestions on the lower right. Image 2 is the user's exact solid grey-blue background swatch.
Make ONE targeted change to Image 1: replace the backdrop with a perfectly uniform, flat, opaque grey-blue #8FA1A4 matching Image 2. Remove all full-canvas texture, haze, mottling, gradient, vignette, glow and ambient background shading. The outer margins should be the same solid color on every side.
Preserve the robot head's silhouette, cream shell, pixel eyes, 2.5D pixel shading, every beam and arrow, their directions and layout, all five Chinese question texts, font and colors, and the target image's existing wide aspect ratio. Keep only the localized blocky pixel shadow immediately underneath the floating head; do not spread its shading across the background.
Do not add any element, border, title, wordmark, card, body, limb or screen effect. This is a faithful background cleanup of the existing illustration, not a redesign.
```
