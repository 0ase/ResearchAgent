import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd(), "messages");
const domains = [
  "common",
  "navigation",
  "composer",
  "task",
  "report",
  "evidence",
  "papers",
  "history",
  "replay",
];

function read(locale, domain) {
  const file = path.join(root, locale, `${domain}.json`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function flatten(value, prefix = "") {
  const output = new Map();
  for (const [key, child] of Object.entries(value)) {
    const next = prefix ? `${prefix}.${key}` : key;
    if (child && typeof child === "object" && !Array.isArray(child)) {
      for (const [nestedKey, nestedValue] of flatten(child, next)) {
        output.set(nestedKey, nestedValue);
      }
    } else {
      output.set(next, String(child));
    }
  }
  return output;
}

function parameters(value) {
  return [...value.matchAll(/\{([a-zA-Z][\w-]*)[^}]*\}/g)].map((match) => match[1]).sort();
}

const errors = [];
for (const domain of domains) {
  const zh = flatten(read("zh-CN", domain));
  const en = flatten(read("en", domain));
  for (const key of new Set([...zh.keys(), ...en.keys()])) {
    if (!zh.has(key)) errors.push(`${domain}: missing zh-CN key ${key}`);
    if (!en.has(key)) errors.push(`${domain}: missing en key ${key}`);
    if (zh.has(key) && en.has(key)) {
      const zhParams = JSON.stringify(parameters(zh.get(key)));
      const enParams = JSON.stringify(parameters(en.get(key)));
      if (zhParams !== enParams) {
        errors.push(`${domain}.${key}: ICU parameters differ`);
      }
    }
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("i18n parity passed");
