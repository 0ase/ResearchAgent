# B1GONE 吉祥物 v9：上方文案靠近输入线

使用内置 imagegen 在 v8 上进一步收紧上方文案与黑色输入线的间距。最终图片为 b1gone-mascot-v9.png。

上方 TRANSFORMER / ARCHITECTURE: 整体下移，减少 ARCHITECTURE: 字底与黑线之间的空白。下方 WHAT'S NEW OVER / THE PAST TWO YEARS? 及四个子问题保留原有排版。英文文案、来源和完整翻译沿用 b1gone-mascot-v7-labels.json。保留此前版本。

## 编辑提示词

```text
Use case: precise-object-edit / text-layout micro-adjustment.
Image 1 is the edit target, the selected cream pixel robot with the black prompt split above and below a horizontal input line.

Make ONE change only: MOVE THE UPPER TWO-LINE BLACK TEXT GROUP DOWN so the bottom of "ARCHITECTURE:" sits immediately above the horizontal black input line, with only a very small gap of approximately 5–8 pixels on this 1536x1024 canvas.
The two-line group is:
"TRANSFORMER"
"ARCHITECTURE:"
Move both lines together as a single block, preserving their existing line spacing, exact left alignment, font size, bold angular uppercase letterforms, spelling and color. In the current target, the bottom of this upper block is around y=430 while the beam is around y=496. Move it down by approximately 55 pixels so the bottom of the letters of ARCHITECTURE: is near y=486–490, very close to the beam. The black beam should visually sit directly beneath ARCHITECTURE: like an underline, not separated by a large empty gap. Do not overlap or touch the glyph pixels with the beam.

Preserve everything else EXACTLY, especially:
- Keep the horizontal black beam at its current y position and thickness.
- Keep the lower two-line group "WHAT'S NEW OVER" / "THE PAST TWO YEARS?" at its existing position below the beam.
- Keep the robot head, ears, antenna, face and all pixel details unchanged.
- Keep all four colored bands and their English labels unchanged.
- Keep the same grey-blue background, 3:2 canvas and framing.
Do not change font size, line breaks, wording, colors or any other element. This is only a downward translation of the upper two-line text block to sit very close to the black line.
```

## 间距细化提示词

```text
Use case: precise-object-edit. Image 1 is the edit target.
There is STILL TOO MUCH GAP under "ARCHITECTURE:". Make one exact positioning correction:
Move ONLY the upper black two-line group "TRANSFORMER" / "ARCHITECTURE:" DOWN by about 24 pixels. The bottommost pixels of the letters in ARCHITECTURE: must be at y=487–488 in this 1536x1024 canvas, while the black input line remains starting around y=492. This means only THREE TO FOUR PIXELS of grey background between the letter bottoms and the black line. It must look tightly adjacent, nearly resting on the line, rather than separated by a 25–30px blank space. Preserve both lines' existing spacing, letter shapes, font size, exact x=43 left alignment and wording. Do not resize them.
Freeze all other elements exactly: the black beam, lower text below the beam, mascot, four colored rays and English labels, grey-blue background and canvas. Do not move the black line upward. Do not add an underline or line. Only translate the two upper text lines downward so ARCHITECTURE: is genuinely tight against the existing beam without overlapping it.
```

## 进一步收紧提示词

```text
Use case: precise local text-position edit.
Image 1 is the target. There is still a visible grey gap of around 15 pixels between the bottom of ARCHITECTURE: and the top of the black horizontal beam. REMOVE THAT GREY GAP.
Move the TWO upper black lines "TRANSFORMER" and "ARCHITECTURE:" together DOWN so ARCHITECTURE: rests directly on top of the existing black beam, with zero or at most ONE PIXEL of separation. Treat the existing beam as the baseline immediately beneath the letter bottoms. The bottom of ARCHITECTURE: should be FLUSH WITH THE TOP EDGE OF THE BLACK BEAM. Do not leave a grey strip between them. It is okay for the bottoms of the thick black letters to visually meet the top of the beam. Preserve letter shapes, size, left alignment and line spacing. Move the text, not the beam.
Everything else is frozen: black line height/thickness, below-line WHAT'S NEW OVER / THE PAST TWO YEARS?, all robot pixels and antenna, four colored beams and their captions, background and 3:2 canvas. Do not add text or anything else. Only remove the remaining gap by moving the upper text block down.
```
