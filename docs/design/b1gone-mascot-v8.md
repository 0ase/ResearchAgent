# B1GONE 吉祥物 v8：输入文案上下分组

使用内置 imagegen 在选定的 v7 英文版本上调整输入文案。图片为 b1gone-mascot-v8.png。

将 TRANSFORMER / ARCHITECTURE: 放在线上方，将 WHAT'S NEW OVER / THE PAST TWO YEARS? 放在线下方。文案来源仍为 b1gone-mascot-v7-labels.json 中的真实拆解记录映射；保留四个英文子问题与原有字体风格。

## 编辑提示词

```text
Use case: precise-object-edit / text-layout adjustment.
Image 1 is the edit target: the selected front-facing cream pixel robot with four colored Transformer subquestions.

Make ONE local layout correction to the BLACK INPUT CAPTION on the LEFT. It currently has four lines all above the horizontal black input beam, making the upper area crowded.
Split it into TWO GROUPS around the beam:
ABOVE the black input beam, exactly these two lines:
"TRANSFORMER"
"ARCHITECTURE:"
BELOW the black input beam, exactly these two lines:
"WHAT'S NEW OVER"
"THE PAST TWO YEARS?"

Keep the same left alignment, bold uppercase square-corner geometric font, size, color and exact wording. Use calm balanced spacing: the upper two-line group ends with a comfortable gap above the beam; the lower two-line group begins with a comfortable gap below it. The beam remains between the two text groups, not underneath all four lines. Move only these black text lines vertically within the original left-side region, with the text fully clear of the head and left ear. Do not draw any new separator or underline.

Preserve EVERYTHING ELSE exactly:
- The front-facing cream pixel robot head, black outline/visor, two vertical cream eyes, smile, ears, orange antenna lamp, position, size and pixel-art rendering.
- The same straight horizontal black input beam at its current height, from the left into the left ear.
- Exactly four filled colored output wedges and labels, with identical angles, placement, colors, font size and wording:
"NEW ATTENTION" / "MECHANISMS?"
"NEW EFFICIENT" / "VARIANTS?"
"WHICH BENCHMARKS" / "AND DATASETS?"
"EFFICIENCY AND" / "ACCURACY GAINS?"
- The existing grey-blue background, 3:2 canvas, negative space and framing.
No added text, missing words, additional bands, arrows, connectors, new ports, robot changes, font changes or cropping. This is ONLY a vertical rearrangement of the four black input text lines into two lines above and two lines below the existing input beam.
```
