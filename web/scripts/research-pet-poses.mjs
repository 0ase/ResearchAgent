const CELL_WIDTH = 192;
const CELL_HEIGHT = 208;

const COLORS = {
  outline: "#334A60",
  body: "#E8F4F7",
  head: "#F7FBFC",
  screen: "#24B8C7",
  eye: "#173244",
  accent: "#6D84D8",
  paper: "#F7FBFC",
  paperShade: "#DDF6F7",
  muted: "#8CB9C2",
  success: "#16855B",
  critic: "#B65D3A",
};

export const RESEARCH_STATES = [
  "orchestrate",
  "search",
  "filter",
  "read",
  "analyze",
  "synthesize",
  "critic",
];

export const PERSPECTIVE_CONTRACT = {
  cell: { width: CELL_WIDTH, height: CELL_HEIGHT },
  safeBounds: { left: 12, top: 8, right: 180, bottom: 196 },
  baselineY: 176,
  shadowCenterY: 186,
  maxBodyShiftX: 18,
  maxBodyLeanDeg: 8,
  views: {
    front: { yawDeg: 0 },
    left34: { yawDeg: -35 },
    right34: { yawDeg: 35 },
  },
};

export const RESEARCH_POSES = {
  orchestrate: [
    pose("front", "think", "plan", { loopAnchor: "think" }),
    pose("left34", "take-plan", "plan", { dx: -3, crouch: 5 }),
    pose("left34", "open-plan", "plan", { dx: -3, lean: -3 }),
    pose("front", "point-plan-left", "plan", { poster: true }),
    pose("front", "think-plan", "plan"),
    pose("right34", "point-plan-right", "plan", { dx: 3, lean: 3 }),
    pose("front", "close-plan", "plan"),
    pose("front", "think", "plan", { loopAnchor: "think" }),
  ],
  search: [
    pose("front", "raise-glass", "magnifier", { loopAnchor: "raise" }),
    pose("left34", "scan-left-high", "magnifier", { dx: -7, lean: -5 }),
    pose("left34", "scan-left-low", "magnifier", {
      dx: -8,
      lean: -7,
      crouch: 4,
    }),
    pose("front", "inspect-front", "magnifier", { poster: true }),
    pose("right34", "scan-right-high", "magnifier", {
      dx: 7,
      lean: 5,
    }),
    pose("right34", "scan-right-low", "magnifier", {
      dx: 8,
      lean: 7,
      crouch: 4,
    }),
    pose("front", "lower-glass", "magnifier"),
    pose("front", "raise-glass", "magnifier", { loopAnchor: "raise" }),
  ],
  filter: [
    pose("front", "hold-stack", "paper-baskets", { loopAnchor: "stack" }),
    pose("left34", "pull-left", "paper-baskets", { dx: -3 }),
    pose("left34", "drop-left", "paper-baskets", {
      dx: -6,
      lean: -6,
      crouch: 10,
      poster: true,
    }),
    pose("front", "draw-next", "paper-baskets"),
    pose("right34", "drop-right", "paper-baskets", {
      dx: 6,
      lean: 6,
      crouch: 10,
    }),
    pose("front", "hold-stack", "paper-baskets", { loopAnchor: "stack" }),
  ],
  read: [
    pose("front", "book-open", "book", { loopAnchor: "open" }),
    pose("left34", "read-left", "book", { dx: -2, headDrop: 4 }),
    pose("left34", "read-down", "book", { dx: -2, headDrop: 7 }),
    pose("front", "pinch-page", "book", { headDrop: 3, poster: true }),
    pose("front", "page-vertical", "book", { headDrop: 3 }),
    pose("front", "page-land", "book", { headDrop: 3 }),
    pose("right34", "read-right", "book", { dx: 2, headDrop: 5 }),
    pose("front", "book-open", "book", { loopAnchor: "open" }),
  ],
  analyze: [
    pose("front", "papers-spread", "comparison-papers", {
      loopAnchor: "spread",
    }),
    pose("left34", "inspect-left-paper", "comparison-papers", {
      dx: -4,
      lean: -4,
    }),
    pose("left34", "point-left-paper", "comparison-papers", { dx: -3 }),
    pose("front", "papers-compare", "comparison-papers", { poster: true }),
    pose("right34", "inspect-right-paper", "comparison-papers", {
      dx: 4,
      lean: 4,
    }),
    pose("right34", "point-right-paper", "comparison-papers", { dx: 3 }),
    pose("front", "papers-overlap", "comparison-papers"),
    pose("front", "papers-spread", "comparison-papers", {
      loopAnchor: "spread",
    }),
  ],
  synthesize: [
    pose("front", "sections-apart", "report-sections", {
      loopAnchor: "apart",
    }),
    pose("left34", "align-left", "report-sections", { dx: -3 }),
    pose("front", "align-center", "report-sections"),
    pose("front", "sections-touch", "report-sections", { poster: true }),
    pose("right34", "bind-report", "report-sections", { dx: 3 }),
    pose("front", "present-report", "report-sections", { headDrop: -2 }),
    pose("front", "lower-report", "report-sections"),
    pose("front", "sections-apart", "report-sections", {
      loopAnchor: "apart",
    }),
  ],
  critic: [
    pose("front", "review-ready", "report-pencil", { loopAnchor: "ready" }),
    pose("left34", "review-lean", "report-pencil", {
      dx: -3,
      lean: -4,
      headDrop: 4,
    }),
    pose("left34", "mark-first", "report-pencil", {
      dx: -3,
      headDrop: 4,
      poster: true,
    }),
    pose("front", "rotate-report", "report-pencil", { headDrop: 3 }),
    pose("right34", "mark-second", "report-pencil", {
      dx: 2,
      lean: 3,
      headDrop: 3,
    }),
    pose("front", "review-ready", "report-pencil", { loopAnchor: "ready" }),
  ],
};

