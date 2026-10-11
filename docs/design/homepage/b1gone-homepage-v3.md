# B1GONE 首页效果图 v3

基于 b1gone-homepage-v2.png 使用内置 imagegen 编辑。最终图为 b1gone-homepage-v3.png，保留此前版本。

## 修改内容

- 以约 20% 的头部放大幅度作为生成目标，整体放大奶白机器人头、黑色轮廓、面罩、眼睛、笑脸、耳朵和天线，使角色更醒目。
- 调整黑色入射线及四条彩色子问题线束与头部的连接点。
- 放大初稿遮挡了英文提问末尾；第二次编辑将两块英文提问略向左调整，恢复完整文案和间距。
- 延续左侧布局、像素中文、顶部导航、研究输入框和开始研究按钮，以及灰蓝背景与轻微 CRT 效果。

仅修改静态效果图，没有改动前端页面代码、后端或 Git 提交。放大比例为图像生成的近似表达。

## 放大提示词

```text
Use case: precise-object-edit.
Image 1 is the EDIT TARGET: the latest B1GONE homepage screenshot.

Make one localized change: enlarge the central pixel robot's head by approximately 20%, making the mascot more prominent. Scale its cream head, stepped black outline, black visor, two cream eye bars, smile, side ears and orange antenna proportionally around the same existing head center. Preserve the same front-facing 2D pixel character, expression, proportions and crisp pixel edges. The head should be visibly larger, not merely taller or wider.

Reconnect the existing horizontal black input line to the enlarged LEFT ear and the existing FOUR colored outgoing wedges to the enlarged RIGHT ear. Only adjust the short connection endpoints as needed. The long black line remains perfectly horizontal at its current height and extends continuously to the left screen edge, separating the introductory text from the agent nodes. Keep the wedge endpoints and labels at their existing positions.

LOCK ALL OTHER ELEMENTS:
Keep the left B1GONE logo, introduction, five agent rows and their icons/rail exactly as they are.
Keep the navigation bar, 文档 / 设置 buttons and GitHub icon unchanged.
Keep the input English text and four output questions exactly as spelled and positioned, in their existing angular uppercase font. Keep all text fully legible, with clear separation from the larger head and no collisions.
Keep the cream question input field and 开始研究 button at the same positions and sizes.
Keep every Chinese pixel-art glyph, all text sizes and line breaks, the grey-blue canvas, charcoal/cream/ink palette and subtle CRT treatment unchanged.
Do not zoom the whole screenshot or enlarge the surrounding layout. No new elements, labels, arrows, character redesign, text changes, cropping or watermark. Only enlarge the robot head and fit the existing beam connections to it.
```

## 文字间距修复提示词

```text
Use case: precise-object-edit / text positioning repair.
Image 1 is the edit target, the B1GONE homepage with the ENLARGED pixel robot.

Keep the enlarged robot EXACTLY as shown, including its size, center, head shape, face, ears, antenna and all beam connections. Keep every other homepage element exactly unchanged.

Repair ONLY the incoming English question text. Its bottom line is currently partly hidden behind the enlarged head. Translate BOTH the above-beam and below-beam input text blocks LEFT by approximately 55 pixels, so their left edges are around x=632 rather than x=687 on the 1672px-wide image. Retain their current vertical positions, size, square-cut uppercase font, black color and two-line grouping. Restore the full text, visible and unoccluded:
Above the line:
"TRANSFORMER"
"ARCHITECTURE:"
Below the line:
"WHAT'S NEW OVER"
"THE PAST TWO YEARS?"

Leave at least a small clear gap between the last glyph and the enlarged robot. These blocks fit in the gap to the right of the LEFT column, without moving or touching any left-column copy. Do not shrink the font, rewrite the text, remove the question mark or change the robot.

LOCK EVERYTHING ELSE: B1GONE logo, all Chinese pixel type, introduction, five agent icons/rows, top black navigation, GitHub icon, grey-blue canvas and subtle CRT effects, continuous horizontal black line, four colored wedges and all output labels, cream input field and 开始研究 button and its ASCII ghosts. No new content, cropping or redesign.
```
