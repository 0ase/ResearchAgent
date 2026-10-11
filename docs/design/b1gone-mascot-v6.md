# B1GONE 首页吉祥物概念 v6

使用内置 imagegen 对 v5 的黑色输入线末端做局部平顺处理；概念图保存为 b1gone-mascot-v6.png，保留此前版本。

去掉紧邻机器人左侧轮廓的向上回弯，让末端近似水平地平顺延伸至机器人边缘。继续保留右侧柔软彩色线束、单个居中的输出口、原有机器人与问题文案。本图为首页视觉概念。

## 编辑提示词

```text
Use case: precise-object-edit.
Image 1 is the clean edit target, the current B1GONE pixel robot with a black incoming strand and four colored outgoing strands.
Make ONE VERY SMALL LOCAL CORRECTION to the black input line ONLY. In the reference canvas of 1672x940, the last roughly 100–120 pixels of the black line immediately before the robot's left edge (around x=490 to x=605, y=370–385) currently curl UPWARD. Remove that upturn entirely. Continue that short segment smoothly and almost HORIZONTALLY from the preceding strand into the robot's left silhouette, around the same height as the strand just before the upturn. It must be a calm straight continuation, with no curve, upward curl, elbow, kink, hook, bump, downward droop or new connector near the head. The line disappears behind the robot silhouette. Keep the original line thickness and charcoal color, with clean restrained pixel edges.

Change NOTHING ELSE:
- Preserve the black input strand before this final segment, its overall very shallow angle and location.
- Preserve every Chinese question letter, its size, position, baseline, font and color.
- Preserve all FOUR gently curved colored output strands exactly, their locations, endpoints, colors and the single centered right-side port.
- Preserve the cream pixel robot's exact silhouette, pose, scale, location, dark face, eyes, processing slot, buttons and shadow.
- Preserve the grey-blue background, wide canvas, composition, lighting and all other pixels as faithfully as possible.
- Do not add arrows, left intake sockets, additional ports, labels or any elements.
Do not add the user's red annotation circle; the output must be a clean illustration without annotations. This is ONLY a cleanup of the short black line segment right beside the robot.
```