export function renderResearchFrame(state, frame, { debug = false } = {}) {
  const frames = RESEARCH_POSES[state];
  if (!frames) throw new Error(`Unknown research pet state: ${state}`);
  const spec = frames[frame];
  if (!spec) throw new Error(`Unknown frame ${frame} for ${state}`);

  const action = renderAction(state, spec);
  const shadowWidth = 38 - Math.abs(spec.lean) * 0.35;
  const transform = `translate(${spec.dx} 0) rotate(${spec.lean} 96 176)`;
  const debugMarkup = debug
    ? renderDebugContacts(action.contacts, spec.view)
    : "";

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${CELL_WIDTH}" height="${CELL_HEIGHT}" viewBox="0 0 ${CELL_WIDTH} ${CELL_HEIGHT}">
  <g id="shadow" opacity=".14"><ellipse cx="${96 + spec.dx}" cy="186" rx="${shadowWidth}" ry="8" fill="#17283A"/></g>
  ${action.ground}
  <g id="character" transform="${transform}">
    ${action.farArm}
    ${renderBody(spec, "torso")}
    ${renderBody(spec, "head")}
    ${action.nearArm}
    ${action.prop}
    ${action.hands}
    ${debugMarkup}
  </g>
  </svg>`;
}

export function renderTurnaroundReferenceSvg() {
  const views = ["front", "left34", "right34"];
  const bodies = views
    .map((view, index) => {
      const spec = pose(view, "reference", "none");
      return `<g transform="translate(${index * CELL_WIDTH} 0)"><ellipse cx="96" cy="186" rx="38" ry="8" fill="#17283A" opacity=".14"/>${renderBody(spec, "torso")}${renderBody(spec, "head")}</g>`;
    })
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="576" height="208" viewBox="0 0 576 208">${bodies}</svg>`;
}

