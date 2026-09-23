import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

import {
  PERSPECTIVE_CONTRACT,
  RESEARCH_POSES,
  RESEARCH_STATES,
  renderPropPerspectiveSvg,
  renderResearchFrame,
  renderTurnaroundOverlaySvg,
  renderTurnaroundReferenceSvg,
} from "./research-pet-poses.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const outputDir = path.resolve(scriptDir, "../public/pets/research-bot");
const sourceDir = path.join(outputDir, "source");
const rowsDir = path.join(outputDir, "rows");
const qaDir = path.join(outputDir, "qa");
const cellWidth = 192;
const cellHeight = 208;
const columns = 8;

const animations = [
  ["idle", 6, 260],
  ["orchestrate", 8, 200],
  ["search", 8, 140],
  ["filter", 6, 180],
  ["read", 8, 220],
  ["analyze", 8, 180],
  ["synthesize", 8, 160],
  ["critic", 6, 220],
  ["dragging", 4, 120],
  ["completed", 8, 120],
  ["failed", 6, 260],
];

await Promise.all([
  mkdir(sourceDir, { recursive: true }),
  mkdir(rowsDir, { recursive: true }),
  mkdir(qaDir, { recursive: true }),
]);

const frames = [];
for (let row = 0; row < animations.length; row += 1) {
  const [state, frameCount, duration] = animations[row];
  const rowFrames = [];
  for (let frame = 0; frame < frameCount; frame += 1) {
    const svg = RESEARCH_STATES.includes(state)
      ? renderResearchFrame(state, frame)
      : legacyRobotSvg(state, frame, frameCount);
    rowFrames.push(await sharp(Buffer.from(svg)).png().toBuffer());
  }
  frames.push(rowFrames);

  const strip = await transparentCanvas(cellWidth * columns, cellHeight)
    .composite(
      rowFrames.map((input, left) => ({
        input,
        left: left * cellWidth,
        top: 0,
      })),
    )
    .webp({ quality: 92, alphaQuality: 100, smartSubsample: true })
    .toBuffer();
  await writeFile(
    path.join(rowsDir, `${String(row).padStart(2, "0")}-${state}.webp`),
    strip,
  );

  const animated = await sharp({
    create: {
      width: cellWidth,
      height: cellHeight * frameCount,
      pageHeight: cellHeight,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  })
    .composite(
      rowFrames.map((input, index) => ({
        input,
        left: 0,
        top: index * cellHeight,
      })),
    )
    .gif({ loop: 0, delay: Array(frameCount).fill(duration), effort: 7 })
    .toBuffer();
  await writeFile(
    path.join(qaDir, `${String(row).padStart(2, "0")}-${state}.gif`),
    animated,
  );
}

const atlasComposites = frames.flatMap((rowFrames, row) =>
  rowFrames.map((input, column) => ({
    input,
    left: column * cellWidth,
    top: row * cellHeight,
  })),
);
const spritesheet = await transparentCanvas(
  cellWidth * columns,
  cellHeight * animations.length,
)
  .composite(atlasComposites)
  .webp({ quality: 92, alphaQuality: 100, smartSubsample: true })
  .toBuffer();
await writeFile(path.join(outputDir, "spritesheet.webp"), spritesheet);

const preview = await sharp(frames[0][0])
  .resize(96, 104)
  .webp({ quality: 88, alphaQuality: 100 })
  .toBuffer();
await writeFile(path.join(outputDir, "preview.webp"), preview);

const checker = checkerSvg(cellWidth * columns, cellHeight * animations.length);
const contactSheet = await sharp(Buffer.from(checker))
  .composite([{ input: spritesheet }, { input: Buffer.from(gridSvg()) }])
  .png()
  .toBuffer();
await writeFile(path.join(qaDir, "contact-sheet.png"), contactSheet);
await writeFile(
  path.join(sourceDir, "canonical-base.svg"),
  legacyRobotSvg("idle", 0, 6).replace(/[ \t]+$/gm, ""),
);
await Promise.all([
  writeFile(
    path.join(sourceDir, "turnaround.svg"),
    renderTurnaroundReferenceSvg(),
  ),
  writeFile(
    path.join(sourceDir, "prop-perspective.svg"),
    renderPropPerspectiveSvg(),
  ),
  writeFile(
    path.join(sourceDir, "perspective-guide.json"),
    `${JSON.stringify(PERSPECTIVE_CONTRACT, null, 2)}\n`,
  ),
  writeFile(
    path.join(sourceDir, "motion-choreography.json"),
    `${JSON.stringify(RESEARCH_POSES, null, 2)}\n`,
  ),
]);

const posterFrames = await Promise.all(
  RESEARCH_STATES.map(async (state, index) => {
    const frame = RESEARCH_POSES[state].findIndex((spec) => spec.poster);
    return sharp(frames[index + 1][frame])
      .resize(72, 78)
      .png()
      .toBuffer();
  }),
);
const posterSheet = await transparentCanvas(72 * RESEARCH_STATES.length, 78)
  .composite(
    posterFrames.map((input, index) => ({ input, left: index * 72, top: 0 })),
  )
  .png()
  .toBuffer();
await writeFile(path.join(qaDir, "poster-contact-sheet.png"), posterSheet);

const debugFrames = await Promise.all(
  RESEARCH_STATES.map(async (state) => {
    const frame = RESEARCH_POSES[state].findIndex((spec) => spec.poster);
    return sharp(
      Buffer.from(renderResearchFrame(state, frame, { debug: true })),
    )
      .png()
      .toBuffer();
  }),
);
const contactPoints = await sharp(
  Buffer.from(checkerSvg(cellWidth * RESEARCH_STATES.length, cellHeight)),
)
  .composite(
    debugFrames.map((input, index) => ({
      input,
      left: index * cellWidth,
      top: 0,
    })),
  )
  .png()
  .toBuffer();
await writeFile(path.join(qaDir, "contact-points.png"), contactPoints);

const turnaroundOverlay = await sharp(Buffer.from(renderTurnaroundOverlaySvg()))
  .png()
  .toBuffer();
await writeFile(path.join(qaDir, "turnaround-overlay.png"), turnaroundOverlay);

function transparentCanvas(width, height) {
  return sharp({
    create: {
      width,
      height,
      channels: 4,
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    },
  });
}

function legacyRobotSvg(state, frame, frameCount) {
  const phase = (frame / frameCount) * Math.PI * 2;
  const bob =
    state === "completed"
      ? -Math.round(Math.abs(Math.sin(phase)) * 16)
      : Math.round(Math.sin(phase) * 2);
  const dragging = state === "dragging";
  const failed = state === "failed";
  const completed = state === "completed";
  const antennaShift =
    state === "search"
      ? Math.round(Math.sin(phase) * 10)
      : failed
        ? 12
        : Math.round(Math.sin(phase) * 2);
  const blink = state === "idle" && frame === frameCount - 1;
  const screen = completed ? "#16855B" : failed ? "#B65D3A" : "#24B8C7";
  const armLift = completed && frame % 2 === 1;
  const tablet = tabletContent(state, frame, frameCount);

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${cellWidth}" height="${cellHeight}" viewBox="0 0 192 208">
  <g id="shadow" opacity=".14"><ellipse cx="96" cy="186" rx="39" ry="8" fill="#17283A"/></g>
  <g id="antenna" transform="translate(0 ${bob})" stroke="#334A60" stroke-width="6" stroke-linecap="round">
    <path d="M96 47 L${96 + antennaShift} 25"/><circle cx="${96 + antennaShift}" cy="21" r="7" fill="#24B8C7" stroke="#334A60" stroke-width="4"/>
  </g>
  <g id="body" transform="translate(0 ${bob})">
    <rect x="57" y="82" width="78" height="82" rx="28" fill="#E8F4F7" stroke="#334A60" stroke-width="6"/>
    <rect x="64" y="48" width="64" height="53" rx="22" fill="#F7FBFC" stroke="#334A60" stroke-width="6"/>
    <rect x="72" y="60" width="48" height="27" rx="10" fill="${screen}"/>
    ${blink ? `<path d="M82 74h8M102 74h8" stroke="#173244" stroke-width="4" stroke-linecap="round"/>` : `<circle cx="86" cy="73" r="4" fill="#173244"/><circle cx="106" cy="73" r="4" fill="#173244"/>`}
    <path d="M72 151v${dragging ? 12 : 25}M120 151v${dragging ? 12 : 25}" stroke="#334A60" stroke-width="8" stroke-linecap="round"/>
    <path d="M60 106l-${armLift ? 15 : dragging ? 3 : 12} ${armLift ? -22 : dragging ? 16 : 22}M132 106l${armLift ? 18 : dragging ? 3 : 12} ${armLift ? -27 : dragging ? 16 : 22}" stroke="#334A60" stroke-width="8" stroke-linecap="round"/>
    <circle cx="96" cy="116" r="7" fill="#6D84D8"/>
  </g>
  ${state === "idle" || state === "dragging" || completed || failed ? "" : `<g id="tablet" transform="translate(0 ${bob})"><rect x="58" y="112" width="76" height="49" rx="7" fill="#253A50" stroke="#334A60" stroke-width="5"/><rect x="65" y="119" width="62" height="34" rx="3" fill="#DDF6F7"/>${tablet}</g>`}
  ${failed ? `<g id="failed-tablet" transform="translate(0 ${bob})"><path d="M70 134l52 23" stroke="#334A60" stroke-width="7" stroke-linecap="round"/></g>` : ""}
  </svg>`;
}

function tabletContent(state, frame, frameCount) {
  const pulse = frame % 3;
  if (state === "orchestrate") {
    return `<g fill="#6D84D8" stroke="#6D84D8" stroke-width="2"><circle cx="78" cy="135" r="4"/><circle cx="96" cy="126" r="4"/><circle cx="114" cy="139" r="4"/><path d="M81 133l11-5M100 128l10 8" fill="none"/></g>`;
  }
  if (state === "search") {
    const x = 74 + Math.round((frame / Math.max(1, frameCount - 1)) * 38);
    return `<path d="M72 128h45M72 138h45M72 147h30" stroke="#8CB9C2" stroke-width="3"/><circle cx="${x}" cy="134" r="8" fill="none" stroke="#24B8C7" stroke-width="3"/><path d="M${x + 6} 140l6 6" stroke="#24B8C7" stroke-width="3"/>`;
  }
  if (state === "filter") {
    return `<path d="M96 121v30" stroke="#8CB9C2" stroke-width="2"/><rect x="72" y="${125 + pulse * 4}" width="14" height="8" rx="2" fill="#6D84D8"/><rect x="106" y="${139 - pulse * 4}" width="14" height="8" rx="2" fill="#24B8C7"/>`;
  }
  if (state === "read") {
    return `<path d="M96 124c-7-5-15-5-24-2v25c9-3 17-2 24 3 7-5 15-6 24-3v-25c-9-3-17-3-24 2z" fill="#FFF" stroke="#8CB9C2" stroke-width="2"/><path d="M96 124v26" stroke="#8CB9C2" stroke-width="2"/><path d="M76 ${130 + pulse * 5}h14M102 ${130 + pulse * 5}h14" stroke="#6D84D8" stroke-width="2"/>`;
  }
  if (state === "analyze") {
    return `<rect x="72" y="${142 - pulse * 4}" width="8" height="8" fill="#6D84D8"/><rect x="84" y="132" width="8" height="18" fill="#24B8C7"/><rect x="101" y="127" width="8" height="23" fill="#6D84D8"/><rect x="113" y="${135 + pulse * 3}" width="8" height="15" fill="#24B8C7"/>`;
  }
  if (state === "synthesize") {
    const count = 1 + (frame % 4);
    return Array.from(
      { length: count },
      (_, index) =>
        `<rect x="${72 + (index % 2) * 24}" y="${124 + Math.floor(index / 2) * 14}" width="19" height="9" rx="2" fill="${index % 2 ? "#24B8C7" : "#6D84D8"}"/>`,
    ).join("");
  }
  if (state === "critic") {
    return `<path d="M72 128h29M72 139h29M72 149h29" stroke="#8CB9C2" stroke-width="3"/><path d="M108 128l3 3 6-7M108 141l3 3 6-7" fill="none" stroke="#16855B" stroke-width="3" stroke-linecap="round"/><circle cx="114" cy="144" r="10" fill="none" stroke="#6D84D8" stroke-width="3"/>`;
  }
  return "";
}

function checkerSvg(width, height) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><defs><pattern id="c" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="24" height="24" fill="#f3f6f8"/><rect width="12" height="12" fill="#e3e9ed"/><rect x="12" y="12" width="12" height="12" fill="#e3e9ed"/></pattern></defs><rect width="100%" height="100%" fill="url(#c)"/></svg>`;
}

function gridSvg() {
  const width = cellWidth * columns;
  const height = cellHeight * animations.length;
  const lines = [];
  for (let x = 0; x <= width; x += cellWidth)
    lines.push(`<path d="M${x} 0v${height}"/>`);
  for (let y = 0; y <= height; y += cellHeight)
    lines.push(`<path d="M0 ${y}h${width}"/>`);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><g fill="none" stroke="#536474" stroke-opacity=".35" stroke-width="2">${lines.join("")}</g></svg>`;
}
