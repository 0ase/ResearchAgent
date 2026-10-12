# B1GONE 首页吉祥物概念 v4

使用内置 imagegen 对 v3 进行接线口与透视调整。概念图保存为 b1gone-mascot-v4.png，保留此前版本。

- 去掉左侧外露接线口，恢复完整的奶白轮廓；入射线在机器人左侧轮廓处被遮挡。
- 输入射线由左侧向右略向下倾斜，输入问题文字随射线方向倾斜。
- 右侧只保留一个位于侧面中央的凹入式输出口，其轮廓沿侧面的透视方向。
- 四条彩色射线从同一输出口中心展开，箭头与对应问题文字分别沿射线方向调整。
- 保留原有四个视觉示例子问题、像素机器人、灰蓝背景及奶白与炭黑配色。
- 本次产物为首页视觉概念。

## 编辑提示词

```text
Use case: precise-object-edit.
Asset type: B1GONE retro pixel mascot homepage concept.
Image 1 is the edit target. Correct ONLY its port geometry and spatial perspective while preserving the original mascot, four question texts, palette, and wide landscape composition.

Preserve the current original cream 2.5D voxel/pixel robot head, dark charcoal face, its two cream square eyes, three lower buttons, processing slot, approximate size and location, grey-blue backdrop, restrained localized pixel shadow and clean 1970s computer character. No body or limbs. Use the existing three-quarter camera: FRONT face and RIGHT side are visible; the LEFT side is occluded by the front silhouette. Do not rotate the head to show a left side, and do not mirror it.

Required port correction:
1. REMOVE the protruding intake socket on the viewer's LEFT completely. Repair the cream shell and left silhouette into a clean continuous shape. There must be NO visible left socket, left black rectangle, connector, rim, hole or protruding adapter. The input reaches the hidden left side; the head's silhouette naturally occludes its termination.
2. On the visible RIGHT SIDE retain EXACTLY ONE dark recessed output opening. Remove both existing upper/lower ports and create ONE small square opening centered on that visible right side face, midway up its height and centered within the side panel. The port's outline is foreshortened to the right-face perspective: its top/bottom edges follow the same receding directions as the cuboid shell, its vertical edges follow the shell verticals. It is a recessed opening, not a flat front-facing pasted square, not a protruding connector. No second port. Restore uninterrupted cream shell above and below.

Required perspective correction:
Treat black input, robot and colored output as ONE coherent 3D optical scene under the same camera, not flat screen-space graphics pasted around a 3D head.
- The black incoming beam comes from the LEFT at a subtle nonzero angle, roughly 6–10 degrees descending toward the right in the image, and disappears behind the head's LEFT silhouette near its mid-height. It should head toward the interior center of the head; no beam is drawn across the robot's face. A rightward arrow cue, if used, follows this diagonal axis and is naturally occluded at the silhouette, without an intake fitting.
- The black incoming text "如何提高文献筛选的相关性？" sits just above and follows the incoming ray's diagonal baseline, with subtle consistent perspective/foreshortening. Keep it legible, calm, pixel-like and on canvas. No horizontal text floating independently of the ray direction.
- All FOUR colored rays originate at ONE EXACT COMMON POINT at the center of the single right-side output opening. That point is visibly on the side plane, not in mid-air in front of or below the socket.
- Four straight rays spread out to the viewer's RIGHT in a natural projected fan: red slightly upward, amber near the central outgoing axis, teal gently downward, blue further downward. They are genuinely straight geometric rays; stepped square pixels depict diagonal raster edges, NOT bent wires or dogleg connectors. Their projected directions are compatible with the cuboid camera and the incident beam passing through the head. No ray starts at a second point.
- Their pixel arrowheads align with their respective ray directions in perspective; do not use four identical horizontal arrowheads on diagonal rays.
- At each outgoing ray's end, the matching colored subquestion follows that ray's projected baseline/plane, with subtle believable 3D foreshortening and the SAME overall camera as the robot. The four labels should have slightly different angles corresponding to the different outgoing rays, not four perfectly horizontal screen-aligned labels. Prioritize accurate readable Chinese letters. No excessive rotation, distortion or tiny text.
- All four rays and text are fully to the right of the robot and fully within the canvas with margins; no line pierces the visible face.

Exact output text, ONCE each:
rust red: "如何定义相关性？"
ochre amber: "哪些元数据有帮助？"
dusty teal: "如何设计评分维度？"
muted blue: "如何验证筛选效果？"

Keep all existing cream #E7DEC5, charcoal #202223, grey-dominant grey-blue #8FA1A4, and the four muted retro spectrum colors. No redesign, new text, brand title, UI, literal prism, sparkle, glow, cyberpunk, neon or dramatic lighting. This is a targeted optical-perspective correction of the existing concept, with a clean socket-free hidden left side and exactly one central right-side output aperture.
```