export function renderTurnaroundOverlaySvg() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="192" height="208" viewBox="0 0 192 208"><g opacity=".42">${renderBody(pose("front", "reference", "none"), "torso")}${renderBody(pose("front", "reference", "none"), "head")}</g><g opacity=".34">${renderBody(pose("left34", "reference", "none"), "torso")}${renderBody(pose("left34", "reference", "none"), "head")}</g><g opacity=".34">${renderBody(pose("right34", "reference", "none"), "torso")}${renderBody(pose("right34", "reference", "none"), "head")}</g></svg>`;
}

export function renderPropPerspectiveSvg() {
  const magnifiers = [
    magnifier(56, 56, 15, 1, 68, 73),
    magnifier(150, 56, 15, 0.82, 163, 73),
    magnifier(246, 56, 15, 0.82, 259, 73),
  ];
  const books = [
    bookShape(42, 112, "front", "open"),
    bookShape(138, 112, "left34", "open"),
    bookShape(234, 112, "right34", "open"),
  ];
  const papers = [
    paperShape(39, 22, 42, 52, "front"),
    paperShape(135, 22, 42, 52, "left34"),
    paperShape(231, 22, 42, 52, "right34"),
  ];
  return `<svg xmlns="http://www.w3.org/2000/svg" width="288" height="176" viewBox="0 0 288 176"><g transform="translate(0 12)">${papers.join("")}${magnifiers.join("")}${books.join("")}</g></svg>`;
}

function pose(view, action, prop, options = {}) {
  return {
    view,
    action,
    prop,
    dx: 0,
    lean: 0,
    crouch: 0,
    headDrop: 0,
    poster: false,
    loopAnchor: null,
    baselineY: 176,
    ...options,
  };
}

function renderBody(spec, layer) {
  const y = spec.crouch;
  const headY = 48 + Math.round(y * 0.72) + spec.headDrop;
  const torsoY = 82 + y;
  const torsoHeight = 82 - y;
  const legStart = 151 + Math.round(y * 0.45);
  const eyeY = headY + 25 + Math.round(spec.headDrop * 0.25);
  const serious =
    spec.action.startsWith("review") || spec.action.startsWith("mark");

  if (layer === "torso") {
    if (spec.view === "front") {
      return `<g id="body-${spec.view}"><path d="M72 ${legStart}V176M120 ${legStart}V176" stroke="${COLORS.outline}" stroke-width="8" stroke-linecap="round"/><rect x="57" y="${torsoY}" width="78" height="${torsoHeight}" rx="28" fill="${COLORS.body}" stroke="${COLORS.outline}" stroke-width="6"/><circle cx="96" cy="${torsoY + 34}" r="7" fill="${COLORS.accent}"/></g>`;
    }
    const mirror = spec.view === "right34";
    const torsoPath = mirror
      ? `M66 ${torsoY + 7}Q69 ${torsoY} 82 ${torsoY}H119Q134 ${torsoY + 5} 135 ${torsoY + 21}L132 ${torsoY + 57}Q130 164 116 164H78Q61 162 58 ${torsoY + 58}L58 ${torsoY + 24}Q59 ${torsoY + 12} 66 ${torsoY + 7}Z`
      : `M73 ${torsoY}H110Q124 ${torsoY} 130 ${torsoY + 8}Q134 ${torsoY + 13} 134 ${torsoY + 24}L134 ${torsoY + 58}Q131 162 114 164H76Q62 164 60 ${torsoY + 58}L57 ${torsoY + 21}Q58 ${torsoY + 5} 73 ${torsoY}Z`;
    const legLeftX = mirror ? 75 : 72;
    const legRightX = mirror ? 121 : 117;
    const accentX = mirror ? 99 : 93;
    return `<g id="body-${spec.view}"><path d="M${legLeftX} ${legStart}V176M${legRightX} ${legStart}V176" stroke="${COLORS.outline}" stroke-width="8" stroke-linecap="round"/><path d="${torsoPath}" fill="${COLORS.body}" stroke="${COLORS.outline}" stroke-width="6" stroke-linejoin="round"/><path d="M${mirror ? 75 : 117} ${torsoY + 5}Q${mirror ? 67 : 125} ${torsoY + 40} ${mirror ? 75 : 117} 159" fill="none" stroke="#CBE3E8" stroke-width="3" opacity=".8"/><circle cx="${accentX}" cy="${torsoY + 34}" r="7" fill="${COLORS.accent}"/></g>`;
  }

  if (spec.view === "front") {
    const eyeMarkup = serious
      ? `<path d="M81 ${eyeY - 1}l9 2M102 ${eyeY + 1}l9-2" stroke="${COLORS.eye}" stroke-width="4" stroke-linecap="round"/>`
      : `<circle cx="86" cy="${eyeY}" r="4" fill="${COLORS.eye}"/><circle cx="106" cy="${eyeY}" r="4" fill="${COLORS.eye}"/>`;
    return `<g id="head-${spec.view}"><path d="M96 ${headY}L96 ${headY - 22}" stroke="${COLORS.outline}" stroke-width="6" stroke-linecap="round"/><circle cx="96" cy="${headY - 27}" r="7" fill="${COLORS.screen}" stroke="${COLORS.outline}" stroke-width="4"/><rect x="64" y="${headY}" width="64" height="53" rx="22" fill="${COLORS.head}" stroke="${COLORS.outline}" stroke-width="6"/><rect x="72" y="${headY + 12}" width="48" height="27" rx="10" fill="${COLORS.screen}"/>${eyeMarkup}</g>`;
  }

  const right = spec.view === "right34";
  const headPath = right
    ? `M72 ${headY}H113Q128 ${headY + 1} 131 ${headY + 16}L129 ${headY + 37}Q127 ${headY + 52} 113 ${headY + 53}H75Q62 ${headY + 51} 61 ${headY + 37}L62 ${headY + 17}Q63 ${headY + 4} 72 ${headY}Z`
    : `M79 ${headY}H120Q129 ${headY + 4} 130 ${headY + 17}L131 ${headY + 37}Q130 ${headY + 51} 117 ${headY + 53}H79Q65 ${headY + 52} 63 ${headY + 37}L61 ${headY + 16}Q64 ${headY + 1} 79 ${headY}Z`;
  const screenPath = right
    ? `M73 ${headY + 12}H112Q120 ${headY + 13} 121 ${headY + 21}L120 ${headY + 31}Q119 ${headY + 39} 111 ${headY + 40}H72Q68 ${headY + 37} 68 ${headY + 31}L68 ${headY + 21}Q68 ${headY + 15} 73 ${headY + 12}Z`
    : `M80 ${headY + 12}H119Q124 ${headY + 15} 124 ${headY + 21}L124 ${headY + 31}Q124 ${headY + 37} 120 ${headY + 40}H81Q73 ${headY + 39} 72 ${headY + 31}L71 ${headY + 21}Q72 ${headY + 13} 80 ${headY + 12}Z`;
  const nearEyeX = right ? 105 : 87;
  const farEyeX = right ? 83 : 109;
  const rootX = right ? 100 : 92;
  const tipX = right ? 108 : 84;
  const eyes = serious
    ? `<path d="M${nearEyeX - 4} ${eyeY - 1}l8 2M${farEyeX - 3} ${eyeY}l6-1" stroke="${COLORS.eye}" stroke-width="4" stroke-linecap="round"/>`
    : `<circle cx="${nearEyeX}" cy="${eyeY}" r="4" fill="${COLORS.eye}"/><circle cx="${farEyeX}" cy="${eyeY}" r="3.3" fill="${COLORS.eye}"/>`;
  return `<g id="head-${spec.view}"><path d="M${rootX} ${headY + 1}L${tipX} ${headY - 22}" stroke="${COLORS.outline}" stroke-width="6" stroke-linecap="round"/><circle cx="${tipX}" cy="${headY - 27}" r="7" fill="${COLORS.screen}" stroke="${COLORS.outline}" stroke-width="4"/><path d="${headPath}" fill="${COLORS.head}" stroke="${COLORS.outline}" stroke-width="6" stroke-linejoin="round"/><path d="${screenPath}" fill="${COLORS.screen}"/>${eyes}</g>`;
}

function renderAction(state, spec) {
  if (state === "orchestrate") return renderOrchestrate(spec);
  if (state === "search") return renderSearch(spec);
  if (state === "filter") return renderFilter(spec);
  if (state === "read") return renderRead(spec);
  if (state === "analyze") return renderAnalyze(spec);
  if (state === "synthesize") return renderSynthesize(spec);
  if (state === "critic") return renderCritic(spec);
  return emptyAction();
}

function renderOrchestrate(spec) {
  const s = shoulders(spec);
  const y = spec.crouch;
  let leftHand = { x: 69, y: 119 + y };
  let rightHand = { x: 124, y: 118 + y };
  let leftElbow = { x: 52, y: 111 + y };
  let rightElbow = { x: 139, y: 108 + y };
  let prop = "";

  if (spec.action === "think") {
    leftHand = { x: 82, y: 74 + spec.headDrop };
    leftElbow = { x: 58, y: 105 };
    rightHand = { x: 131, y: 132 };
    rightElbow = { x: 143, y: 119 };
  } else if (spec.action === "take-plan") {
    leftHand = { x: 70, y: 145 };
    rightHand = { x: 112, y: 142 };
    leftElbow = { x: 53, y: 129 };
    rightElbow = { x: 133, y: 126 };
    prop = foldedPlan(76, 132, spec.view);
  } else if (spec.action === "open-plan") {
    leftHand = { x: 53, y: 128 };
    rightHand = { x: 131, y: 132 };
    prop = planSheet(51, 107, 82, 42, spec.view, false);
  } else if (spec.action === "point-plan-left") {
    leftHand = { x: 54, y: 133 };
    rightHand = { x: 87, y: 111 };
    rightElbow = { x: 137, y: 111 };
    prop = planSheet(49, 112, 94, 42, "front", true);
  } else if (spec.action === "think-plan") {
    leftHand = { x: 55, y: 135 };
    rightHand = { x: 113, y: 75 };
    rightElbow = { x: 139, y: 106 };
    prop = planSheet(50, 114, 91, 40, "front", false);
  } else if (spec.action === "point-plan-right") {
    leftHand = { x: 104, y: 111 };
    rightHand = { x: 139, y: 134 };
    leftElbow = { x: 54, y: 111 };
    prop = planSheet(50, 112, 92, 42, spec.view, true);
  } else {
    leftHand = { x: 75, y: 134 };
    rightHand = { x: 119, y: 134 };
    prop = foldedPlan(81, 126, "front");
  }
  return composeHeldAction(
    spec,
    s,
    leftElbow,
    leftHand,
    rightElbow,
    rightHand,
    prop,
  );
}

function renderSearch(spec) {
  const s = shoulders(spec);
  const y = spec.crouch;
  let glass = { x: 116, y: 88, rx: 15, ratio: 1, gripX: 128, gripY: 104 };
  let rightHand = { x: glass.gripX, y: glass.gripY };
  let rightElbow = { x: 141, y: 116 + y };
  let leftHand = { x: 55, y: 133 + y };
  let leftElbow = { x: 45, y: 119 + y };

  if (spec.action.includes("left")) {
    glass = spec.action.endsWith("low")
      ? { x: 49, y: 127, rx: 16, ratio: 0.82, gripX: 62, gripY: 142 }
      : { x: 52, y: 77, rx: 16, ratio: 0.82, gripX: 65, gripY: 94 };
    leftHand = { x: glass.gripX, y: glass.gripY };
    leftElbow = { x: 49, y: 112 + y };
    rightHand = { x: 135, y: 133 + y };
    rightElbow = { x: 144, y: 119 + y };
  } else if (spec.action.includes("right")) {
    glass = spec.action.endsWith("low")
      ? { x: 143, y: 127, rx: 16, ratio: 0.82, gripX: 130, gripY: 142 }
      : { x: 140, y: 77, rx: 16, ratio: 0.82, gripX: 127, gripY: 94 };
    rightHand = { x: glass.gripX, y: glass.gripY };
    rightElbow = { x: 143, y: 112 + y };
    leftHand = { x: 57, y: 133 + y };
    leftElbow = { x: 47, y: 119 + y };
  } else if (spec.action === "inspect-front") {
    glass = { x: 107, y: 75, rx: 18, ratio: 1, gripX: 121, gripY: 96 };
    rightHand = { x: 121, y: 96 };
    rightElbow = { x: 144, y: 112 };
  } else if (spec.action === "lower-glass") {
    glass = { x: 135, y: 132, rx: 14, ratio: 1, gripX: 124, gripY: 145 };
    rightHand = { x: 124, y: 145 };
    rightElbow = { x: 145, y: 126 };
  }

  const prop = magnifier(
    glass.x,
    glass.y,
    glass.rx,
    glass.ratio,
    glass.gripX,
    glass.gripY,
  );
  return composeHeldAction(
    spec,
    s,
    leftElbow,
    leftHand,
    rightElbow,
    rightHand,
    prop,
  );
}

function renderFilter(spec) {
  const s = shoulders(spec);
  const y = spec.crouch;
  const ground = `${basket(22, 163, false)}${basket(132, 163, true)}`;
  let leftHand = { x: 75, y: 132 + y };
  let rightHand = { x: 116, y: 132 + y };
  let leftElbow = { x: 56, y: 120 + y };
  let rightElbow = { x: 136, y: 120 + y };
  let prop = paperStack(77, 118 + y, 39, 31, "front", 4);

  if (spec.action === "pull-left") {
    leftHand = { x: 54, y: 116 };
    rightHand = { x: 109, y: 134 };
    leftElbow = { x: 48, y: 109 };
    prop = `${paperStack(82, 122, 36, 28, spec.view, 3)}${paperShape(39, 93, 39, 29, spec.view)}`;
  } else if (spec.action === "drop-left") {
    leftHand = { x: 45, y: 157 };
    rightHand = { x: 110, y: 142 };
    leftElbow = { x: 54, y: 136 };
    prop = `${paperStack(82, 130, 34, 25, spec.view, 2)}${paperShape(29, 142, 35, 25, spec.view)}`;
  } else if (spec.action === "draw-next") {
    leftHand = { x: 82, y: 121 };
    rightHand = { x: 116, y: 135 };
    prop = `${paperStack(79, 124, 38, 27, "front", 3)}${paperShape(69, 105, 41, 27, "front")}`;
  } else if (spec.action === "drop-right") {
    leftHand = { x: 82, y: 142 };
    rightHand = { x: 147, y: 157 };
    rightElbow = { x: 138, y: 136 };
    prop = `${paperStack(76, 130, 34, 25, spec.view, 2)}${paperShape(128, 142, 35, 25, spec.view)}`;
  }
  return {
    ...composeHeldAction(
      spec,
      s,
      leftElbow,
      leftHand,
      rightElbow,
      rightHand,
      prop,
    ),
    ground,
  };
}

function renderRead(spec) {
  const s = shoulders(spec);
  const y = spec.crouch;
  const leftHand = { x: 54, y: 148 + y };
  const rightHand = { x: 138, y: 148 + y };
  const leftElbow = { x: 45, y: 127 + y };
  const rightElbow = { x: 147, y: 127 + y };
  const page =
    spec.action === "page-vertical"
      ? "vertical"
      : spec.action === "page-land"
        ? "land"
        : spec.action === "pinch-page"
          ? "pinch"
          : "open";
  const prop = bookShape(45, 111, spec.view, page);
  return composeHeldAction(
    spec,
    s,
    leftElbow,
    leftHand,
    rightElbow,
    rightHand,
    prop,
  );
}

function renderAnalyze(spec) {
  const s = shoulders(spec);
  let leftPaper = { x: 28, y: 100, view: spec.view };
  let rightPaper = { x: 119, y: 100, view: spec.view };
  let leftHand = { x: 55, y: 139 };
  let rightHand = { x: 137, y: 139 };
  let leftElbow = { x: 47, y: 119 };
  let rightElbow = { x: 145, y: 119 };

  if (spec.action.includes("left")) {
    leftPaper = { x: 42, y: 86, view: "left34" };
    rightPaper = { x: 116, y: 111, view: "left34" };
    leftHand = { x: 63, y: 129 };
    rightHand = spec.action.startsWith("point")
      ? { x: 68, y: 111 }
      : { x: 137, y: 143 };
    rightElbow = { x: 137, y: 119 };
  } else if (spec.action.includes("right")) {
    leftPaper = { x: 30, y: 111, view: "right34" };
    rightPaper = { x: 108, y: 86, view: "right34" };
    rightHand = { x: 129, y: 129 };
    leftHand = spec.action.startsWith("point")
      ? { x: 124, y: 111 }
      : { x: 55, y: 143 };
    leftElbow = { x: 55, y: 119 };
  } else if (spec.action === "papers-overlap") {
    leftPaper = { x: 55, y: 103, view: "front" };
    rightPaper = { x: 82, y: 107, view: "front" };
    leftHand = { x: 70, y: 143 };
    rightHand = { x: 119, y: 143 };
  }

  const prop = `${paperShape(leftPaper.x, leftPaper.y, 43, 50, leftPaper.view)}${paperShape(rightPaper.x, rightPaper.y, 43, 50, rightPaper.view, true)}`;
  return composeHeldAction(
    spec,
    s,
    leftElbow,
    leftHand,
    rightElbow,
    rightHand,
    prop,
  );
}

function renderSynthesize(spec) {
  const s = shoulders(spec);
  let left = { x: 26, y: 106, w: 43, h: 45 };
  let right = { x: 123, y: 106, w: 43, h: 45 };
  let leftHand = { x: 57, y: 142 };
  let rightHand = { x: 135, y: 142 };
  let leftElbow = { x: 45, y: 122 };
  let rightElbow = { x: 147, y: 122 };

  if (spec.action === "align-left") {
    left = { x: 42, y: 103, w: 43, h: 45 };
    leftHand = { x: 69, y: 140 };
  } else if (spec.action === "align-center") {
    left = { x: 53, y: 104, w: 43, h: 45 };
    right = { x: 103, y: 106, w: 43, h: 45 };
    leftHand = { x: 79, y: 141 };
    rightHand = { x: 123, y: 142 };
  } else if (spec.action === "sections-touch") {
    left = { x: 55, y: 104, w: 42, h: 46 };
    right = { x: 95, y: 104, w: 42, h: 46 };
    leftHand = { x: 72, y: 143 };
    rightHand = { x: 120, y: 143 };
  } else if (spec.action === "bind-report") {
    left = { x: 67, y: 104, w: 58, h: 47 };
    right = { x: 67, y: 104, w: 58, h: 47 };
    leftHand = { x: 74, y: 140 };
    rightHand = { x: 118, y: 140 };
  } else if (spec.action === "present-report") {
    left = { x: 65, y: 91, w: 62, h: 50 };
    right = { x: 65, y: 91, w: 62, h: 50 };
    leftHand = { x: 70, y: 128 };
    rightHand = { x: 122, y: 128 };
    leftElbow = { x: 49, y: 111 };
    rightElbow = { x: 143, y: 111 };
  } else if (spec.action === "lower-report") {
    left = { x: 66, y: 105, w: 60, h: 48 };
    right = { x: 66, y: 105, w: 60, h: 48 };
    leftHand = { x: 72, y: 142 };
    rightHand = { x: 120, y: 142 };
  }

  const merged =
    spec.action === "bind-report" || spec.action === "present-report";
  const completeReport = merged || spec.action === "lower-report";
  const prop = completeReport
    ? reportShape(left.x, left.y, left.w, left.h, spec.view)
    : `${sectionShape(left.x, left.y, left.w, left.h, "left")}${sectionShape(right.x, right.y, right.w, right.h, "right")}`;
  return composeHeldAction(
    spec,
    s,
    leftElbow,
    leftHand,
    rightElbow,
    rightHand,
    prop,
  );
}

function renderCritic(spec) {
  const s = shoulders(spec);
  let report = { x: 52, y: 102, view: spec.view };
  let leftHand = { x: 62, y: 143 };
  let rightHand = { x: 130, y: 122 };
  let leftElbow = { x: 49, y: 124 };
  let rightElbow = { x: 146, y: 116 };
  let pencil = { x1: 124, y1: 116, x2: 102, y2: 135 };

  if (spec.action === "review-lean" || spec.action === "mark-first") {
    report = { x: 47, y: 99, view: "left34" };
    leftHand = { x: 59, y: 141 };
    rightHand = { x: 122, y: 119 };
    pencil =
      spec.action === "mark-first"
        ? { x1: 119, y1: 115, x2: 91, y2: 129 }
        : { x1: 126, y1: 111, x2: 104, y2: 124 };
  } else if (spec.action === "rotate-report") {
    report = { x: 61, y: 97, view: "front" };
    leftHand = { x: 69, y: 141 };
    rightHand = { x: 132, y: 123 };
  } else if (spec.action === "mark-second") {
    report = { x: 61, y: 100, view: "right34" };
    leftHand = { x: 71, y: 142 };
    rightHand = { x: 132, y: 128 };
    pencil = { x1: 130, y1: 124, x2: 101, y2: 141 };
  }

  const prop = `${reviewReport(report.x, report.y, 67, 58, report.view)}${pencilShape(pencil.x1, pencil.y1, pencil.x2, pencil.y2)}`;
  return composeHeldAction(
    spec,
    s,
    leftElbow,
    leftHand,
    rightElbow,
    rightHand,
    prop,
  );
}

function composeHeldAction(
  spec,
  s,
  leftElbow,
  leftHand,
  rightElbow,
  rightHand,
  prop,
) {
  const leftArm = armPath(
    s.left,
    leftElbow,
    leftHand,
    spec.view === "right34" ? 7 : 8,
  );
  const rightArm = armPath(
    s.right,
    rightElbow,
    rightHand,
    spec.view === "left34" ? 7 : 8,
  );
  const leftIsFar = spec.view === "right34";
  const rightIsFar = spec.view === "left34";
  return {
    ground: "",
    farArm: `${leftIsFar ? leftArm : ""}${rightIsFar ? rightArm : ""}`,
    nearArm: `${leftIsFar ? "" : leftArm}${rightIsFar ? "" : rightArm}`,
    prop,
    hands: `${hand(leftHand.x, leftHand.y, leftIsFar ? 4.5 : 5)}${hand(rightHand.x, rightHand.y, rightIsFar ? 4.5 : 5)}`,
    contacts: [leftHand, rightHand],
  };
}

function shoulders(spec) {
  const y = 106 + spec.crouch;
  if (spec.view === "left34")
    return { left: { x: 61, y }, right: { x: 128, y: y + 2 } };
  if (spec.view === "right34")
    return { left: { x: 64, y: y + 2 }, right: { x: 131, y } };
  return { left: { x: 60, y }, right: { x: 132, y } };
}

function armPath(shoulder, elbow, handPoint, width) {
  return `<path d="M${shoulder.x} ${shoulder.y}Q${elbow.x} ${elbow.y} ${handPoint.x} ${handPoint.y}" fill="none" stroke="${COLORS.outline}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"/>`;
}

function hand(x, y, r) {
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${COLORS.body}" stroke="${COLORS.outline}" stroke-width="3"/>`;
}

