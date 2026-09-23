import { createHash } from "node:crypto";
import { access, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

import {
  PERSPECTIVE_CONTRACT,
  RESEARCH_POSES,
  RESEARCH_STATES,
} from "./research-pet-poses.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "../public/pets/research-bot");
const manifest = JSON.parse(
  await readFile(path.join(root, "manifest.json"), "utf8"),
);
const atlasPath = path.join(root, "spritesheet.webp");
const previewPath = path.join(root, "preview.webp");
await Promise.all([
  access(atlasPath),
  access(previewPath),
  access(path.join(root, "source", "turnaround.svg")),
  access(path.join(root, "source", "prop-perspective.svg")),
  access(path.join(root, "source", "perspective-guide.json")),
  access(path.join(root, "source", "motion-choreography.json")),
  access(path.join(root, "qa", "poster-contact-sheet.png")),
  access(path.join(root, "qa", "contact-points.png")),
  access(path.join(root, "qa", "turnaround-overlay.png")),
]);

const atlas = sharp(atlasPath);
const metadata = await atlas.metadata();
const atlasSpec = {
  width: manifest.cell.width * manifest.grid.columns,
  height: manifest.cell.height * manifest.grid.rows,
  cellWidth: manifest.cell.width,
  cellHeight: manifest.cell.height,
  columns: manifest.grid.columns,
  rows: manifest.grid.rows,
};
assert(
  metadata.width === atlasSpec.width,
  `atlas width must be ${atlasSpec.width}`,
);
assert(
  metadata.height === atlasSpec.height,
  `atlas height must be ${atlasSpec.height}`,
);
assert(metadata.hasAlpha, "atlas must include an alpha channel");
assert((await stat(atlasPath)).size <= 2 * 1024 * 1024, "atlas must be <= 2MB");
assert((await stat(previewPath)).size <= 50 * 1024, "preview must be <= 50KB");

const seenRows = new Set();
for (const [name, spec] of Object.entries(manifest.states)) {
  assert(
    Number.isInteger(spec.row) && spec.row >= 0 && spec.row < atlasSpec.rows,
    `${name}: invalid row`,
  );
  assert(!seenRows.has(spec.row), `${name}: duplicate row ${spec.row}`);
  seenRows.add(spec.row);
  assert(
    Number.isInteger(spec.frameCount) &&
      spec.frameCount >= 1 &&
      spec.frameCount <= atlasSpec.columns,
    `${name}: invalid frameCount`,
  );
  assert(
    Number.isInteger(spec.posterFrame) &&
      spec.posterFrame >= 0 &&
      spec.posterFrame < spec.frameCount,
    `${name}: invalid posterFrame`,
  );

  for (let column = 0; column < atlasSpec.columns; column += 1) {
    const frameBuffer = await sharp(atlasPath)
      .extract({
        left: column * atlasSpec.cellWidth,
        top: spec.row * atlasSpec.cellHeight,
        width: atlasSpec.cellWidth,
        height: atlasSpec.cellHeight,
      })
      .png()
      .toBuffer();
    const stats = await sharp(frameBuffer).stats();
    const alpha = stats.channels[3];
    assert(alpha, `${name}/${column}: alpha channel missing`);
    if (column < spec.frameCount) {
      assert(alpha.max > 0, `${name}/${column}: used frame is empty`);
      if (RESEARCH_STATES.includes(name)) {
        const bounds = await alphaBounds(frameBuffer);
        assert(bounds, `${name}/${column}: missing alpha bounds`);
        assert(
          bounds.left >= PERSPECTIVE_CONTRACT.safeBounds.left &&
            bounds.top >= PERSPECTIVE_CONTRACT.safeBounds.top &&
            bounds.right <= PERSPECTIVE_CONTRACT.safeBounds.right &&
            bounds.bottom <= PERSPECTIVE_CONTRACT.safeBounds.bottom,
          `${name}/${column}: artwork ${JSON.stringify(bounds)} escapes safe bounds`,
        );
      }
    } else {
      assert(
        alpha.max === 0,
        `${name}/${column}: unused frame must be transparent`,
      );
    }
  }
}

for (const state of RESEARCH_STATES) {
  const poses = RESEARCH_POSES[state];
  const manifestSpec = manifest.states[state];
  assert(
    poses.length === manifestSpec.frameCount,
    `${state}: pose count must match manifest frameCount`,
  );
  const posterIndex = poses.findIndex((pose) => pose.poster);
  assert(
    posterIndex === manifestSpec.posterFrame,
    `${state}: poster pose ${posterIndex} must match manifest posterFrame ${manifestSpec.posterFrame}`,
  );
  assert(
    poses[0].loopAnchor && poses[0].loopAnchor === poses.at(-1).loopAnchor,
    `${state}: first and last frames must share a loop anchor`,
  );

  for (let index = 0; index < poses.length; index += 1) {
    const current = poses[index];
    const next = poses[(index + 1) % poses.length];
    assert(
      Math.abs(current.dx) <= PERSPECTIVE_CONTRACT.maxBodyShiftX,
      `${state}/${index}: body shift exceeds contract`,
    );
    assert(
      Math.abs(current.lean) <= PERSPECTIVE_CONTRACT.maxBodyLeanDeg,
      `${state}/${index}: body lean exceeds contract`,
    );
    assert(
      current.baselineY === PERSPECTIVE_CONTRACT.baselineY,
      `${state}/${index}: baseline must stay at ${PERSPECTIVE_CONTRACT.baselineY}`,
    );
    assert(
      current.view === next.view ||
        current.view === "front" ||
        next.view === "front",
      `${state}/${index}: ${current.view} cannot jump directly to ${next.view}`,
    );
  }
}

const lockedArtifactHashes = {
  "rows/00-idle.webp":
    "8D80FE429D0104370449FEFA6696ABD00513BF7948FEF4969E6EB3892FAAA1EE",
  "rows/08-dragging.webp":
    "8A7D450EA8B43BA35E289279B3F07AF8061DAF7763DFB01061E58CFCA6EE29DF",
  "rows/09-completed.webp":
    "AEFD2271325DDC6A6FAE1631FF4E247F5B0F3DA2E7681187B787218F0A958CD3",
  "rows/10-failed.webp":
    "C8763D295A00DAC43B125BD2CC1FAAD84DEBE56B609D8CAA2B8288C2B3BA03A9",
  "preview.webp":
    "A699A4B6D3CD8A71378C3CA81DC3E29FF6DD972C2A9DFD09E9248D1139C97733",
};
for (const [relativePath, expected] of Object.entries(lockedArtifactHashes)) {
  const actual = await sha256(path.join(root, relativePath));
  assert(
    actual === expected,
    `${relativePath}: unchanged artifact hash mismatch (${actual})`,
  );
}

assert(
  seenRows.size === atlasSpec.rows,
  "manifest must define every atlas row",
);
process.stdout.write(
  `Validated ${Object.keys(manifest.states).length} pet animations in ${atlasSpec.width}x${atlasSpec.height} atlas.\n`,
);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function alphaBounds(image) {
  const { data, info } = await sharp(image)
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  let left = info.width;
  let top = info.height;
  let right = -1;
  let bottom = -1;
  for (let y = 0; y < info.height; y += 1) {
    for (let x = 0; x < info.width; x += 1) {
      const alpha = data[(y * info.width + x) * info.channels + 3];
      if (alpha === 0) continue;
      left = Math.min(left, x);
      top = Math.min(top, y);
      right = Math.max(right, x);
      bottom = Math.max(bottom, y);
    }
  }
  return right < 0 ? null : { left, top, right, bottom };
}

async function sha256(filePath) {
  return createHash("sha256")
    .update(await readFile(filePath))
    .digest("hex")
    .toUpperCase();
}