function renderDebugContacts(contacts, view) {
  return `<g id="debug-contacts" fill="#FF2D7A" stroke="#FFFFFF" stroke-width="1.5">${contacts.map(({ x, y }) => `<circle cx="${x}" cy="${y}" r="4"/>`).join("")}<circle cx="96" cy="176" r="3"/><path d="M96 176V184" stroke="#FF2D7A" stroke-width="2"/><path d="M90 184H102" stroke="#FF2D7A" stroke-width="2"/><title>${view} grip and baseline contacts</title></g>`;
}

function emptyAction() {
  return {
    ground: "",
    farArm: "",
    nearArm: "",
    prop: "",
    hands: "",
    contacts: [],
  };
}

function planSheet(x, y, width, height, view, withPointer) {
  const skew = view === "left34" ? -6 : view === "right34" ? 6 : 0;
  const pointer = withPointer
    ? `<path d="M${x + width * 0.52} ${y + height * 0.58}l10-12" stroke="${COLORS.outline}" stroke-width="4" stroke-linecap="round"/>`
    : "";
  return `<g><path d="M${x + skew} ${y}H${x + width + skew}L${x + width - skew} ${y + height}H${x - skew}Z" fill="${COLORS.paper}" stroke="${COLORS.outline}" stroke-width="4" stroke-linejoin="round"/><g fill="${COLORS.accent}" stroke="${COLORS.accent}" stroke-width="2"><circle cx="${x + 18}" cy="${y + 13}" r="4"/><circle cx="${x + width * 0.52}" cy="${y + 10}" r="4"/><circle cx="${x + width - 18}" cy="${y + 25}" r="4"/><path d="M${x + 22} ${y + 13}L${x + width * 0.48} ${y + 10}M${x + width * 0.56} ${y + 12}L${x + width - 21} ${y + 23}" fill="none"/></g>${pointer}</g>`;
}

function foldedPlan(x, y, view) {
  return paperShape(x, y, 34, 22, view);
}

function magnifier(cx, cy, radius, ratio, gripX, gripY) {
  const ry = radius;
  const rx = radius * ratio;
  return `<g><ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="#DDF6F7" fill-opacity=".45" stroke="${COLORS.outline}" stroke-width="6"/><path d="M${cx + rx * 0.62} ${cy + ry * 0.65}L${gripX} ${gripY}" stroke="${COLORS.outline}" stroke-width="7" stroke-linecap="round"/><ellipse cx="${cx}" cy="${cy}" rx="${Math.max(3, rx - 6)}" ry="${Math.max(3, ry - 6)}" fill="none" stroke="${COLORS.screen}" stroke-width="2" opacity=".7"/></g>`;
}

function basket(x, y, right) {
  const skew = right ? 3 : -3;
  return `<g><path d="M${x + 4} ${y + 8}H${x + 36}L${x + 31 + skew} ${y + 31}H${x + 9 + skew}Z" fill="#CBE3E8" stroke="${COLORS.outline}" stroke-width="4" stroke-linejoin="round"/><ellipse cx="${x + 20}" cy="${y + 8}" rx="18" ry="6" fill="${COLORS.paperShade}" stroke="${COLORS.outline}" stroke-width="4"/><path d="M${x + 12} ${y + 16}V${y + 27}M${x + 20} ${y + 15}V${y + 28}M${x + 28} ${y + 16}V${y + 27}" stroke="${COLORS.muted}" stroke-width="2"/></g>`;
}

function paperStack(x, y, width, height, view, count) {
  return Array.from({ length: count }, (_, index) =>
    paperShape(
      x - index * 2,
      y - index * 3,
      width,
      height,
      view,
      index % 2 === 1,
    ),
  ).join("");
}

function paperShape(x, y, width, height, view, alternate = false) {
  const skew = view === "left34" ? -5 : view === "right34" ? 5 : 0;
  const line = alternate ? COLORS.accent : COLORS.screen;
  return `<g><path d="M${x + skew} ${y}H${x + width + skew}L${x + width - skew} ${y + height}H${x - skew}Z" fill="${COLORS.paper}" stroke="${COLORS.outline}" stroke-width="3" stroke-linejoin="round"/><path d="M${x + 8} ${y + 12}H${x + width - 8}M${x + 8} ${y + 21}H${x + width - 13}M${x + 8} ${y + 30}H${x + width - 10}" stroke="${line}" stroke-width="2.5" stroke-linecap="round"/></g>`;
}

function bookShape(x, y, view, page) {
  const skew = view === "left34" ? -7 : view === "right34" ? 7 : 0;
  const leftOuter = x - skew;
  const spine = x + 51;
  const rightOuter = x + 102 + skew;
  const verticalPage =
    page === "vertical"
      ? `<path d="M${spine} ${y + 3}Q${spine + 8} ${y - 5} ${spine + 12} ${y + 5}V${y + 47}Q${spine + 5} ${y + 43} ${spine} ${y + 50}Z" fill="#FFFFFF" stroke="${COLORS.muted}" stroke-width="2"/>`
      : "";
  const landed = page === "land" ? 9 : 0;
  const pinch =
    page === "pinch"
      ? `<path d="M${spine + 31} ${y + 7}l8-5" stroke="${COLORS.outline}" stroke-width="3" stroke-linecap="round"/>`
      : "";
  return `<g><path d="M${leftOuter} ${y + 7}Q${x + 25} ${y - 1} ${spine} ${y + 8}V${y + 52}Q${x + 27} ${y + 42} ${leftOuter} ${y + 49}Z" fill="${COLORS.paper}" stroke="${COLORS.outline}" stroke-width="4"/><path d="M${rightOuter} ${y + 7 + landed}Q${x + 77} ${y - 1 + landed} ${spine} ${y + 8}V${y + 52}Q${x + 77} ${y + 42 + landed} ${rightOuter} ${y + 49 + landed}Z" fill="${COLORS.paper}" stroke="${COLORS.outline}" stroke-width="4"/><path d="M${spine} ${y + 8}V${y + 52}" stroke="${COLORS.muted}" stroke-width="2"/><path d="M${x + 13} ${y + 18}H${x + 39}M${x + 13} ${y + 28}H${x + 42}M${x + 64} ${y + 18 + landed}H${x + 91}M${x + 62} ${y + 28 + landed}H${x + 88}" stroke="${COLORS.accent}" stroke-width="2"/>${verticalPage}${pinch}</g>`;
}

function sectionShape(x, y, width, height, side) {
  const fill = side === "left" ? COLORS.paperShade : COLORS.paper;
  return `<g><rect x="${x}" y="${y}" width="${width}" height="${height}" rx="4" fill="${fill}" stroke="${COLORS.outline}" stroke-width="3"/><path d="M${x + 8} ${y + 12}H${x + width - 8}M${x + 8} ${y + 22}H${x + width - 13}M${x + 8} ${y + 32}H${x + width - 9}" stroke="${side === "left" ? COLORS.accent : COLORS.screen}" stroke-width="2.5"/></g>`;
}

function reportShape(x, y, width, height, view = "front") {
  const skew = view === "left34" ? -5 : view === "right34" ? 5 : 0;
  return `<g><path d="M${x + skew} ${y}H${x + width + skew}L${x + width - skew} ${y + height}H${x - skew}Z" fill="${COLORS.paper}" stroke="${COLORS.outline}" stroke-width="4" stroke-linejoin="round"/><path d="M${x + 8 + skew * 0.5} ${y + 8}H${x + width - 8 + skew * 0.5}V${y + 17}H${x + 8 - skew * 0.5}Z" fill="${COLORS.accent}"/><path d="M${x + 10} ${y + 27}H${x + width - 10}M${x + 10} ${y + 37}H${x + width - 17}" stroke="${COLORS.screen}" stroke-width="3"/></g>`;
}

function reviewReport(x, y, width, height, view) {
  const skew = view === "left34" ? -5 : view === "right34" ? 5 : 0;
  return `<g><path d="M${x + skew} ${y}H${x + width + skew}L${x + width - skew} ${y + height}H${x - skew}Z" fill="${COLORS.paper}" stroke="${COLORS.outline}" stroke-width="4"/><path d="M${x + 12} ${y + 14}H${x + width - 12}M${x + 12} ${y + 27}H${x + width - 18}M${x + 12} ${y + 40}H${x + width - 15}" stroke="${COLORS.muted}" stroke-width="3"/><path d="M${x + 10} ${y + 22}l4 4 7-9M${x + 10} ${y + 36}l4 4 7-9" fill="none" stroke="${COLORS.success}" stroke-width="2.5" stroke-linecap="round"/></g>`;
}

function pencilShape(x1, y1, x2, y2) {
  return `<g><path d="M${x1} ${y1}L${x2} ${y2}" stroke="${COLORS.critic}" stroke-width="6" stroke-linecap="round"/><path d="M${x2} ${y2}l-4 5 6-2Z" fill="${COLORS.outline}"/></g>`;
}
